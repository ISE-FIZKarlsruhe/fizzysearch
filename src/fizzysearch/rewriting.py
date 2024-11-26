import os, sys, argparse
from tree_sitter import Language, Parser

if sys.platform == "darwin":
    SPARQL = Language("/usr/local/lib/sparql.dylib", "sparql")
else:
    SPARQL = Language("/usr/local/lib/sparql.so", "sparql")

PARSER = Parser()
PARSER.set_language(SPARQL)


def rewrite(query: str, predicate_map: dict = dict()) -> dict:
    """@var predicate_map is a dictionary keyed on properties that map to a callable that can be called to expand values for that property"""

    result = {"query": query, "rewritten": query, "comments": []}
    tree = PARSER.parse(query.encode("utf8"))

    result["query_type"] = None
    for t in ("select", "construct", "ask", "describe"):
        for m, m_name in SPARQL.query(f"({t}_query) @{t}_q").captures(tree.root_node):
            result["query_type"] = t

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
                        output = tocall(var_name, q_object)
                        results = []
                        for line in output.get("results", []):
                            lline = " ".join(
                                [l for l in line if not l.startswith("_:")]
                            )
                            if len(line) > 1:
                                results.append(f"({lline})")
                            else:
                                results.append(lline)
                        vars = output.get("vars", [])
                        if len(vars) > 1:
                            results = (
                                "VALUES ("
                                + " ".join([var for var in vars])
                                + ")\n{"
                                + "\n".join(results)
                                + "\n}"
                            )
                        else:
                            results = (
                                f"VALUES {vars[0]}"
                                + " {\n"
                                + "\n".join(results)
                                + "\n}"
                            )
                        for cc in results:
                            newq.append(cc)
                        i = end_byte
            if not in_found:
                newq.append(chr(c))
            i += 1
        newq = "".join(newq)
        result["rewritten"] = newq

    return result
