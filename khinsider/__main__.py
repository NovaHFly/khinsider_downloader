import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from khinsider.cache import CacheManager
from khinsider.constants import MAX_CONCURRENT_REQUESTS
from khinsider.decorators import log_time
from khinsider.files import download_many

logger = logging.getLogger('khinsider')


def _construct_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--file',
        '-f',
        help='File containing album or track urls',
        required=False,
    )
    input_group.add_argument(
        'URLS',
        help='Album or track urls',
        nargs='*',
        default=[],
    )
    parser.add_argument(
        '--threads',
        '-t',
        type=int,
        default=MAX_CONCURRENT_REQUESTS,
    )

    return parser


def _summarize_download(
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
def _main_cli() -> None:
    logging.basicConfig(
        level=logging.INFO,
        handlers=(logging.FileHandler('main.log'), logging.StreamHandler()),
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
        force=True,
    )
    CacheManager.get_manager(use_garbage_collector=False)

    args = _construct_argparser().parse_args()

    logger.info('Started cli script')
    logger.info(f'File: {args.file}')
    logger.info(f'Urls: {args.URLS}')
    logger.info(f'Thread count: {args.threads}')

    urls = args.URLS or Path(args.file).read_text().splitlines()

    downloads = tuple(download_many(*urls, thread_count=args.threads))
    _summarize_download(downloads)


if __name__ == '__main__':
    _main_cli()
