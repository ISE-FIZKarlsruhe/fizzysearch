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

The generated bloomtyper index file is only circa 52MB in size, which is tiny - and fast to use - compared to the gigabytes of compressed triples it indexes.
You can download a generated file from here: [https://nfdi.fiz-karlsruhe.de/gnd.bloomtyper](https://nfdi.fiz-karlsruhe.de/gnd.bloomtyper)

We can also see the resulting map of types from the GND, and their counts (as of October 2024):

```python
for x, y in c:
    print(x,y)
```

```
http://purl.org/ontology/bibo/Document 12513177
https://d-nb.info/standards/elementset/gnd#DifferentiatedPerson 6146309
http://purl.org/ontology/bibo/Article 2482466
http://purl.org/ontology/bibo/Issue 2364907
http://purl.org/ontology/bibo/Periodical 1828449
https://d-nb.info/standards/elementset/gnd#CorporateBody 1293126
https://d-nb.info/standards/elementset/gnd#ConferenceOrEvent 775826
https://schema.org/SheetMusic 480217
http://purl.org/ontology/bibo/Collection 430021
http://purl.org/ontology/bibo/Series 344288
https://d-nb.info/standards/elementset/gnd#MusicalWork 292711
http://purl.org/ontology/bibo/Map 292002
https://d-nb.info/standards/elementset/gnd#Work 227514
https://d-nb.info/standards/elementset/gnd#TerritorialCorporateBodyOrAdministrativeUnit 191321
https://d-nb.info/standards/elementset/gnd#SubjectHeadingSensoStricto 127251
https://d-nb.info/standards/elementset/gnd#OrganOfCorporateBody 112424
https://d-nb.info/standards/elementset/gnd#SeriesOfConferenceOrEvent 111320
https://d-nb.info/standards/elementset/gnd#BuildingOrMemorial 76206
https://d-nb.info/standards/elementset/gnd#Company 54418
https://d-nb.info/standards/elementset/gnd#MusicalCorporateBody 52438
https://d-nb.info/standards/elementset/gnd#NomenclatureInBiologyOrChemistry 33330
https://d-nb.info/standards/elementset/gnd#PlaceOrGeographicName 29887
https://d-nb.info/standards/elementset/gnd#NaturalGeographicUnit 22983
https://d-nb.info/standards/elementset/gnd#ReligiousCorporateBody 22180
https://d-nb.info/standards/elementset/gnd#Family 21654
http://xmlns.com/foaf/0.1/Organization 20956
https://d-nb.info/standards/elementset/gnd#AdministrativeUnit 14011
http://purl.org/ontology/bibo/AudioVisualDocument 10573
https://d-nb.info/standards/elementset/gnd#SoftwareProduct 8531
https://d-nb.info/standards/elementset/gnd#SubjectHeading 8221
https://d-nb.info/standards/elementset/gnd#ProvenanceCharacteristic 8147
https://d-nb.info/standards/elementset/gnd#ProductNameOrBrandName 7767
http://purl.org/dc/dcmitype/Service 7749
https://d-nb.info/standards/elementset/gnd#Manuscript 6912
"http://www.w3.org/2006/vcard/ns#Pref"^^<http://www.w3.org/2001/XMLSchema#string 6142
https://d-nb.info/standards/elementset/gnd#Language 6139
http://purl.org/library/BrailleBook 5853
https://d-nb.info/standards/elementset/gnd#Expression 5586
https://d-nb.info/standards/elementset/gnd#WayBorderOrLine 5382
https://d-nb.info/standards/elementset/gnd#ReligiousAdministrativeUnit 4929
https://d-nb.info/standards/elementset/gnd#HistoricSingleEventOrEra 4911
https://d-nb.info/standards/elementset/gnd#EthnographicName 4528
https://d-nb.info/standards/elementset/gnd#RoyalOrMemberOfARoyalHouse 4177
https://d-nb.info/standards/elementset/gnd#ProjectOrProgram 3672
https://d-nb.info/standards/elementset/gnd#CharactersOrMorphemes 3206
https://d-nb.info/standards/elementset/gnd#VersionOfAMusicalWork 2913
https://d-nb.info/standards/elementset/gnd#ReligiousTerritory 2662
https://d-nb.info/standards/elementset/gnd#NameOfSmallGeographicUnitLyingWithinAnotherGeographicUnit 2451
https://d-nb.info/standards/elementset/gnd#Collection 1775
https://d-nb.info/standards/elementset/gnd#LiteraryOrLegendaryCharacter 1604
https://d-nb.info/standards/elementset/gnd#MeansOfTransportWithIndividualName 1517
https://d-nb.info/standards/elementset/gnd#GroupOfPersons 950
https://d-nb.info/standards/elementset/gnd#CollectivePseudonym 924
https://d-nb.info/standards/elementset/gnd#Gods 692
https://d-nb.info/standards/elementset/gnd#MemberState 521
https://d-nb.info/standards/elementset/gnd#ExtraterrestrialTerritory 314
https://d-nb.info/standards/elementset/gnd#Country 306
https://d-nb.info/standards/elementset/gnd#Spirits 121
https://d-nb.info/standards/elementset/gnd#FictivePlace 44
https://d-nb.info/standards/elementset/gnd#FictiveCorporateBody 33
```
