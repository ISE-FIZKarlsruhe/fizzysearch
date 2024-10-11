import fizzysearch
from fizzysearch.rdf2vec import use_rdf2vec
import pytest, os

import fizzysearch.rdf2vec


@pytest.fixture
def testdb():
    if not os.path.exists("testrdf2vec"):
        fizzysearch.rdf2vec.build_rdf2vec_index(["pizza.nt"], "testrdf2vec")
    yield "testrdf2vec"


def test_rewrite_rdf2vec(testdb):
    query = """select ?s where {?s <https://fizzysearch.ise.fiz-karlsruhe.de/rdf2vec> <http://www.co-ode.org/ontologies/pizza/pizza.owl#FourSeasons>}"""
    expected_query = 'select ?s where {VALUES (?s ?sScore)\n{(<http://www.co-ode.org/ontologies/pizza/pizza.owl#hasTopping> "0.6233452558517456"^^xsd:decimal)\n(<http://www.co-ode.org/ontologies/pizza/pizza.owl#hasCountryOfOrigin> "0.6356878280639648"^^xsd:decimal)\n}'
    rewritten_query = fizzysearch.rewrite(
        query,
        {"https://fizzysearch.ise.fiz-karlsruhe.de/rdf2vec": use_rdf2vec(testdb, 2)},
    ).get("rewritten")

    assert rewritten_query == expected_query


def test_rewrite_with_prefixin_object(testdb):
    query = """PREFIX pizza: <http://www.co-ode.org/ontologies/pizza/pizza.owl#> \nselect ?s where {?s <https://fizzysearch.ise.fiz-karlsruhe.de/rdf2vec> pizza:FourSeasons}"""
    expected_query = "select ?s where {VALUES ?s {<http://www.co-ode.org/ontologies/pizza/pizza.owl#FourSeasons>}}"
    rewritten_query = fizzysearch.rewrite(
        query,
        {"https://fizzysearch.ise.fiz-karlsruhe.de/rdf2vec": use_rdf2vec(testdb, 2)},
    ).get("rewritten")

    assert rewritten_query == expected_query


if __name__ == "__main__":
    pytest.main()
