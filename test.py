from fizzysearch import register, rewrite, comments


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


def test_comment_caller():
    found = set()

    comments(lambda x: found.add(x))
    comments(lambda x: found.add(x.lower().replace(" ", "_")))

    query = '# This is a comment\nSELECT ?var WHERE { ?var <http://fizzy/simple> "something" . }'
    rewritten_query = rewrite(query)
    assert "# This is a comment" in found
    assert "#_this_is_a_comment" in found


if __name__ == "__main__":
    test_rewrite_simple()
    test_comment_caller()
