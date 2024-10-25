FROM python:3.10-bullseye AS builder

ENV PYTHONUNBUFFERED=True

RUN apt update && apt install -y gcc g++ libffi-dev libc-dev make libsqlite3-dev git perl \
    && git clone --recursive https://github.com/epoz/fts5-snowball.git

WORKDIR /fts5-snowball
RUN make

WORKDIR /spellfix
RUN git clone https://gist.github.com/bda9efcdceb1dda0ba7cd80395a86450.git
RUN gcc -g -shared -fPIC bda9efcdceb1dda0ba7cd80395a86450/spellfix.c -o spellfix.so

WORKDIR /tree_sitter_sparql
RUN git clone https://github.com/epoz/tree-sitter-sparql
RUN pip install tree-sitter==0.20.1
RUN python -c "from tree_sitter import Language; Language.build_library('b/sparql.so', ['tree-sitter-sparql'])"

FROM python:3.10-bullseye

COPY --from=builder /fts5-snowball/fts5stemmer.so /usr/local/lib/
COPY --from=builder /spellfix/spellfix.so /usr/local/lib/
COPY --from=builder /tree_sitter_sparql/b/sparql.so /usr/local/lib

WORKDIR /src

COPY ./src .
COPY README.md .
COPY pyproject.toml .

RUN pip install .

ENTRYPOINT ["python", "-m", "fizzysearch"]
