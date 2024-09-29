from fizzysearch import register, rewrite, rewrite_extended


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


def test_comments():
    query = '# This is a comment\nSELECT ?var WHERE { ?var <http://fizzy/simple> "something" . }'
    rewritten_query = rewrite_extended(query)
    assert "This is a comment" in rewritten_query["comments"]


if __name__ == "__main__":
    test_rewrite_simple()
    test_comments()
