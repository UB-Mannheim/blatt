# Structuring the "Wer Leitet?" book

Save page-xml files into `./wer_leitet/`.

## Segmentation into segments with separate entities

* see class PageTwoColumns
* geometrically via coordinates
* exceptions are taken into account

## Merging segments from consequent pages and getting the entities

* see class Entities
* properties for entities are obtained via splitting using ':'
* lines between ':' are unhyphenated and merged

## Postprocessing
