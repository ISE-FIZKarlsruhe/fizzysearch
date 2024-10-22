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
        bf = Bloom(len(v), 0.001, hash_func)
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
    def __init__(self, db: str):
        self.predicate_map = {}
        self.predicate_map_size = {}
        self.db = get_db(db)
        for pred, size in self.db.execute(
            "SELECT predicate, size FROM bloomtyper_index"
        ):
            self.predicate_map[pred] = False
            self.predicate_map_size[pred] = size

    def _fetch_from_db(self, predicate: str):
        for pred, bloom in self.db.execute(
            "SELECT predicate, bloom FROM bloomtyper_index WHERE predicate = ?",
            (predicate,),
        ):
            self.predicate_map[pred] = Bloom.load_bytes(bloom, hash_func)
            return self.predicate_map[pred]

    def __call__(self, value, predicate=None):
        if predicate is None:
            return [pred for pred, _ in self if value in self[pred]]

        if self.predicate_map.get(predicate, False) is False:
            self._fetch_from_db(predicate)
        pm = self.predicate_map.get(predicate, set())
        return value in pm

    def __iter__(self):
        for pred in self.predicate_map:
            yield pred, self.predicate_map_size[pred]

    def __getitem__(self, predicate):
        if self.predicate_map.get(predicate) == False:
            return self._fetch_from_db(predicate)
        return self.predicate_map.get(predicate, set())

    def __contains__(self, predicate):
        return predicate in self.predicate_map
