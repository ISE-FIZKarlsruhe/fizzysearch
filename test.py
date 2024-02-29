from fizzysearch import register, rewrite


def test_rewrite_simple():
    def replacer(q_object):
        return ["urn:een", "urn:twee", "urn:drie"]

    register(["<http://fizzy/simple>"], replacer)

    query = 'SELECT ?var WHERE { ?var <http://fizzy/simple> "something" . }'
    expected_query = (
        "SELECT ?var WHERE { VALUES ?var {<urn:een> <urn:twee> <urn:drie>}}"
    )
    rewritten_query = rewrite(query)

    assert rewritten_query == expected_query


if __name__ == "__main__":
    test_rewrite_simple()
