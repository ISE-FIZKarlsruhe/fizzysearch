import sys
from tree_sitter import Language, Parser

if sys.platform == "darwin":
    SPARQL = Language("/usr/local/lib/sparql.dylib", "sparql")
else:
    SPARQL = Language("/usr/local/lib/sparql.so", "sparql")

PARSER = Parser()
PARSER.set_language(SPARQL)

PREDICATE_MAP = {}


def register(predicates: list[str], replacer: callable) -> None:
    """
    Register the plugin with the fizzysearch module.

    """
    for p in predicates:
        PREDICATE_MAP[p] = replacer


def rewrite(query: str) -> str:
    tree = PARSER.parse(query.encode("utf8"))
    q = SPARQL.query(
        """((triples_same_subject (var) @var (property_list (property (path_element (iri_reference) @predicate) (object_list [(rdf_literal) @q_object_literal (iri_reference) @q_object_iri])))) @tss (".")* @tss_dot )"""
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
                    found_vars.append((start_byte, end_byte, var_name, q_object))
            start_byte = n.start_byte
            end_byte = n.end_byte
            var_name = q_object = None
            found = False
        if name in ("q_object_literal", "q_object_iri"):
            q_object = n.text.decode("utf8")
        if name == "predicate" and n.text.decode("utf8") in PREDICATE_MAP:
            predicate = n.text.decode("utf8")
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
                    results = PREDICATE_MAP[predicate](q_object.strip('"'))
                    results = " ".join(
                        [
                            f"<{result}>"
                            for result in results
                            if not result.startswith("_:")
                        ]
                    )
                    if results:
                        for cc in f"VALUES {var_name} {{{results}}}":
                            newq.append(cc)
                    i = end_byte
            if not in_found:
                newq.append(chr(c))
            i += 1
        newq = "".join(newq)
        query = newq
    return query
