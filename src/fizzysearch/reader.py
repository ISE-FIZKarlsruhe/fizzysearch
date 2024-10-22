import gzip, re


def literal_to_parts(literal: str):
    literal_value = language = datatype = None
    if literal.startswith('"'):
        end_index = literal.rfind('"')
        if end_index > 0:
            literal_value = literal[1:end_index]
            remainder = literal[end_index + 1 :].strip()
            language = datatype = None
            if remainder.startswith("@"):
                language = remainder[1:]
                datatype = None
            elif remainder.startswith("^^"):
                datatype = remainder[2:]
                language = None
    return literal_value, language, datatype


def decode_unicode_escapes(s):
    # See: https://www.w3.org/TR/n-triples/#grammar-production-UCHAR
    unicode_escape_pattern_u = re.compile(
        r"\\u([0-9a-fA-F]{4})"
    )  # \uXXXX (4 hex digits)
    unicode_escape_pattern_U = re.compile(
        r"\\U([0-9a-fA-F]{8})"
    )  # \UXXXXXXXX (8 hex digits)

    def replace_unicode_escape_u(match):
        hex_value = match.group(1)
        return chr(
            int(hex_value, 16)
        )  # Convert hex to integer, then to Unicode character

    def replace_unicode_escape_U(match):
        hex_value = match.group(1)
        return chr(
            int(hex_value, 16)
        )  # Convert hex to integer, then to Unicode character

    s = unicode_escape_pattern_U.sub(replace_unicode_escape_U, s)
    s = unicode_escape_pattern_u.sub(replace_unicode_escape_u, s)

    return s


class StringParamException(Exception):
    pass


def read_nt(triplefile_paths: list):
    if not type(triplefile_paths) == list:
        raise StringParamException(
            "triplefile_paths must be a list of paths to n-triple files"
        )

    for triplefile_path in triplefile_paths:
        if triplefile_path.endswith(".gz"):
            thefile = gzip.open(triplefile_path, "rb")
        else:
            thefile = open(triplefile_path, "rb")
        for line in thefile:
            if not line.endswith(b" .\n"):
                continue
            line = decode_unicode_escapes(line.decode("utf8"))
            line = line.strip()
            line = line[:-2]
            parts = line.split(" ")
            if len(parts) > 2:
                s = parts[0]
                p = parts[1]
                o = " ".join(parts[2:])

            if not (s.startswith("<") and s.endswith(">")):
                continue
            if not (p.startswith("<") and p.endswith(">")):
                continue

            yield s, p, o, triplefile_path
