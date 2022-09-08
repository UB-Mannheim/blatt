import click
from .page import Page
from pathlib import Path
from tqdm import tqdm

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group()
def cli():
    """Blatt CLI: NLP-helper for OCR-ed pages in PAGE XML format. To get help for a particular COMMAND, use `blatt
    COMMAND -h`. """


@cli.command('convert', short_help='Converts PAGE XML files to plain text TXT files', context_settings=CONTEXT_SETTINGS)
@click.option('--linebreak',
              '-lb',
              type=bool,
              default=False,
              show_default=True,
              help="If linebreak==False, it removes hyphens at the end of lines and merges the lines without line "
                   "breaks. Otherwise, it merges the lines using line breaks.")
@click.argument('page_folder', type=click.Path(exists=True))
@click.argument('text_folder', type=click.Path())
def convert(page_folder, text_folder, linebreak):
    """blatt convert: converts all PAGE XML files in PAGE_FOLDER to TXT files in TEXT_FOLDER."""
    file_paths = Path(page_folder).glob('*.xml')
    for file_path in tqdm(file_paths):
        output_file = Path(text_folder, file_path.stem + '.txt').as_posix()
        p = Page(file_path.as_posix())
        p.to_txt(output_file, linebreak)


if __name__ == '__main__':
    cli()
