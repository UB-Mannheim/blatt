# Blatt

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

### PAGE XML reader, hyphen remover and converter

On initiation the Page-class reads the file `PAGEXML` and stores TextRegions, TextLines and Baseline Coordinates in the Page-object `p`. The plain text can be saved to `TXT`:
```
from blatt import Page
p = Page(PAGEXML)
p.to_text(TXT)
```

By default it saves the plain text without line breaks (the hyphens '-', '-', '⹀' and '⸗' are removed and the corresponding words are merged). If you need line breaks, use `p.to_text(TXT, linebreak=True)`.

## Command Line Interface

```
% blatt
Usage: blatt [OPTIONS] COMMAND [ARGS]...

  BLATT CLI: NLP-helper for OCR-ed pages in PAGE XML format. To get help for a
  particular COMMAND, use `blatt COMMAND -h`.

Options:
  --help  Show this message and exit.

Commands:
  convert  Converts PAGE XML files to plain text TXT files
```

```
% blatt convert -h
Usage: blatt convert [OPTIONS] PAGE_FOLDER TEXT_FOLDER

  blatt convert: converts all PAGE XML files in PAGE_FOLDER to TXT files in
  TEXT_FOLDER.

Options:
  -lb, --linebreak BOOLEAN  If linebreak==False, it removes hyphens at the end
                            of lines and merges the lines without line breaks.
                            Otherwise, it merges the lines using line breaks.
                            [default: False]
  -h, --help                Show this message and exit.
```