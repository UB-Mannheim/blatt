# Structuring the "Maschinenindustrie 1937" book

Save page-xml files into `./MI1937/`.

## Segmentation into segments with separate entities

* see class PageTwoColumns
* geometrically via coordinates
* exceptions are taken into account

## Merging segments from consequent pages and getting the entities

* see class Entities
* properties for entities are obtained via splitting using ':'
* lines between ':' are unhyphenated and merged
* dataframe with 5150 companies and 420 properties are saved into 'raw'-files

## Postprocessing

* properties are grouped and the corresponding values are added into another column with capitalized column-names. For example, the values for the group `{'Geschäftjahr', 'Geschäftsjahr', 'Gescbäftsjahr',
                              'Geschätfsjahr', '.Geschäftsjahr'}` are added to the column `GESCHÄFTSJAHR`
* 'Drahtanschrift' values are exctracted from 'Fernruf' values
* legal forms are exctracted from 'Company' into 'RECHTSFORM'
* 1717 entities have legal forms, 3433 entities don't have legal forms
* the processed dataframe is saved into 'processed'-files

```
PROPERTY                   NUMBER OF VALUES
Company                    5150
RAW_TEXT                   5150
RAW_TEXT_1LINE             5150
FILE_SEGMENT               5150
FABRIKATIONSPROGRAMM       4186
POSTSCHECK-KONTO           3790
FERNRUF                    4096
DRAHTANSCHRIFT             3522
BANKVERBINDUNGEN           4026
ANLAGEN                    2386
INHABER                    1878
GRUNDBESITZ                1770
ANGABEN                    1289
PROKURISTEN                1245
GEFOLGSCHAFT               1344
EIGENE VERTRETUNGEN        1102
GESCHÄFTSFÜHRER            1055
GRÜNDUNG                   4027
SIEHE                       896
AUFSICHTSRAT                468
ANTEILSEIGNER               466
VORSTAND                    429
KAPITAL                    1319
TOCHTERGESELLSCHAFTEN       198
AKTIONÄRE                   187
NUTZFLÄCHE                  238
GESELLSCHAFTER              135
GESCHÄFTSJAHR              3494
FIRMA_GEHÖRT                 80
BETEILIGUNGEN                32
KOMPLEMENTÄRE                31
LENGTH                     5150
OHNE_siehe                   25
SPEZIALITÄT                  19
BEVOLLMÄCHTIGTE              19
GESCHÄFTSINHABER_FÜHRER      18
NIEDERLASSUNGEN              16
UMSATZ                        8
VERTRÄGE                      7
VERKAUFSBÜRO                  6
KOMMANDITISTEN                5
FABRIKATIONSANLAGEN           4
RECHTSFORM                 1717
```

* 'Company' contains company names (and sometimes also legal form and address)
* RAW_TEXT is a raw text per entity from the book
* RAW_TEXT_1LINE is unhyphenated text per entity from the book
* FILE_SEGMENT is a file path + '_' + number of the segment at the page
* LENGTH (quality-check) variable is a list with two values, corresponding to the number of properties in the raw and processed entities. If they are not equal, the entity has multiple values per property.