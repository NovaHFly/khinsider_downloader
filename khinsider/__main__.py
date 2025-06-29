import argparse
import logging
from collections.abc import Sequence
from pathlib import Path
from pprint import pprint

from khinsider.constants import MAX_CONCURRENT_REQUESTS
from khinsider.decorators import log_time
from khinsider.files import download_many
from khinsider.scraper import get_album, search_albums

logger = logging.getLogger('khinsider')


def construct_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--file',
        '-f',
        help='File containing album or track urls',
        required=False,
    )
    input_group.add_argument(
        '--search',
        '-s',
        nargs='*',
        help='Search for albums',
        required=False,
    )
    input_group.add_argument(
        'URLS',
        help='Album or track urls',
        nargs='*',
        default=[],
    )
    input_group.add_argument(
        '--album',
        '-a',
        required=False,
    )
    parser.add_argument(
        '--threads',
        '-t',
        type=int,
        default=MAX_CONCURRENT_REQUESTS,
    )

    return parser


def summarize_download(
    downloads: Sequence[Path | None],
) -> None:
    download_count = len(downloads)
    successful_tasks: list[Path] = list(filter(None, downloads))
    success_count = len(successful_tasks)

    downloaded_bytes = sum(
        download.stat().st_size for download in successful_tasks
    )

    logger.info(f'Downloaded {success_count}/{download_count} tracks')
    logger.info(f'Download size: {downloaded_bytes / 1024 / 1024:.2f} MB')


@log_time
def main_cli() -> None:
    logging.basicConfig(
        level=logging.INFO,
        filename='main.log',
        filemode='a',
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    )
    logger.addHandler(logging.StreamHandler())

    args = construct_argparser().parse_args()

    if args.album:
        pprint(get_album(args.album))
        return

    logger.info('Started cli script')
    logger.info(f'File: {args.file}')
    logger.info(f'Urls: {args.URLS}')
    logger.info(f'Search_query: {args.search}')
    logger.info(f'Thread count: {args.threads}')

    if args.search:
        for i, result in enumerate(
            search_albums(' '.join(args.search)),
            start=1,
        ):
            pprint(f'{i}. {result.name}')
        return

    urls = args.URLS or Path(args.file).read_text().splitlines()

    downloads = tuple(download_many(*urls, thread_count=args.threads))
    summarize_download(downloads)


if __name__ == '__main__':
    main_cli()
