import os, sys, gzip, sqlite3, logging, argparse
from typing import Union
from .rewriting import literal_to_parts


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


def use_fts(
    fts_filepath: Union[str, sqlite3.Connection], use_language=False, limit=999
):
    return lambda varname, value: search_fts(
        fts_filepath, varname, value, use_language, limit
    )


def search_fts(
    fts_index: Union[str, sqlite3.Connection],
    varname: str,
    literal: str,
    use_language=False,
    limit=999,
):
    db = get_db(fts_index)
    literal_value, language, datatype = literal_to_parts(literal)
    if not literal_value:
        return {}

    def doit(q):
        if use_language:
            theq = f"SELECT distinct subject, object FROM literal_index WHERE object match ? and language = ? order by rank limit {limit}"
            params = (q, language)
        else:
            theq = f"SELECT distinct subject, object FROM literal_index WHERE object match ? order by rank limit {limit}"

            params = (q,)
        return [(subject, object) for subject, object in db.execute(theq, params)]

    try:
        return {"results": doit(literal_value), "vars": (varname, varname + "Literal")}
    except sqlite3.OperationalError as soe:
        if str(soe).find("no such column") > -1:
            try:
                return {
                    "results": doit(f'"{literal_value}"'),
                    "vars": (varname, varname + "Literal"),
                }
            except:
                logging.exception("Error in search_fts: " + literal)
    except:
        logging.exception("Error in search_fts: " + literal)

    return {}
