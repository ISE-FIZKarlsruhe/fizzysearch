---
title: Getting Started
---

# Getting Started

## Installation

Create a Python virtual environment, and then issue the command:

```shell
pip install fizzysearch
```

## Running the tests

See the [test file](test_all.py) for some examples on how to build an index and run some test queries.

## Examples

Let's say you have a n-triples files in the current directory name `foobar.nt`.
To create a fulltext index of all the literals in this file, you can issue the command in the shell:

```shell
FTS_SQLITE_PATH=example.db python -m fizzysearch
```

If all goes well, this should read your file named foobar.nt, index it, and store the results in a SQLite file named `example.db`

!!! note

    Running on the command line will 'walk' the entire current directory, and all sub-directories if you do not explicitly specify a path. So if you have many .nt files in the current directory, it will try to index them all!

Now that you have a fulltext index for your n-triple file, you could use it in a system like <a href="https://shmarql.com/">SHMARQL</a> to query the file easily.
