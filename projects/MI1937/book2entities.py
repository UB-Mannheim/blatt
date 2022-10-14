import csv
import difflib
import json
from collections import defaultdict
from glob import glob
from typing import List

import numpy as np
import pandas as pd
import regex
from tqdm import tqdm

from blatt import Page

# these values are needed for merging and splitting segments
MAXDY0 = 59  # Maximal difference in Y0 between the lines for merging segments # 65 = 5104; 59 = 5112
MINDY0 = 86  # 96  # Minimal difference in Y0 between the lines for splitting segments
# 115 => 4969; 100 => 5085; 90 => 5104

paths = ['./data/maschinenindustrie_1937_' + str(n).zfill(4) + '.xml' for n in range(6, 654)]
#paths = sorted(glob('./data/*.xml'))[5:653]


class PageTwoColumns(Page):
    def __init__(self, *args):
        super(PageTwoColumns, self).__init__(*args)
        self.dataframe = None
        self.segments = {}
        self.dY0 = []
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
            if ((df.loc[i, 'Segmentation'] == True) & (':' in df['Line'].loc[i])) and (
                    df.loc[i, 'Line'] != 'Eigene Vertretungen im Ausland: Kowno, Riga.'):
                df.loc[i, 'Segmentation'] = False

        # Exceptions
        try:
            df.loc[df[df['Line'].isin(['Zittau, Friedländerstr. 10/12.',
                                       'Schönebecker Str. 8.',
                                       'Staufen i. Breisgau.',
                                       'Augsburg, Im Sack G 273/74.',
                                       'München N 23, Soxhletstraße 1.',
                                       'Berlin S 42, Prinzenstr. 21.'])].index[:], 'Segmentation'] = False
        except Exception:
            pass

        segid = 0
        df['SegmentID'] = ''
        for i, seg in df['Segmentation'].items():
            df.loc[i, 'SegmentID'] = segid
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
            df.drop(index=right_col, inplace=True)
        if ' — ' in df['Line'].loc[0]:
            df.drop(index=0, inplace=True)
        if 0 in df.index:
            if df['TextRegionID'].loc[0] != df['TextRegionID'].loc[1]:
                df.drop(index=0, inplace=True)

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
        if (all(df['dY0'].loc[right_col:right_col + 2] <= MAXDY0) or all(
                df['Line'].loc[right_col:right_col + 1].str.contains(':'))) and (
                df['Line'].loc[right_col] not in ['Richard Weber & Co.,']):
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
            segments[str(self.filename) + '_' + str(sid)] = df[df['SegmentID'] == sid][
                ['Line', 'Line_ID', 'dY0']].values.tolist()
        self.segments = segments
        self.dY0 = df['dY0'].tolist()


class Entities:
    """
    Class Entities: Takes list of paths to page-xml files, executes Page() on them,
    merge segments from consequent pages, removes hyphens and extracts entities.
    """

    def __init__(self, paths: List[str]):
        self.entities = {}
        self.d = {}
        self.segments = None
        self.segments_text = None
        self.segments_text_unhyphenated = None
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
                if ((v[0][2] <= MAXDY0 and v[1][2] <= MAXDY0) or (':' in v[0][0] and ':' in v[1][0])):
                    segments[list(segments.keys())[list(segments.keys()).index(k) - 1]].extend(v)
                    idx.append(k)
        for i in idx:
            del segments[i]
        self.segments = segments
        s, m = {}, {}
        for k, v in self.segments.items():
            s[k] = '\n'.join([k[0] for k in v])
            m[k] = Page.remove_hyphens([k[0] for k in v])
        self.segments_text = s
        self.segments_text_unhyphenated = m

    @staticmethod
    def unhyphenate(txt: List[str]):
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
               (k.split(':', 1)[0] not in ['', 'von', 'Speyer a. Rh.', 'Abt. II',
                                           'firmiert', '—Borsigwalde G. m. b. H., Berlin. — Zweck',
                                           'Düsseldorf-Grafenberg', 'ohne Demontage. Werk II',
                                           'A. Riedinger)', 'Nürnberg',
                                           'Meißel-, Pfahl- u. Spundwandrammen (Arbeitsgewichte',
                                           'Bln.-Kladow, Kladower Schanze (Prokurist',
                                           'Betonwaren. (Spez.', 'Werk Siegmar',
                                           'Schmiedestücke, roh u. bearbeitet; b) für den Bergbau',
                                           'Eisemann-Werke A.-G., Stuttgart. — A.-K.',
                                           'Rheinhausen/Niederrh. — Kohlenzechen',
                                           'Gleisanschlus. — Werk IV', 'rulagen',
                                           'Webschützen', 'jetzt', 'darunter', '& Co. A.-G.)',
                                           'Konstanz, übernommen. — Unionwerke A.-G.',
                                           'Karl Laux, Bln.-Kladow; Fernruf', 'Rotterdam',
                                           'elektrische u. autogene Schweißerei. Gießerei',
                                           'Street (Tel.', 'Cainsdorf i. Sachsen (Königin Marienhütte)',
                                           'Fabrikation. Gleisanschluß. — Werk II',
                                           'Leipzig', 'Kunstharzpresserei, Landmaschinen (Spez.',
                                           'Enzinger Werke A.-G.', 'Werk Gustavsburg',
                                           'Werk Nürnberg', 'ölhärtbar. — Siemens-Martin-Stahlschienen. Sonderheit',
                                           'Wettlaufer, Dir. Asshauer (Zweigbüro',
                                           '„Buschmann“ D.R. P. Sonderheiten der Maschinenfabrik',
                                           'Werke der V. E. S.', 'an', 'Inh.',
                                           'A. K.', 'aus Stahl', 'Hof u. Garten. — Landmaschinen',
                                           'Fernseh A.-G., Berlin. — A.-K.',
                                           'Karl Hupe. — Weitere Prokuristen',
                                           'Werk Lampertsheim', 'Maschinenfabrik, Gießerei. — Werk Eschweiler',
                                           'Lokomobilanlage. — Werk Gößnitz',
                                           'Luftpumpen, Vorwärmer. Getränke-Industrie',
                                           'Wolfgang Schleicher, Hirschberg; Geschäftsleiter',
                                           'Lüftungsanlagen. — Werk Hamburg',
                                           'Fritz Finckh. — Betriebsdir.', 'Schanghai; Inland',
                                           'Bronzen; Nickellegierungen. Leichtmetalle',
                                           'zur Bearbeitung sämtlicher metallischer Werkstoffe, wie',
                                           'Dampfkühler; Entöler. Entaschungsanlagen',
                                           'H. F. Baumann aufgekauft, der seither firmiert',
                                           '(Hobelmaschinen); ferner'
                                           ])

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
                    elif i == (len(sis) - 1):
                        entities[joiner(v[0:sis[0]])].append(
                            {v[si].split(': ', 1)[0]: joiner(v[si].split(': ', 1)[1:]) +
                                                      ' ' + joiner(v[si + 1:len(v)])})
                    else:
                        entities[joiner(v[0:sis[0]])].append(
                            {v[si].split(': ', 1)[0]: joiner(v[si].split(': ', 1)[1:]) +
                                                      ' ' + joiner(v[si + 1:sis[i + 1]])})
            else:
                v[1] = v[1].replace('siche', 'siehe').replace('sieh ', 'siehe ')  # Fixing an OCR-error
                v[1] = v[1].replace('siene', 'siehe').replace('siebe ', 'siehe ')  # Fixing an OCR-error
                v[1] = v[1].replace('sjehe', 'siehe')  # Fixing an OCR-error
                try:
                    ind = [i for i, e in enumerate(v) if 'siehe ' in e]
                    entities[joiner(v[:ind[0]])] = [METADATA, {'siehe': joiner(v).split('siehe ')[1]}]
                except Exception:
                    entities[joiner(v)] = [METADATA, {'OHNE_siehe': joiner(v)}]

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
for key, value in entities.items():
    value['RAW_TEXT'] = pages.segments_text[value['FILE_SEGMENT']]
    value['RAW_TEXT_1LINE'] = pages.segments_text_unhyphenated[value['FILE_SEGMENT']]
table = pd.DataFrame(entities).T.reset_index().fillna('')
table = table.rename(columns={'index': 'Company'})
table.replace('-a--, Gebrüder Neunert Maschinenfabrik, Elmshorn b. Hbg., Ollnsstr. 35.',
              'Gebrüder Neunert Maschinenfabrik, Elmshorn b. Hbg., Ollnsstr. 35.',
              inplace=True)
table['Kapital'].replace('—.', '', regex=True, inplace=True)
table['Kapital'].replace('—', '', regex=True, inplace=True)
table['Gründung'] = table['Gründung'].apply(lambda s: s.rstrip('.'))
table['Inhaber'] = table['Inhaber'].apply(lambda s: s.rstrip('.'))

# SAVE RAW TABLE
table.to_excel("MI1937_raw.xlsx", sheet_name='Maschinenindustrie_1937_raw')
table.to_csv("MI1937_raw.csv", sep=',', quoting=csv.QUOTE_ALL)
table.describe()

## Quality checks

# Print entities with repeating properties
for k, v in pages.entities.items():
    if v['LENGTH'][0] != v['LENGTH'][1]:
        print(v['LENGTH'], k, '   ', v['FILE_SEGMENT'])

# Sorting and grouping the properties
properties = sorted(table.columns.to_list())
props = table.describe().T.reset_index()
prop_groups = {}
for prop in properties:
    prop_groups[prop] = frozenset(difflib.get_close_matches(prop, properties, n=30, cutoff=0.65))
unique_prop_groups = []
for prop in set(prop_groups.values()):
    unique_prop_groups.append(set(prop))

# Manually curated groups of properties
prop_sets = {}
prop_sets['EIGENE VERTRETUNGEN'] = {'Vertretungen', 'Generalvertretungen',
                                    'Bezirksvertretungen', 'Generalvertretungen im Ausland', 'Generalvertretung',
                                    'Eigene Vertretungen im Inland', 'Eigene Vertretung in Berlin',
                                    'Bigene Vertretungen im Ausland', 'Eigene Vertretungen in',
                                    'Eigene Vertrétung im Ausland',
                                    'Eigene Vertretungen im Auslande', 'Eigene Vertretungen im Ansland',
                                    'Eigene Vertretungen im In- u. Ausland', 'Eigene Vertretung in Essen',
                                    'Eigene Vetretungen im Ausland', 'Eigene Vertretungen im Ausland',
                                    'Vertretung im Ausland',
                                    'Bigene Vertretung in Berlin', 'Eigene Vertetung in Berlin',
                                    'Eigene Vertretung im Ausland',
                                    'Eigene Vertretungen in Berlin', 'Eigene Vertretung in Ausland',
                                    'Eigene Vertretungen in Berlin u. im Ausland',
                                    'Eigene Vertretungen in Berlin und im Ausland',
                                    'Eigene Vertretungen in Deutschland u. im Ausland:',
                                    'Generalvertretungen im Ausland', 'Vertretungen im Ausland',
                                    'Eigene Büros und Vertretungen',
                                    'Eigene Niederlassung in Berlin', 'Eigene Vertetung', 'Eigene Vertretung',
                                    'Eigene Vertretung für Munitionsmaschinen', 'Eigene Vertretungen',
                                    'General-Vertretung in Berlin',
                                    'Vertretung in Berlin', 'Vertretungen in Berlin', 'eigene Vertretungen in',
                                    'Eigene Niederlassung im Ausland', 'Vertretungen im In- u. Ausland'}

prop_sets['POSTSCHECK-KONTO'] = {'Postscheck-Konto ', 'Postseheck-Konto',
                                 'PostscheckKonto', 'Postscheck-Konnto', 'Fostscheck-Konto',
                                 'Postcheck-Konto', 'Postscheek-Konto', 'Potscheck-Konto',
                                 'Postscbeck-Konto', 'Postscheckkonto', 'Postschek-Konto',
                                 'Postscheck-Konten', 'Ponstscheck-Konto', 'Postscheck-Konto'}

prop_sets['GESCHÄFTSJAHR'] = {'Geschäftjahr', 'Geschäftsjahr', 'Gescbäftsjahr',
                              'Geschätfsjahr', '.Geschäftsjahr'}

prop_sets['GESCHÄFTSFÜHRER'] = {'Geschäftsführer', 'Geschäftsleiter', 'Geschaftsführer',
                                'Geschäftsieiter', 'Géschäftsführer', 'Geschäftsführerin',
                                'Komplementär und Geschäftsführer', 'Kaufm. Leiter',
                                'Gesellschafter u. Geschäftsführer', 'Geschäftsleitung',
                                'Anteileigner u. Geschäftsführer', 'Geschäftleiter',
                                'Anteileigner und Geschäftsführer', 'Kaufm. Geschäftsleiter',
                                'Kaufm. Direktor', 'Kaufm. Leiter', 'Direktor', 'Leiter',
                                'Betriebsführer', 'Leitung', 'Betriebsleiter',
                                'Inhaber und Geschäftsführer', 'Inhaber u. Geschäftsführer'}

prop_sets['FILIALE'] = {'Filialen', 'Filiale'}

prop_sets['GESCHÄFTSSTELLE'] = {'Geschäftsstelle', 'Geschäftsstellen'}

prop_sets['INHABER'] = {'Inhaber', 'Alleininhaber', 'Geschäftsinhaber',
                        'Inhaber (bzw. Gesellschafter)', 'Alleiniger Inhaber'}

prop_sets['BEVOLLMÄCHTIGTE'] = {'Handelsbevollmächtigte', 'Bevollmächtigte', 'Bevollmächtigter',
                                'Handlungsbevollmächtigte', 'Generalbevollmächtigter',
                                'Handlungsbevollmächtigter', 'Generalbevollmächtigte'}

prop_sets['SPEZIALITÄT'] = {'Arten. Spezialität', 'Eisenpulver. Spezialität',
                            'als Spezialität', '(Spezialität', 'Rastatt (Spezialität',
                            'Spezialität', 'Dampf. Spezialität', 'u. Industrie. Spezialität',
                            'Lederindustrie. Spezialität', 'Rastatt (Spezialität',
                            'Feuerungsanlagen. Spezialität', 'Kunststein-Industrie. Spezialität',
                            'pharmazeutische Industrie (Spezialität', 'Formen für die Gummi-Industrie. Spezialität',
                            'jeden Brennstoff. Spezialität', 'Feuerungsanlagen. Spezialität',
                            'Lederindustrie. Spezialität'}

prop_sets['BANKVERBINDUNGEN'] = {'Bankverbindungen:', 'Bankverbindunng', 'Bankvérbindungen',
                                 'Bankverbindngen', 'Bankverbiadung', 'Bankverbindungen', 'Bankverbindung'}

prop_sets['NIEDERLASSUNGEN'] = {'A.-G., Zweigniederlassungen', 'Niederlassungen',
                                'Zweigniederlassung', 'Zweigniederlassungen', 'Fabrikniederlassung Berlin',
                                'Verkaufsniederlassungen', 'Niederlassung'}

prop_sets['PROKURISTEN'] = {'Prokurist', 'Einzelprokurist', 'Gesamt-Prokuristen',
                            'Prokuristen', 'Prokuristin', 'Pokurist'}

prop_sets['PROKURIST DER ZWEIGNIEDERLASSUNG'] = {'Prokurist der Zweigniederlassung Sonthofen',
                                                 'Prokurist der Zweigniederlassung'}

prop_sets['GRUNDBESITZ'] = {'Grundbesitz', 'Grunabesitz', 'Gründbesitz', 'Ges. Grundbesitz', 'Grundbesitz:'}

prop_sets['DRAHTANSCHRIFT'] = {'Drahtanschriften:', 'Drahtanschrift'}

prop_sets['POSTANSCHRIFT'] = {'(Postanschrift', 'Briefanschrift'}

prop_sets['TOCHTERGESELLSCHAFTEN'] = {'Tochtergeselschaft', 'Schwestergesellschaften',
                                      'Tochtergesellschaften:', 'Tochtergesellschaft',
                                      'Schwestergesellschaft', 'Tochtergesellschaften und Beteiligungen',
                                      'Tochtergesellschaften'}

prop_sets['FABRIKATIONSPROGRAMM'] = {'Fabfikationsprogramm', 'Fabrikationprogramm',
                                     'Fabrikationsproramm', 'Fabrikationsprogramm:',
                                     'Fabrikstionsprogramm', 'Fabrkkationsprogramm',
                                     'Fabrikationsprogramm'}

prop_sets['AKTIONÄRE'] = {'Aktionäre', 'Großaktionär', 'Groß-Aktionäre', 'Aktionär',
                          'Hauptaktionär', 'Großaktionäre'}

prop_sets['BETEILIGUNGEN'] = {'Beteiligung', 'RM; Beteiligung', 'Beteiligungen',
                              'Sonstige Beteiligungen'}

prop_sets['FABRIKATIONSANLAGEN'] = {'Fabrikanlagen in', 'Fabrikationsanlagen'}

prop_sets['VERKAUFSBÜRO'] = {'Verkaufsbüro', 'Verkaufsbüro und Lager', 'Eigene Verkaufsbüros'}

prop_sets['VERKAUFSSTELLEN'] = {'Eigene Verkaufsstellen', 'eigene Verkaufsstellen in'}

prop_sets['ANLAGEN'] = {'Anlagen', 'Besondere Anlagen', 'Betriebsanlagen',
                        'Anlagen (in Teltow b. Berlin)', 'Anlage',
                        'Anlagen jedweder Art'}

prop_sets['ANGESTELLTE'] = {'Angestellte'}

prop_sets['ANGABEN'] = {'Weitere Angaben', 'Besondere Angaben'}

prop_sets['WERK DÜSSELDORF'] = {'Werk Düsseldorf', 'für Werk Düsseldorf'}

prop_sets['KOMMANDITISTEN'] = {'Kommanditisten', 'Kommanditist'}

prop_sets['NUTZFLÄCHE'] = {'Nutzfläche', 'qm Nutzfläche; gesamte Nutzfläche',
                           'Fläche; gesamte Nutzfläche',
                           'gesamte Nutzfläche', 'qm bebaut; gesamte Nutzfläche'}

prop_sets['FIRMA GEHÖRT'] = {'Firma gehört folgendem Konzern an',
                             'Firma gehört folgender Interessengemeinschaft an:',
                             'Firma gehört folgendem Konzern', 'Firma gehört folgenden Konzernen an',
                             'Firma gehört an'}

prop_sets['KAPITAL'] = {'Stamm-Kapital', 'Kaßital', 'Kapital', 'Stammkapital',
                        'Aktienkapital', 'Gründungskapital'}

prop_sets['ZWEIGBÜROS'] = {'Eigene Zweigbüros', 'Zweigbüros', 'Zweig-Büro'}

prop_sets['FERNRUF'] = {'Fernraf', 'Fernruf'}

prop_sets['GEFOLGSCHAFT'] = {'Gefolgschaft', 'Gefolgschaft:'}

prop_sets['GESELLSCHAFTER'] = {'Gesellschafter', 'Persönlich haftender Gesellschafter',
                               'Persönlich haftende Gesellschafter',
                               'Pers. haft. Gesellschafter',
                               'Persönl. haftende Gesellschafter'}

prop_sets['UMSATZ'] = {'Umsatz', 'Umsatz:', 'Umsatz (Mill. RM)',
                       'Umsatz (Maschinenfabrik u. Eisengießerei)'}

prop_sets['ANTEILSEIGNER'] = {'Anteileigner', 'Anteileigener', 'Hauptanteileigner',
                              'Anteileignerin', 'Anteileigher', 'Anteifeigner',
                              'Großanteileigner', 'Vorsitzer'}

prop_sets['AUFSICHTSRAT'] = {'Aufsichtsrat', 'Aufsichtrat', 'Oufsichtsrat'}

prop_sets['KOMPLEMENTÄRE'] = {'Komplementär', 'Komplementäre'}

prop_sets['VERTRÄGE'] = {'Verträge', 'Vertrag'}

prop_sets['BESITZ'] = {'Besitz'}

prop_sets['SITZ'] = {'Sitz'}

matched_props = defaultdict(list)

# Merge values within the groups of properties. Remove then the columns with properties merged already
for key, value in prop_sets.items():
    table[key] = ''
    for v in value:
        if v in table:
            table[key] = table[key] + table[v]
            matched_props[key].append(v)
    for v in value:
        if v in table:
            table.drop(v, axis=1, inplace=True)

# Match with fuzziness
for main_prop, proppatterns in prop_sets.items():
    subprops = []
    for proppattern in proppatterns:
        fuzziness = 1 if len(proppattern) > 5 else 0
        pattern = f'({proppattern.upper().replace("(","").replace(")","")})' + '{s<='+str(fuzziness)+':[A-Z]}'
        for col_name in set(table.keys()).difference(set(prop_sets.keys())):
            res = regex.search(pattern, col_name.upper())
            if res: subprops.append(col_name)
    if subprops:
        print(f"{main_prop}: {subprops}")
        if main_prop not in table:
            table[main_prop] = ''
        for subprop in set(subprops):
            table[main_prop] = table[main_prop] + table[subprop]
            matched_props[main_prop].append(subprop)
            table.drop(subprop, axis=1, inplace=True)


# Extract Drahtanschrift from Fernruf
def drahtanschrift(x):
    for anschrift in ['Drahtanschrift: ', 'Drahtänschrift: ']:
        return x.split(anschrift)[1] if anschrift in x else x


table['FERNRUF'] = table['FERNRUF'].replace('Drahtanschrift;', 'Drahtanschrift:', regex=True)
table['FERNRUF'] = table['FERNRUF'].replace('Drahtanschrift ', 'Drahtanschrift: ', regex=True)
table['DRAHTANSCHRIFT'] = table['DRAHTANSCHRIFT'].astype(bool) * (table['DRAHTANSCHRIFT'] + '; ') + \
                          (table['FERNRUF'].apply(lambda x: drahtanschrift(x)) != table['DRAHTANSCHRIFT']) * table[
                              'FERNRUF'].apply(lambda x: drahtanschrift(x))


# Remove Drahtanschrift from Fernruf
def remove_drahtanschrift(x):
    for anschrift in ['Drahtanschrift: ', 'Drahtänschrift: ']:
        return x.split(anschrift)[0] if anschrift in x else x


table['FERNRUF'] = table['FERNRUF'].apply(lambda x: remove_drahtanschrift(x))
table['FERNRUF'] = table['FERNRUF'].apply(lambda s: s.rstrip('.').rstrip('. '))
table['DRAHTANSCHRIFT'] = table['DRAHTANSCHRIFT'].apply(lambda s: s.rstrip('; '))

# Capitilize column names (those with minor changes or without groups)
table.rename(columns={"Gründung": "GRÜNDUNG",
                      "siehe": "SIEHE",
                      "Vorstand": "VORSTAND"},
             inplace=True)

# Remove all properties with two or less values
props = table.describe().T.reset_index()
#props = props[props['unique'] > 4]
table['DIVERSES'] = ''
matched_props['DIVERSES'] = []
for prop in set(props[props['unique'] <= 4]['index']).difference(set(prop_sets.keys())):
    try:
        table.loc[table[prop].str.len() > 0, 'DIVERSES'].add(f'\n {prop} : ')
        table['DIVERSES'] = table['DIVERSES'] + table[prop]
        matched_props['DIVERSES'].append(prop)
        table.drop(prop, axis=1, inplace=True)
    except Exception:
        continue
else:
    table['DIVERSES'] = table['DIVERSES'].str.strip()

props = table.describe().T.reset_index()
props = props.sort_values(by=['unique'], ascending=False)
cols = props['index'].tolist()
tablet = table[cols]

# Extract the legal forms from 'Company'
# unused_forms = [ 'Gesellschaft', 'Maschinenbauanstalt' ]
# rechtsform['BG'] = ['Baugesellschaft']
# rechtsform['Fabrik'] = ['Fabr.', 'fabrik', 'Fabrik', 'fabr.', 'fbk.']
rechtsform = {'GmbH': ['m. b. H.', 'G. m. b. H.', 'Gesellschaft m. b. H.',
                       'G.m.b. H.', 'Ges. m.b. H.', 'GmbH', 'G. m. b.H.',
                       'mit beschr. Haftung', 'Ges.m.b.H.', 'G.m.b.H.',
                       'GmbH.', 'GmbH'],
              'AG': ['A.-G.', 'Aktien-Gesellschaft', 'Actien-Gesellschaft',
                     'Aktiengesellschaft', 'Akt.-Ges.', 'Aktien-Gesellsch.', 'A. G.'],
              'KG': ['K.-G.', 'Kom.-Ges.', 'Komm.-Ges.', 'KG.', 'Kommanditgesellschaft',
                     'Kom. Ges.', 'Komm.-Ges.'],
              'oHG': ['o. H. G.', 'o. H.-G.'],
              'VDI': ['VDI'],
              'Aktien-Maschinenfabrik': ['Aktien-Maschinenfabrik'],
              'Elektricitäts-Gesellschaft': ['Elektricitäts-Gesellschaft']}


def legal_form(x):
    lforms = []
    for k, v in rechtsform.items():
        if any(a.lower() in x.lower() for a in v):
            lforms.append(k)
    return '; '.join(lforms)


# 1717 entities with legal forms, 3433 without legal forms
tablet['RECHTSFORM'] = tablet['Company'].apply(lambda x: legal_form(x))

# Sort columns and remove dots at the end of strings
cols = tablet.replace('', np.nan).notna().sum().index.tolist()
tablet = tablet[cols]
for col in cols:
    tablet[col] = tablet[col].apply(lambda s: s.rstrip('.').rstrip('. ') if type(s) == str else s)

# SAVE RESULTS
with open("Matched_properties.json", "w") as fout:
    json.dump(matched_props, fout, indent=4)

tablet.to_excel("MI1937_processed.xlsx", sheet_name='Maschinenindustrie_1937_v1')
tablet.to_csv("MI1937_processed.csv", sep=',', quoting=csv.QUOTE_ALL)
tablet.describe()
