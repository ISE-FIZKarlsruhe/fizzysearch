import os, sys, time
from .fts import build_fts_index
from .rdf2vec import build_rdf2vec_index
from .bloomtyper import build_bloomtyper_index
import logging

log = logging.getLogger("fizzysearch")
handler = logging.StreamHandler()
log.addHandler(handler)
log.setLevel(logging.DEBUG)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(levelname)-9s %(name)s %(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)

input_filepath = os.getenv("INPUT_FILEPATH", ".")

input_filepaths = []
for root, dirs, files in os.walk(input_filepath):
    for file in files:
        if file.endswith(".nt") or file.endswith(".nt.gz"):
            input_filepaths.append(os.path.join(root, file))
if len(input_filepaths) == 0:
    sys.stderr.write(
        f"No n-triple files found in the input directory: {input_filepath}\n"
    )
else:
    start_time = time.time()
    sys.stderr.write(f"Found {len(input_filepaths)} n-triple files\n")

fts_sqlite_path = os.getenv("FTS_SQLITE_PATH")
if fts_sqlite_path:
    sys.stderr.write(
        "Generating a FTS index dirfectly in Fizzysearch is not supported any more. This is now handled by bikidata\n"
    )
    sys.exit(1)

rdf2vec_index_path = os.getenv("RDF2VEC_INDEX_PATH")
if rdf2vec_index_path:
    build_rdf2vec_index(input_filepaths, rdf2vec_index_path)

bloomtyper_index_path = os.getenv("BLOOMTYPER_INDEX_PATH")
if bloomtyper_index_path:
    build_bloomtyper_index(input_filepaths, bloomtyper_index_path)

    sys.stderr.write(
        "Please set either the RDF2VEC_INDEX_PATH or BLOOMTYPER_INDEX_PATH or environment variables to build an index\n"
    )
    sys.exit(1)
else:
    end_time = time.time()
    sys.stderr.write(f"\nIndexing took {int(end_time - start_time)} seconds\n")
