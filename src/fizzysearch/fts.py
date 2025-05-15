import logging
from typing import Union
import bikidata


class StringParamException(Exception):
    pass


def use_fts(use_language=False, limit=999):
    return lambda varname, value: search_fts(varname, value, use_language, limit)


def use_fts_stats(use_language=False, limit=999):
    return lambda varname, value: search_fts_stats(varname, value, use_language, limit)


def search_fts(
    varname: str,
    literal: str,
    use_language=False,
    limit=999,
):
    results = search_fts_stats(varname, literal, use_language, limit)
    return {
        "results": [(iri,) for iri, _, _ in results["results"]],
        "vars": (varname,),
    }


def search_fts_stats(
    varname: str,
    literal: str,
    use_language=False,
    limit=999,
):

    literal_value, language, datatype = bikidata.literal_to_parts(literal)
    if not literal_value:
        return {}

    def doit(q, language):
        db = bikidata.raw()

        if use_language:
            theq = f"""with scored as (select *, fts_main_literals.match_bm25(hash, ?, conjunctive:=1) AS score from literals)
            select distinct I1.value, S.value, S.score from (select * from scored where score is not null and value like '%@{language}') S join triples T on S.hash = T.o 
            join iris I1 on I1.hash = T.s join iris I2 on I2.hash = T.p
            order by S.score limit {limit}
            """
        else:
            theq = f"""with scored as (select *, fts_main_literals.match_bm25(hash, ?, conjunctive:=1) AS score from literals)
            select distinct I1.value, S.value, S.score from (select * from scored where score is not null) S join triples T on S.hash = T.o 
            join iris I1 on I1.hash = T.s
            order by S.score limit {limit}
            """
        params = (q,)

        back = []
        for subject, object, score in db.execute(theq, params).fetchall():
            object = bikidata.decode_unicode_escapes(object)
            back.append((subject, object, f'"{score}"^^xsd:decimal'))
        return back

    try:
        return {
            "results": doit(literal_value, language),
            "vars": (varname, varname + "Literal", varname + "Rank"),
        }
    except Exception as e:
        logging.exception("Error in search_fts: " + literal)

    return {}
