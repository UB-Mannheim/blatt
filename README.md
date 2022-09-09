# Blatt

[![PyPI version](https://badge.fury.io/py/blatt.svg)](https://badge.fury.io/py/blatt)

NLP-helper for OCR-ed pages in [PAGE XML](https://github.com/PRImA-Research-Lab/PAGE-XML) format.

## Table of contents
* [Installation](#installation)
* [How to use](#how-to-use)
* [Command Line Interface](#command-line-interface)

## Installation

```shell
pip install blatt
```

or
```shell
git clone https://github.com/UB-Mannheim/blatt
cd blatt/
pip install .
```

## How to use

### Page object

On initiation the Page-class reads the file `PAGEXML` and stores TextRegions, TextLines and Baseline Coordinates in the Page-object `p`. 
```
from blatt import Page
p = Page(PAGEXML)
```

The Page-object stores unprocessed and processed TextLines as attributes.
```
print(p)
[('root', 2),
 ('namespace', 63),
 ('filename', 24),
 ('text_regions_xml', 38),
 ('text_lines_xml', 260),
 ('text_regions', 260),
 ('text_lines', 260),
 ('baselines', 3651),
 ('text_with_linebreaks', 12111),
 ('text_without_linebreaks', 11979),
 ('sentences', 102),
 ('x_baselines', 3651),
 ('y_baselines', 3651),
 ('center_baseline', 2)]
```

### Hyphen remover & converter to_txt()

The plain text can be saved to `TXT`:
```
from blatt import Page
p = Page(PAGEXML)
p.to_txt(TXT)
```

By default it saves the plain text without line breaks (the hyphens '-', '-', '⹀' and '⸗' are removed and the corresponding words are merged). If you need line breaks, use `p.to_txt(TXT, linebreak=True)`.

### Sentence splitter & converter to_tsv()

The TextLines or sentences can be saved to `TSV`:
```
from blatt import Page
p = Page(PAGEXML)
p.to_tsv(TSV)
```

By default it saves TextLines, TextRegionID, TextLineID and Coordinates to TSV. If you use `p.to_tsv(TSV, sentence=True)`, it saves sentences (not lines!) into separate lines of TSV. The sentences are split from the plain text without hyphens using the [SegTok](https://github.com/fnl/segtok) library.

## Command Line Interface

```
% blatt        
Usage: blatt [OPTIONS] COMMAND [ARGS]...

  Blatt CLI: NLP-helper for OCR-ed pages in PAGE XML format. To get help for a
  particular COMMAND, use `blatt COMMAND -h`.

Options:
  -h, --help  Show this message and exit.

Commands:
  to_tsv  Converts PAGE XML files to TSV files with TextLines or sentences
  to_txt  Converts PAGE XML files to TXT files with or without line breaks &
          hyphens
```

```
% blatt to_txt -h
Usage: blatt to_txt [OPTIONS] PAGE_FOLDER TEXT_FOLDER

  blatt to_txt: converts all PAGE XML files in PAGE_FOLDER to TXT files
  with/without hyphens in TEXT_FOLDER.

Options:
  -lb, --linebreak BOOLEAN  If linebreak==False, it removes hyphens at the end
                            of lines and merges the lines without line breaks.
                            Otherwise, it merges the lines using line breaks.
                            [default: False]
  -h, --help                Show this message and exit.
```

```
% blatt to_tsv -h
Usage: blatt to_tsv [OPTIONS] PAGE_FOLDER TSV_FOLDER

  blatt to_tsv: converts all PAGE XML files in PAGE_FOLDER to TSV files in
  TSV_FOLDER.

Options:
  -s, --sentence BOOLEAN  If sentence==False, it saves TextLines,
                          TextRegionID, TextLineID and Coordinates to TSV.
                          Otherwise, it saves sentences (not lines!) into
                          separate lines of TSV. The sentences are split from
                          the plain text without hyphens using the SegTok
                          library.  [default: False]
  -h, --help              Show this message and exit.
```
