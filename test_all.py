from fizzysearch import *
import sqlite3
import pytest


@pytest.fixture
def testdb():
    db = sqlite3.connect(":memory:")
    build_fts_index(["pizza.nt"], db)
    yield db
    db.close()


def test_rewrite_simple(testdb):
    query = 'SELECT ?var WHERE { ?var <https://fizzysearch.ise.fiz-karlsruhe.de/fts/> "PizzaComQueijo" . }'
    expected_query = "SELECT ?var WHERE { VALUES ?var {<http://www.co-ode.org/ontologies/pizza/pizza.owl#CheeseyPizza>}}"
    rewritten_query = rewrite(
        query, {"https://fizzysearch.ise.fiz-karlsruhe.de/fts/": use_fts(testdb)}
    ).get("rewritten")

    assert rewritten_query == expected_query


def test_rewrite_language(testdb):
    query = 'SELECT ?var WHERE { ?var <https://fizzysearch.ise.fiz-karlsruhe.de/fts_language/> "PizzaComQueijo"@pt . }'
    expected_query = "SELECT ?var WHERE { VALUES ?var {<http://www.co-ode.org/ontologies/pizza/pizza.owl#CheeseyPizza>}}"
    rewritten_query = rewrite(
        query,
        {
            "https://fizzysearch.ise.fiz-karlsruhe.de/fts_language/": use_fts(
                testdb, use_language=True
            )
        },
    ).get("rewritten")

    assert rewritten_query == expected_query

    query = 'SELECT ?var WHERE { ?var <https://fizzysearch.ise.fiz-karlsruhe.de/fts_language/> "PizzaComQueijo"@gr . }'
    expected_query = "SELECT ?var WHERE { }"
    rewritten_query = rewrite(
        query,
        {
            "https://fizzysearch.ise.fiz-karlsruhe.de/fts_language/": use_fts(
                testdb, use_language=True
            )
        },
    ).get("rewritten")

    assert rewritten_query == expected_query


def test_comments():
    query = '# This is a comment\nSELECT ?var WHERE { ?var <https://fizzysearch.ise.fiz-karlsruhe.de/fts/> "something" . }'
    rewritten_query = rewrite(query)
    assert "This is a comment" in rewritten_query["comments"]


def test_fts_search_pizza(testdb):
    for row in testdb.execute("SELECT COUNT(*) FROM literal_index"):
        assert row[0] > 0


def test_literal_to_parts():
    literal_value, language, datatype = literal_to_parts('"something"@en')
    assert literal_value == "something"
    assert language == "en"
    literal_value, language, datatype = literal_to_parts('"something"@en')


def test_passing_string_to_fts_index(testdb):
    with pytest.raises(StringParamException) as excinfo:
        build_fts_index("astring", testdb)


if __name__ == "__main__":
    pytest.main()
