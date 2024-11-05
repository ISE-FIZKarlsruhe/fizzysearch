# FIZzysearch

[Documentation](https://ise-fizkarlsruhe.github.io/fizzysearch/)

## A SPARQL rewriter that performs enhanced searches

This is an extension of the work that was started at the [2023 HackaLOD](https://github.com/ISE-FIZKarlsruhe/hackaLOD23) event in Gouda.
The package provides a SPARQL rewriting framework which can be used to implement different enhanced search facilities like full-text searches or embeddings based searches. The re-writing can be used as a "front-end" to existing SPARQL endpoints, or integrated as a software library.
One of the benefits are enabling easier searches for existing triplestores in which it might be cumbersome to install or configure enhanced search facilities.

✨ This library gives you ["fizzy"](https://en.wiktionary.org/wiki/fizzy) searches! ✨

(and it was made by the [FIZ ISE](https://www.fiz-karlsruhe.de/en/forschung/information-service-engineering) group)

## Example

See the [test file](test_all.py) for some examples on how to build an index and run some test queries.
