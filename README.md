# FIZzysearch

## A SPARQL rewriter that performs enhanced searches

This is an extension of the work that was started at the [2023 HackaLOD](https://github.com/ISE-FIZKarlsruhe/hackaLOD23) event in Gouda.
The package provides a SPARQL rewriting framework which can be used to implement different enhanced search facilities like full-text searches or embeddings based searches. The re-writing can be used as a "front-end" to existing SPARQL endpoints, or integrated as a software library.
One of the benefits are enabling easier searches for existing triplestores in which it might be cumbersome to install or configure enhanced search facilities.

✨ This library gives you ["fizzy"](https://en.wiktionary.org/wiki/fizzy) searches! ✨

(and it was made by the [FIZ ISE](https://www.fiz-karlsruhe.de/en/forschung/information-service-engineering) group)

## Example

See it in action by running this command in a terminal:

```shell
docker run --rm -it -p 8000:8000 -e FTS_FILEPATH=/fts -e DATA_LOAD_PATHS=https://yogaontology.org/ontology.ttl ghcr.io/epoz/shmarql:latest
```

This will load up a triplestore with an example ontology, and allow fulltext searches over the literals in that store.

[Try this query](http://localhost:8000/sparql#query=SELECT%20*%20WHERE%20%7B%0A%20%20%3Fsub%20%3Chttp%3A%2F%2Fshmarql.com%2Ffts%3E%20%22Sa*%22%20.%0A%7D&endpoint=http%3A%2F%2Flocalhost%3A8000%2Fsparql&requestMethod=POST&tabTitle=Query&headers=%7B%7D&contentTypeConstruct=application%2Fn-triples%2C*%2F*%3Bq%3D0.9&contentTypeSelect=application%2Fsparql-results%2Bjson%2C*%2F*%3Bq%3D0.9&outputFormat=table)

```sparql
SELECT * WHERE {
  ?sub <http://shmarql.com/fts> "Sa*" .
}
```

This demo is from [SHMARQL](https://github.com/epoz/shmarql) which uses FIZzysearch to add fulltext searches to the triplestore.

## TODO

- [x] Add a sample FTS implementation as demo

- [ ] Add documentation on how to build the dependencies and where to fetch the SPARQL grammar
