import sqlite3, sys, time
from typing import Union
from rbloom import Bloom  # we want to use at least version 1.5.2
from hashlib import sha256
from .reader import read_nt

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS bloomtyper_index (predicate TEXT, size INTEGER, bloom BLOB);
"""


def get_db(bloomtyper_index: str):
    if isinstance(bloomtyper_index, str):
        db = sqlite3.connect(bloomtyper_index)
    else:
        db = bloomtyper_index
    db.executescript(DB_SCHEMA)
    return db


def hash_func(obj):
    h = sha256(obj.encode("utf8")).digest()
    # use sys.byteorder instead of "big" for a small speedup when
    # reproducibility across machines isn't a concern
    return int.from_bytes(h[:16], "big", signed=True)


def build_bloomtyper_index(
    triplefile_paths: list, index_db_path: Union[str, sqlite3.Connection]
):
    db = get_db(index_db_path)
    the_map = {}
    count = 0
    batch_interval = 30
    start_time = time.time()
    batch_time = start_time - (batch_interval * 2)
    for s, p, o, triplefile_path in read_nt(triplefile_paths):
        count += 1
        if p == "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>":
            the_map.setdefault(o.strip("<>"), set()).add(s.strip("<>"))
            if time.time() - batch_time > batch_interval:
                sys.stderr.write("\r" + " " * 80)
                sys.stderr.write(
                    f"\rFrom {triplefile_path} processed {count} triples in {int(time.time() - start_time)} seconds"
                )
                batch_time = time.time()

    for k, v in the_map.items():
        bf = Bloom(len(v), 0.005, hash_func)
        for vv in v:
            bf.add(vv)

        outbuf = bf.save_bytes()
        db.execute(
            "INSERT INTO bloomtyper_index (predicate, size, bloom) VALUES (?, ?, ?)",
            (k, len(v), outbuf),
        )
    db.commit()
    return count


class Checker:
    def __init__(self, db: str, only_predicates=[]):
        self.predicate_map = {}
        db = get_db(db)

        for predicate, bloom in db.execute(
            "SELECT predicate, bloom FROM bloomtyper_index"
        ):
            self.predicate_map[predicate] = Bloom.load_bytes(bloom, hash_func)

    def check(self, predicate, value):
        if not predicate or not value:
            return []
        return [
            predicate
            for predicate, bloom in self.predicate_map.items()
            if value in bloom
        ]
