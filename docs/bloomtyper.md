# Bloomtyper

A fast way to check what the `http://www.w3.org/1999/02/22-rdf-syntax-ns#type` is for a given entity over a large input dataset.

The Bloomtyper index builds a set of [bloomfilters](https://en.wikipedia.org/wiki/Bloom_filter), one for each object of the <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> predicate in the scanned triples. The bloomfilter contains a hashed index for all subject entities for each predicate. This can be used for fast lookups of types in large datasets, without looking up the specific entity.

## Use case history

This index was developed in the context of the [NFDI4Culture Knowledge Graph](https://nfdi4culture.de/services/details/culture-knowledge-graph.html). When harvesting data items that use controlled vocabularies like the [GND](https://www.dnb.de/EN/Professionell/Standardisierung/GND/gnd_node.html) it is not feasible for look up each GND item to retrieve it's type while in a transformation loop. (it would make the processor too slow)

The Bloomtyper allows us to preprocess the GND dumps, build an index, and then perform fast lookups.

## Usage example - Star Wars

For a quick test, we can use the nifty [Star Wars Dataset](https://platform.ontotext.com/3.2/datasets/star-wars.html) that has been converted from the [source at SWAPI](https://swapi.dev/) by Ontotext. Let's download the file, and convert it to n-triples first:

```shell
wget https://platform.ontotext.com/3.2/_downloads/0eb1165f6fb5cde4d521e274ce6049ab/starwars-data.ttl
rapper -i turtle -o ntriples starwars-data.ttl > starwars-data.nt
```

This assumes you have the `wget` and [rapper](https://librdf.org/raptor/rapper.html) tools installed on your command line.
Now we can index this file:

```shell
BLOOMTYPER_INDEX_PATH=starwars.bloomtyper python3 -m fizzysearch
```

Using it from python, you can do:

```python
>>> from fizzysearch.bloomtyper import Checker
>>> c = Checker('starwars.bloomtyper')
# Is C3PO a Human?
>>> c('https://swapi.co/resource/droid/2', 'https://swapi.co/vocabulary/Human')
False
# OK, what type is it?
>>> c('https://swapi.co/resource/droid/2')
['https://swapi.co/vocabulary/Character', 'https://swapi.co/vocabulary/Droid']
```

## Usage example - GND

!!! note

    The GND does an amazing job by making their entire [datasets availabe as dumps](https://data.dnb.de/opendata/) 😍 Just fabulous. Wish more institutions would follow their great example.

Here is some instructions on how to build an index. First let's download some authority data:

```shell
wget https://data.dnb.de/opendata/authorities-gnd_lds.nt.gz
wget https://data.dnb.de/opendata/bib_lds.nt.gz
wget https://data.dnb.de/opendata/dnb-all_lds.nt.gz
wget https://data.dnb.de/opendata/zdb_lds.nt.gz
```

This takes a while, and then you have serveral large gzipped n-triple files in a directory.
At the time of writing this, it looked like this:

```shell
4.7G Mar  8  2024 dnb-all_lds.nt.gz
2.1G Feb 27  2024 authorities-gnd_lds.nt.gz
554M Mar 19  2024 zdb_lds.nt.gz
4.8M Mar 19  2024 bib_lds.nt.gz
```

Now we can generate an index over all those files by running the command:

```shell
BLOOMTYPER_INDEX_PATH=gnd.bloomtyper python3 -m fizzysearch
```

This will take some time, as those are quite a number of triples. Once this process is complete we can use the generated index from Python like this:

```python
>>> from fizzysearch.bloomtyper import Checker
>>> c = Checker('gnd.bloomtyper')
>>> c('https://d-nb.info/gnd/187-9')
['https://d-nb.info/standards/elementset/gnd#SeriesOfConferenceOrEvent']
```

The generated bloomtyper index file is only circa 41MB in size, which is tiny - and fast to use - compared to the gigabytes of compressed triples it indexes.
