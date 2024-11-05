import logging, sqlite3, gzip
import voyager
import numpy as np
from .reader import read_nt


class StringParamException(Exception):
    pass


def build_rdf2vec_index(
    triplefile_paths: list, rdf2vec_index_path: str, triple_iterator=None
):
    if len(triplefile_paths) > 0:
        logging.debug(
            f"Building RDF2Vec index with {triplefile_paths} in {rdf2vec_index_path}"
        )
        iterator = read_nt(triplefile_paths)
    elif triple_iterator:
        logging.debug(
            f"Building RDF2Vec index with a specified iterator in {rdf2vec_index_path}"
        )
        iterator = triple_iterator
    else:
        logging.error(
            "No triples to index, neither triplefile_paths or triple_iterator given"
        )
        return

    # The imports are inside the building method so we can exclude these libraries at runtime
    # if we only want to use the index not build it.
    import multiprocessing
    
    import igraph as ig
    import gensim
    import xxhash

    logging.debug("RDF2Vec init: now creating nodemap and edgemap")
    nodes = {}
    as_ints = []
    only_subjects = set()
    for s, p, o, _ in iterator:
        s = s.strip("<>")
        p = p.strip("<>")
        o = o.strip("<>")  # and literals just remain as they are
        ss = xxhash.xxh64(s).intdigest()
        pp = xxhash.xxh64(p).intdigest()
        oo = xxhash.xxh64(o).intdigest()
        nodes[ss] = s
        nodes[oo] = o
        nodes[pp] = p
        # we are also just sticking the predicates in as nodes, but they are not used for walks

        as_ints.append((ss, pp, oo))
        only_subjects.add(ss)

    # Make as_ints unique
    as_ints = list(sorted(set(as_ints)))
    nodemap = {}
    for i, node_key in enumerate(nodes):
        nodemap[node_key] = i
    # igraph needs small integers can not deal with 64-bit integers

    logging.debug("RDF2Vec init: now creating network graph")
    graph = ig.Graph(n=len(nodes))
    graph.add_edges([(nodemap[s], nodemap[o]) for s, p, o in as_ints])
    graph.es["p_i"] = [nodemap[p] for s, p, o in as_ints]

    logging.debug("RDF2Vec init: doing random walks")
    data = set(
        tuple(
            [
                tuple(graph.random_walk(nodemap[s], 15))
                for s in only_subjects
                for x in range(100)
            ]
        )
    )

    logging.debug("RDF2Vec init: now training model")
    model = gensim.models.Word2Vec(
        sentences=data,
        vector_size=100,
        window=5,
        min_count=1,
        workers=multiprocessing.cpu_count(),
    )
    vectors = []
    for node_id in only_subjects:
        thevector = model.wv.get_vector(nodemap[node_id])
        vectors.append((thevector, node_id))

    index = voyager.Index(voyager.Space.Cosine, 100)
    index.add_items([v for v, _ in vectors])
    index.save(rdf2vec_index_path)
    logging.debug(f"RDF2Vec {rdf2vec_index_path} created")

    DB = sqlite3.connect(rdf2vec_index_path + ".db")
    DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS rdf2vec_index (id INTEGER PRIMARY KEY, uri TEXT, vector BLOB);
CREATE INDEX IF NOT EXISTS rdf2vec_index_uri ON rdf2vec_index (uri);
"""
    DB.executescript(DB_SCHEMA)
    to_insert = [
        (i, str(nodes[node_id]), vector.tobytes())
        for i, (vector, node_id) in enumerate(vectors)
    ]

    DB.executemany("INSERT INTO rdf2vec_index VALUES (?, ?, ?)", to_insert)
    DB.commit()
    logging.debug(f"RDF2Vec mapping saved in {rdf2vec_index_path}.db")
    return len(to_insert)


def use_rdf2vec(rdf2vec_index: str, limit: int = 20):
    return lambda varname, value: search_rdf2vec(rdf2vec_index, varname, value, limit)


def search_rdf2vec(rdf2vec_index: str, varname: str, node_uri: str, limit: int = 20):
    if not rdf2vec_index or not node_uri:
        return {}

    node_uri = node_uri.strip("<>")

    DB = sqlite3.connect(rdf2vec_index + ".db")
    found = False
    for row in DB.execute(
        "SELECT vector FROM rdf2vec_index WHERE uri = ?", (node_uri,)
    ):
        vector = np.frombuffer(row[0], dtype=np.float32)
        found = True
    if not found:
        return {}

    index = voyager.Index.load(rdf2vec_index)
    ids, distances = index.query(vector, limit)
    result_dict = {}
    for id, distance in zip(ids, distances):
        result_dict[id] = {"distance": distance}
    ids_as = ",".join(str(anid) for anid in ids)
    for id, uri in DB.execute(
        f"SELECT id, uri FROM rdf2vec_index WHERE id IN ({ids_as})"
    ):
        result_dict[id]["uri"] = uri
    sorted_results = sorted(
        [(val["distance"], val["uri"]) for val in result_dict.values()]
    )

    results = [
        (f"<{uri}>", f'"{distance}"^^xsd:decimal') for distance, uri in sorted_results
    ]
    logging.debug(f"RDF2Vec search for {node_uri} found {len(results)}")
    return {"results": results, "vars": (varname, varname + "Score")}
