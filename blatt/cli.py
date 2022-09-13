import click
from .page import Page
from pathlib import Path
from tqdm import tqdm

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def cli():
    """Blatt CLI: NLP-helper for OCR-ed pages in PAGE XML format. To get help for a particular COMMAND, use `blatt
    COMMAND -h`. """


@cli.command('to_txt',
             short_help='Converts PAGE XML files to TXT files with or without line breaks & hyphens',
             context_settings=CONTEXT_SETTINGS)
@click.option('--linebreak',
              '-lb',
              type=bool,
              default=False,
              show_default=True,
              help="If linebreak==False, it removes hyphens at the end of lines and merges the lines without line "
                   "breaks. Otherwise, it merges the lines using line breaks.")
@click.argument('page_folder', type=click.Path(exists=True))
@click.argument('txt_folder', type=click.Path())
def to_txt(page_folder, txt_folder, linebreak):
    """blatt to_txt: converts all PAGE XML files in PAGE_FOLDER to TXT files with/without hyphens in TEXT_FOLDER."""
    file_paths = Path(page_folder).glob('*.xml')
    for file_path in tqdm(file_paths):
        output_file = Path(txt_folder, file_path.stem + '.txt').as_posix()
        p = Page(file_path.as_posix())
        p.to_txt(output_file, linebreak)


@cli.command('to_tsv',
             short_help='Converts PAGE XML files to TSV files with TextLines or sentences',
             context_settings=CONTEXT_SETTINGS)
@click.option('--sentence',
              '-s',
              type=bool,
              default=False,
              show_default=True,
              help="If sentence==False, it saves TextLines, TextRegionID, TextLineID and Coordinates to TSV. "
                   "Otherwise, it saves sentences (not lines!) into separate lines of TSV. The sentences are split " 
                   "from the plain text without hyphens using the SegTok library.")
@click.argument('page_folder', type=click.Path(exists=True))
@click.argument('tsv_folder', type=click.Path())
def to_tsv(page_folder, tsv_folder, sentence):
    """blatt to_tsv: converts all PAGE XML files in PAGE_FOLDER to TSV files in TSV_FOLDER."""
    file_paths = Path(page_folder).glob('*.xml')
    for file_path in tqdm(file_paths):
        output_file = Path(tsv_folder, file_path.stem + '.tsv').as_posix()
        p = Page(file_path.as_posix())
        p.to_tsv(output_file, sentence)


if __name__ == '__main__':
    cli()
