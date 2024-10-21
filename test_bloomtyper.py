import fizzysearch
import pytest, os, sqlite3

import fizzysearch.bloomtyper


@pytest.fixture
def testbloomtyperdb():
    db = sqlite3.connect(":memory:")
    fizzysearch.bloomtyper.build_bloomtyper_index(["pizza.nt"], db)
    yield db


def test_simple(testbloomtyperdb):
    c = fizzysearch.bloomtyper.Checker(testbloomtyperdb)
    t1 = c.check(
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        "http://www.co-ode.org/ontologies/pizza/pizza.owl#Veneziana",
    )
    assert "http://www.w3.org/2002/07/owl#Class" in t1


if __name__ == "__main__":
    pytest.main()
