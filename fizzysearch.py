import os, sys, gzip, sqlite3, logging, argparse
from tree_sitter import Language, Parser
from typing import Union

if sys.platform == "darwin":
    SPARQL = Language("/usr/local/lib/sparql.dylib", "sparql")
else:
    SPARQL = Language("/usr/local/lib/sparql.so", "sparql")

PARSER = Parser()
PARSER.set_language(SPARQL)

DB_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS literal_index USING fts5(subject UNINDEXED, predicate UNINDEXED, object, language UNINDEXED, datatype UNINDEXED );
CREATE VIRTUAL TABLE IF NOT EXISTS literal_index_vocab USING fts5vocab('literal_index', 'row');
CREATE VIRTUAL TABLE IF NOT EXISTS literal_index_spellfix USING spellfix1;
"""


def get_db(fts_index: str):
    if isinstance(fts_index, str):
        db = sqlite3.connect(fts_index)
    else:
        db = fts_index

    db.enable_load_extension(True)
    if sys.platform == "darwin":
        db.load_extension("/usr/local/lib/fts5stemmer.dylib")
        db.load_extension("/usr/local/lib/spellfix.dylib")
    else:
        db.load_extension("/usr/local/lib/spellfix")
        db.load_extension("/usr/local/lib/fts5stemmer")
    db.executescript(DB_SCHEMA)
    return db


def literal_to_parts(literal: str):
    literal_value = language = datatype = None
    if literal.startswith('"'):
        end_index = literal.rfind('"')
        if end_index > 0:
            literal_value = literal[1:end_index]
            remainder = literal[end_index + 1 :].strip()
            language = datatype = None
            if remainder.startswith("@"):
                language = remainder[1:]
                datatype = None
            elif remainder.startswith("^^"):
                datatype = remainder[2:]
                language = None
    return literal_value, language, datatype


class StringParamException(Exception):
    pass


def build_fts_index(
    triplefile_paths: list,
    fts_index: Union[str, sqlite3.Connection],
    input_is_unicode_escaped: bool = False,
):
    """
    Iterate over the triplefile_paths list of n-triple files, and index the literals
    Note: In some older datasets the input might not be UTF8, but be unicode-escaped.
    This means a chars look like mi\u00EBs instead of miës. If this is the case, set input_is_unicode_escaped to True.
    And then we need to open the files a binary and do .decode('unicode_escape')

    """
    if not type(triplefile_paths) == list:
        raise StringParamException(
            "triplefile_paths must be a list of paths to n-triple files"
        )

    db = get_db(fts_index)
    logging.debug(f"Building FTS index with {triplefile_paths} in {fts_index}")

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
            # TODO - add support for blank nodes
            # How? We will need to back-reference any blanknodes to their referred subjects... :-(

            literal_value, language, datatype = literal_to_parts(o)

            if literal_value:
                db.execute(
                    "INSERT INTO literal_index (subject, predicate, object, language, datatype) VALUES (?, ?, ?, ?, ?)",
                    (s, p, literal_value, language, datatype),
                )
        db.commit()
        logging.debug(f"Building FTS index done")


def use_fts(fts_filepath: Union[str, sqlite3.Connection], use_language=False):
    return lambda x: search_fts(fts_filepath, x, use_language)


def search_fts(
    fts_index: Union[str, sqlite3.Connection], literal: str, use_language=False
):
    db = get_db(fts_index)
    literal_value, language, datatype = literal_to_parts(literal)
    if not literal_value:
        return []
    if use_language:
        return [
            row[0]
            for row in db.execute(
                "SELECT distinct subject FROM literal_index WHERE object match ? and language = ?",
                (literal_value, language),
            )
        ]
    else:
        return [
            row[0]
            for row in db.execute(
                "SELECT distinct subject FROM literal_index WHERE object match ?",
                (literal_value,),
            )
        ]


def rewrite(query: str, predicate_map: dict = dict()) -> dict:
    """@var predicate_map is a dictionary keyed on properties that map to a callable that can be called to expand values for that property"""

    result = {"query": query, "rewritten": query, "comments": []}
    tree = PARSER.parse(query.encode("utf8"))

    # Call the comments listeners
    comment_q = SPARQL.query("(comment) @comment")
    for n, name in comment_q.captures(tree.root_node):
        result["comments"].append(n.text.decode("utf8").strip("# "))

    q = SPARQL.query(
        """((triples_same_subject (var) @var (property_list (property (path_element [(iri_reference) @predicate (prefixed_name) @predicate_prefix]) (object_list [(rdf_literal) @q_object_literal (iri_reference) @q_object_iri])))) @tss (".")* @tss_dot )"""
    )
    found_vars = []
    found = False
    start_byte = end_byte = 0
    var_name = q_object = None
    predicate = None
    for n, name in q.captures(tree.root_node):
        if name == "tss":
            if start_byte > 0 and end_byte > start_byte:
                if var_name is not None and q_object is not None and found:
                    found_vars.append(
                        (start_byte, end_byte, var_name, q_object, predicate)
                    )
            start_byte = n.start_byte
            end_byte = n.end_byte
            var_name = q_object = None
            found = False
        if name in ("q_object_literal", "q_object_iri"):
            q_object = n.text.decode("utf8")
        if name in ("predicate", "predicate_prefix"):
            bare = n.text.decode("utf8").strip("<>")
            if bare in predicate_map:
                predicate = bare
                found = True
        if name == "var":
            var_name = n.text.decode("utf8")
        if name == "tss_dot":
            end_byte = n.end_byte

    # If there is only one,
    if start_byte > 0 and end_byte > start_byte:
        if var_name is not None and q_object is not None and found:
            found_vars.append((start_byte, end_byte, var_name, q_object, predicate))

    if len(found_vars) > 0:
        newq = []
        query_bytes = query.encode("utf8")
        i = 0
        while i < len(query_bytes):
            c = query_bytes[i]
            in_found = False
            for start_byte, end_byte, var_name, q_object, predicate in found_vars:
                if i >= start_byte and i <= end_byte:
                    in_found = True
                    tocall = predicate_map.get(predicate)
                    if tocall:
                        results = tocall(q_object)
                        results = " ".join(
                            [
                                result
                                for result in results
                                if not result.startswith("_:")
                            ]
                        )
                        if results:
                            for cc in f"VALUES {var_name} {{{results}}}":
                                newq.append(cc)
                        i = end_byte
            if not in_found:
                newq.append(chr(c))
            i += 1
        newq = "".join(newq)
        result["rewritten"] = newq

    return result


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "fts_sqlite_path",
        help="The path to the sqlite file that will be created with the FTS data",
    )
    argparser.add_argument(
        "triplefiles",
        help="The path to scan for n-triple files to index",
    )
    args = argparser.parse_args()

    filenames = [
        os.path.join(args.triplefiles, filename)
        for filename in os.listdir(args.triplefiles)
        if filename.endswith(".nt") or filename.endswith(".nt.gz")
    ]
    build_fts_index(filenames, args.fts_sqlite_path)
