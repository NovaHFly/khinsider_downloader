import argparse
import logging
from concurrent.futures import Future
from pathlib import Path
from pprint import pprint

from ._khinsider import download_tracks, get_album_data
from .constants import DEFAULT_THREAD_COUNT

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
        'URLS',
        help='Album or track urls',
        nargs='*',
        default=[],
    )
    input_group.add_argument('--album', '-a', required=False)
    parser.add_argument(
        '--threads',
        '-t',
        type=int,
        default=DEFAULT_THREAD_COUNT,
    )

    return parser


def summarize_download(
    download_tasks: list[Future[Path]],
) -> None:
    download_count = len(download_tasks)
    successful_tasks = [
        task for task in download_tasks if not task.exception()
    ]
    success_count = len(successful_tasks)

    downloaded_bytes = sum(
        task.result().stat().st_size for task in successful_tasks
    )

    logger.info(f'Downloaded {success_count}/{download_count} tracks')
    logger.info(f'Download size: {downloaded_bytes / 1024 / 1024:.2f} MB')


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
        pprint(get_album_data(args.album))
        return

    logger.info('Started cli script')
    logger.info(f'File: {args.file}')
    logger.info(f'Urls: {args.URLS}')
    logger.info(f'Thread count: {args.threads}')

    summarize_download(
        download_tracks(
            *(
                args.URLS
                if args.URLS
                else Path(args.file).read_text().splitlines()
            ),
            thread_count=args.threads,
        )
    )


if __name__ == '__main__':
    main_cli()
