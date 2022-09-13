from lxml import etree as ET
from pprint import pformat
from typing import List, Tuple
from pathlib import Path
from segtok.segmenter import split_multi
import csv


class Page:
    """
    Class Page: Reads PAGE XML file. Stores TextRegions, TextLines and Baseline coordinates.
    Removes hyphens from the text lines. Computes the coordinates of the mid-range average of baseline points.
    Saves plain text with or without line breaks to TXT file. Splits plain text into sentences and saves it as TSV.
    """

    def __init__(self, filename: Path = ''):
        if filename:
            self.tree, self.root, self.namespace = self._open_page_xml(filename)
            self.filename: Path = filename
            self.text_regions: List
            self.text_regions_xml = [e for e in self.root.iter("{%s}TextRegion" % self.namespace)]
            self.text_lines: List
            self.text_lines_xml = [e for e in self.root.iter("{%s}TextLine" % self.namespace)]
            self._parse_page_xml()
            self.text_with_linebreaks = '\n'.join(self.text_lines)
            self.text_without_linebreaks = self.remove_hyphens(self.text_lines)
            self.sentences = self.split_sentences(self.text_without_linebreaks)
            self.baselines: List
            self.x_baselines: List
            self.y_baselines: List
            self.center_baseline: List
            self._compute_baselines()
            self.attribute_length = [(k, len(v)) for k, v in self.__dict__.items() if k != 'tree']
        else:
            raise ValueError('Empty filename. Specify the proper filename of a PAGE XML file.')

    def __repr__(self):
        return pformat(self.attribute_length)

    def __str__(self):
        return pformat(self.attribute_length)

    @staticmethod
    def _open_page_xml(filename: Path = '') -> Tuple[ET.Element, ET._ElementTree, str]:
        """Opens a PAGE XML file and returns its tree, root and namespace."""
        tree = ET.parse(filename)
        root = tree.getroot()
        namespace = tree.xpath('namespace-uri(.)')
        if 'http://schema.primaresearch.org/PAGE/gts/pagecontent/' not in namespace:
            raise ValueError('The PAGE XML namespace is missing in the xml-file.')
        return tree, root, namespace

    def _parse_page_xml(self):
        """Parses TextRegions, TextLines and Baselines. Adds them to the corresponding attributes."""
        self.text_regions, self.text_lines, self.baselines = [], [], []
        for text_region_id, text_region in enumerate(self.root.iter('{%s}TextRegion' % self.namespace)):
            for text_line in text_region.findall('{%s}TextLine' % self.namespace):
                text_line_id = text_line.attrib['id']
                try:
                    text_line_bs = text_line.find('{%s}Baseline' % self.namespace).attrib['points']
                except (Exception,):
                    print('Warning! No "Baseline points" for "TextLine id"=' +
                          text_line_id + ' in "file"=' + Path(self.filename).name)
                coordinates = [c.split(',') for c in text_line_bs.split(' ')]
                coordinates = [[int(c[0]), int(c[1])] for c in coordinates]
                self.baselines.extend(coordinates)
                for text_equiv in text_line.findall('{%s}TextEquiv' % self.namespace):
                    try:
                        line = text_equiv.find('{%s}Unicode' % self.namespace).text
                        if not line:
                            line = ''
                        self.text_regions.append([line, text_region_id, text_line_id, coordinates])
                        self.text_lines.append(line)
                    except (Exception,):
                        pass
        if all(line is None for line in self.text_lines):
            raise ValueError("The PAGE XML file contains only empty TextLines.")

    def _compute_baselines(self):
        """Returns X & Y baseline coordinates. Computes the coordinates of the mid-range average of baseline points."""
        self.x_baselines = [coord[0] for coord in self.baselines]
        self.y_baselines = [coord[1] for coord in self.baselines]
        self.center_baseline = [(max(self.x_baselines) + min(self.x_baselines)) / 2,
                                (max(self.y_baselines) + min(self.y_baselines)) / 2]

    @staticmethod
    def remove_hyphens(lines: list) -> str:
        """
        Removes hyphens from OCR-ed lines stored in a list. Returns plain text.
        The hyphens are taken from the OCR-D guidelines for hyphenation:
        https://ocr-d.de/en/gt-guidelines/trans/trSilbentrennung.html.
        """
        hyphens = ['-', '-', '⹀', '⸗']
        text = lines[0]
        for i, line in enumerate(lines[:-1]):
            if line:  # only for non-empty strings
                if line[-1] in hyphens:
                    if lines[i + 1][0].isupper():
                        text += lines[i + 1]
                    else:
                        text = text[:-1] + lines[i + 1]
                else:
                    text += ' ' + lines[i + 1]
        return text

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        """Splits input plain text into sentences using the SegTok library https://github.com/fnl/segtok"""
        return list(split_multi(text))

    def to_txt(self, filename: Path, linebreak: bool = False):
        """Saves TextLines as plain text into filename. If linebreak==True, the lines are separated by line breaks.
        Otherwise, the plain text contains no line breaks and hyphens [this is default]."""
        with open(filename, 'w') as f:
            if linebreak:
                f.write(self.text_with_linebreaks)
            else:
                f.write(self.text_without_linebreaks)

    def to_tsv(self, filename: Path, sentence: bool = False):
        """If sentence==False [default], it saves TextLines, TextRegionID, TextLineID and Coordinates to TSV.
        Otherwise, it saves sentences (not lines!) into separate lines of TSV. The sentences are split from the plain
        text without hyphens using the SegTok library. """
        with open(filename, 'w', newline='') as f:
            if sentence:
                tsv = csv.writer(f, delimiter="\n")
                tsv.writerow(self.sentences)
            else:
                tsv = csv.writer(f, delimiter='\t')
                tsv.writerows(self.text_regions)
