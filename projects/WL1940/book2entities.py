import pandas as pd
from tqdm import tqdm
from blatt import Page
from pathlib import Path
import difflib
import numpy as np
import csv

# these values are needed for merging and splitting segments
MAXDY0 = 59  # Maximal difference in Y0 between the lines for merging segments #
MINDY0 = 80   Minimal difference in Y0 between the lines for splitting segments # 40 for 1940; 45 for 1941-1942

# paths = ['./wer_leitet/page-xml-40/516401084_19400001_aanm3ed.pdf_page_' + str(n) + '.xml' for n in range(19,1043)]
paths = ['./wer_leitet/page-xml-41-42/516401084_' + str(n).zfill(4) + '.xml' for n in range(21,1183)]

paths = [p for p in paths if Path(p).is_file()]
paths = [p for p in paths if Path(p).stat().st_size >=50000]
paths = [p for p in paths if not p.endswith('146.xml')]

class PageTwoColumns(Page):
    def __init__(self, *args):
        super(PageTwoColumns, self).__init__(*args)
        self.process_2columns()

    def process_2columns(self):
        # Separate into left and right columns
        for i, line in enumerate(self.text_regions):
            if line[3][0][0] <= self.center_baseline[0]:
                line.append('left')
            else:
                line.append('right')
        df = pd.DataFrame(self.text_regions,
                          columns=['Line', 'TextRegionID', 'Line_ID',
                                   'Baseline_coords', 'Column'])
        df.index.name = 'Index'
        df['X0'] = df['Baseline_coords'].apply(lambda x: x[0][0])
        df['Y0'] = df['Baseline_coords'].apply(lambda x: x[0][1])
        df['Y1'] = df['Baseline_coords'].apply(lambda x: x[1][1])
        df['Ym'] = (df['Y0'] + df['Y1']) * 0.5
        df = df.sort_values(by=['Column', 'Ym', 'X0'])
        df = df.dropna(subset=['Line'])  # Remove None lines
        df['dY0'] = df['Y0'].shift(-1) - df['Y0']
        df = df.reset_index()

        # Set 'SegmentID' for different segments. Don't use TextRegionID like this:
        # df['SegmentID'] = df['TextRegionID'].apply(lambda x: list(dict.fromkeys(df['TextRegionID'])).index(x))
        df['Segmentation'] = (df['dY0'].apply(lambda x: True if abs(x) >= MINDY0 else False))
        # first two lines of segments cannot be with ':'
        for i in range(0, 2):
            if ((df['Segmentation'].loc[i] == True) & (':' in df['Line'].loc[i])) and (
                    df['Line'].loc[i] != 'Eigene Vertretungen im Ausland: Kowno, Riga.'):
                df['Segmentation'].loc[i] = False

        segid = 0
        df['SegmentID'] = ''
        for i, seg in df['Segmentation'].items():
            df['SegmentID'].loc[i] = segid
            if seg:
                segid += 1

        # 'Removing headers': if two consequent rows refer to new segments, remove the second row
        df.drop(df[(df['Segmentation'] == True) & (df['Segmentation'].shift(1) == True)].index, inplace=True)

        # Replace artefacts
        df.replace(':.', ': ', inplace=True, regex=True)
        df.replace(':-', ': ', inplace=True, regex=True)

        # Replace exceptions
        words = ['Simplex Vervielfältiger jetzt:', 'Kratzenfabrik „Ankermarke:e',
                 'Kratzenfabrik „Ankermarke: ']
        for word in words:
            df.replace(word, word.replace(':', ''), inplace=True, regex=True)

        # find the index of the first row in the right column
        right_col = df[(df['Column'] == 'right') &
                       (df['Column'].shift(1) == 'left')].index[0]

        # Drop headers at a page
        if ' — ' in df['Line'].loc[right_col]:
            df.drop(index=(right_col), inplace=True)
        if ' — ' in df['Line'].loc[0]:
            df.drop(index=(0), inplace=True)
        if 0 in df.index:
            df = df.reset_index()
            if df['TextRegionID'].loc[0] != df['TextRegionID'].loc[1]:
                df.drop(index=(0), inplace=True)

        # Remove artefacts, special cases
        if 'vec.' in df[df['SegmentID'] == df['SegmentID'].max()]['Line'].tolist():
            df.drop(list(df[df['SegmentID'] == df['SegmentID'].max()].index), inplace=True)

        # Remove the last segment if it contains only numeric values (e.g.,
        # page numbers) or all lines are shorter than 4 characters
        if all(df[df['SegmentID'] == df['SegmentID'].max()]['Line'].str.isnumeric()) or \
                all(df[df['SegmentID'] == df['SegmentID'].max()]['Line'].str.len() < 4):
            df = df.drop(df[df['SegmentID'] == df['SegmentID'].max()].index)

        # Find the index of the first row in the right column
        df = df.reset_index()
        right_col = df[(df['Column'] == 'right') &
                       (df['Column'].shift(1) == 'left')].index[0]

        # Merge the bottom-left with upper-right TextRegions
        if (all(df['dY0'][right_col:right_col + 2] <= MAXDY0) or all(
                df['Line'][right_col:right_col + 1].str.contains(':'))) and (
                df['Line'][right_col] not in ['Richard Weber & Co.,']):
            df['SegmentID'].replace(df['SegmentID'][right_col + 1],
                                    df['SegmentID'][right_col - 1],
                                    inplace=True)

        # Normalize segment counts
        if df['SegmentID'].min() == 1:
            df['SegmentID'] = df['SegmentID'] - 1

        df.drop(['index', 'Index'], axis=1, inplace=True)  # Remove redundant index

        self.dataframe = df
        segments = {}
        for sid in set(df['SegmentID']):
            segments[self.filename + '_' + str(sid)] = df[df['SegmentID'] == sid][
                ['Line', 'Line_ID', 'dY0']].values.tolist()
        self.segments = segments
        self.dY0 = df['dY0'].tolist()


class Entities:
    """
    Class Entities: Takes list of paths to page-xml files, executes Page() on them,
    merge segments from consequent pages, removes hyphens and extracts entities.
    """

    def __init__(self, paths=[]):
        self.read_files(paths)
        self.merge_segments()
        self.get_entities()

    def __repr__(self):
        return "Pages list of (attribute, length): " + str([(k, len(v)) for k, v in self.__dict__.items()])

    def __str__(self):
        return 'An object of Pages()'

    def read_files(self, paths):
        d = {}
        for i, path in tqdm(enumerate(paths)):
            d[i + 1] = PageTwoColumns(path)
        self.d = d

    def merge_segments(self):
        segments = {}
        for p in self.d.values():
            segments = {**segments, **p.segments}
        # Merge segments from different pages
        idx = []
        for k, v in segments.items():
            if k.endswith('0'):
                try:
                    if ((v[0][2] <= MAXDY0 and v[1][2] <= MAXDY0) or (':' in v[0][0] and ':' in v[1][0])):
                        segments[list(segments.keys())[list(segments.keys()).index(k) - 1]].extend(v)
                        idx.append(k)
                except Exception as e:
                    print(k,v,e)
        for i in idx:
            del segments[i]
        self.segments = segments
        s, m = {}, {}
        for k, v in self.segments.items():
            s[k] = '\n'.join([k[0] for k in v])
            m[k] = Page.remove_hyphens([k[0] for k in v])
        self.segments_text = s
        self.segments_text_unhyphenated = m

    def unhyphenate(self, txt=list):
        """ Removes hyphens from OCR-ed strings stored in a list
        Check out the OCR-D guidelines for hyphenation:
        https://ocr-d.de/en/gt-guidelines/trans/trSilbentrennung.html
        RETURNS list of strings, where the strings, ended with hyphens, were merged
        """
        hyphens = ['-', '-', '⹀', '⸗', '']
        new = [txt[0]]
        for i, line in enumerate(txt[:-1]):
            if line:
                if line[-1] in hyphens:
                    if txt[i + 1]:
                        if txt[i + 1][0].isupper() and (':' not in txt[i + 1]):
                            new[-1] += txt[i + 1]
                        if txt[i + 1][0].islower() and (':' not in txt[i + 1]):
                            new[-1] = new[-1][:-1] + txt[i + 1]
                else:
                    new.append(txt[i + 1])
        return new

    @staticmethod
    def _conditions(k):
        return (':' in k) and \
               ('stellv.' not in k.split(':', 1)[0].lower()) and \
               (not any(t.isdigit() for t in k.split(':', 1)[0])) and \
               (k.split(':', 1)[0] not in [''])

    def get_entities(self):
        s = {}
        for k, v in self.segments.items():
            s[k] = self.unhyphenate([k[0] for k in v])
        entities = {}
        for k, v in s.items():
            v = [m.replace('::', ':') for m in v if m]  # Only non-None
            sis = [i for i, k in enumerate(v) if self._conditions(k)]
            if sis:  # Don't take exceptions with 'Inhaber:' in a company name
                if v[sis[0]].startswith('Inhaber:'):
                    del sis[0]
            METADATA = {'FILE_SEGMENT': k}
            if sis:
                entities[joiner(v[0:sis[0]])] = [METADATA]
                for i, si in enumerate(sis):
                    if (i < len(sis) - 1) and (sis[i] + 1 == sis[i + 1]):
                        entities[joiner(v[0:sis[0]])].append(
                            {v[si].split(': ', 1)[0]: joiner(v[si].split(': ', 1)[1:])})
                    elif (i == len(sis) - 1):
                        entities[joiner(v[0:sis[0]])].append(
                            {v[si].split(': ', 1)[0]: joiner(v[si].split(': ', 1)[1:]) +
                                                      ' ' + joiner(v[si + 1:len(v)])})
                    else:
                        entities[joiner(v[0:sis[0]])].append(
                            {v[si].split(': ', 1)[0]: joiner(v[si].split(': ', 1)[1:]) +
                                                      ' ' + joiner(v[si + 1:sis[i + 1]])})
            else:
                if v:
                    entities[v[0]] = [METADATA]

        ents = {}
        for key, val in entities.items():
            ents[key] = {k: v for d in val for k, v in d.items()}
            ents[key]['LENGTH'] = [len(ents[key]), len(val)]
        self.entities = ents


def joiner(x):
    """Helper join-function"""
    if len(x) == 0:
        return ''
    if len(x) == 1:
        return x[0]
    if len(x) > 1:
        return ' '.join(x)


pages = Entities(paths)

# Postprocessing
entities = pages.entities
