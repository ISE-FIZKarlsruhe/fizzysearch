import os, sys, gzip, sqlite3, logging, argparse
from typing import Union
from .reader import read_nt, literal_to_parts


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
    triplefile_paths: list, index_db_path: Union[str, sqlite3.Connection]
):
    db = get_db(index_db_path)
    logging.debug(f"Building FTS index with {triplefile_paths} in {index_db_path}")

    for s, p, o, _ in read_nt(triplefile_paths):
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

    def doit(q, language):
        if use_language:
            theq = f"SELECT distinct subject, object, language, rank FROM literal_index WHERE object match ? and language = ? order by rank limit {limit}"
            params = (q, language)
        else:
            theq = f"SELECT distinct subject, object, language, rank FROM literal_index WHERE object match ? order by rank limit {limit}"

            params = (q,)

        back = []
        for subject, object, o_language, rank in db.execute(theq, params):
            object = object.encode("utf8").decode("unicode_escape")
            object = object.replace('"', '\\"').replace("\n", "\\n")
            if len(object) > 999:
                object = object[:999] + "..."
            if o_language:
                back.append(
                    (subject, f'"{object}"@{o_language}', f'"{rank}"^^xsd:decimal')
                )
            else:
                back.append((subject, f'"{object}"' f'"{rank}"^^xsd:decimal'))
        return back

    try:
        return {
            "results": doit(literal_value, language),
            "vars": (varname, varname + "Literal", varname + "Rank"),
        }
    except sqlite3.OperationalError as soe:
        if str(soe).find("no such column") > -1:
            try:
                return {
                    "results": doit(f'"{literal_value}"', language),
                    "vars": (varname, varname + "Literal"),
                }
            except Exception as e:
                logging.exception("Error in search_fts: " + literal)
    except Exception as e:
        logging.exception("Error in search_fts: " + literal)

    return {}
