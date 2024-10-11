import logging, sqlite3, gzip
import voyager
import numpy as np


class StringParamException(Exception):
    pass


def build_rdf2vec_index(
    triplefile_paths: list,
    rdf2vec_index_path: str,
    input_is_unicode_escaped: bool = False,
):
    import igraph as ig
    import gensim
    import xxhash

    if not type(triplefile_paths) == list:
        raise StringParamException(
            "triplefile_paths must be a list of paths to n-triple files"
        )

    logging.debug("RDF2Vec init: now creating nodemap and edgemap")
    nodes = {}
    as_ints = []
    only_subjects = set()
    for triplefile_path in triplefile_paths:
        if triplefile_path.endswith(".gz"):
            thefile = gzip.open(triplefile_path, "rb")
        else:
            thefile = open(triplefile_path, "rb")
        for line in thefile:
            if input_is_unicode_escaped:
                line = line.decode("unicode_escape")
            else:
                line = line.decode("utf8")
            line = line.strip()
            if not line.endswith(" ."):
                continue
            line = line[:-2]
            parts = line.split(" ")
            if len(parts) > 2:
                o = " ".join(parts[2:])
                s = parts[0]
                p = parts[1]

            if not (s.startswith("<") and s.endswith(">")):
                continue
            if not (p.startswith("<") and p.endswith(">")):
                continue
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
        sentences=data, vector_size=100, window=5, min_count=1, workers=4
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
