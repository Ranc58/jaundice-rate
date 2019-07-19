import asyncio
import contextlib
import logging
import time
from enum import Enum
from urllib.parse import urlparse

from async_timeout import timeout
from aiohttp import InvalidURL, ClientConnectorError, ClientError

from adapters import ArticleNotFound
from adapters.inosmi_ru import sanitize
from text_tools import split_by_words, calculate_jaundice_rate

SOURCE_LIST = [
    'inosmi.ru'
]


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


@contextlib.asynccontextmanager
async def process_split_by_words(morph, sanitazed_text):
    start_time = time.monotonic()
    splited_text = None
    error = None
    try:
        async with timeout(5):
            splited_text = await split_by_words(morph, sanitazed_text)
    except asyncio.TimeoutError:
        error = True
    finally:
        end_dime = time.monotonic() - start_time
        yield splited_text, end_dime, error


def get_charged_words():
    line_list = []
    with open('charged_dicts/positive_words.txt') as f:
        for line in f:
            line_list.append(line.rstrip('\n'))
    return line_list


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def check_for_available_parse(url):
    netloc = urlparse(url).netloc
    if netloc not in SOURCE_LIST:
        raise ArticleNotFound(f'Статья на {netloc}')


async def process_article(session, morph, charged_words, url):
    try:
        await check_for_available_parse(url)
    except ArticleNotFound as exc:
        return {'title': f'{exc}',  'status': ProcessingStatus.PARSING_ERROR.value, 'score': None, 'words_count': None}
    try:
        async with timeout(5):
            html = await fetch(session, url)
    except (
        InvalidURL,
        ClientConnectorError,
        ClientError
    ):
        return {'title': 'URL Does not exist', 'status': ProcessingStatus.FETCH_ERROR.value,  'score': None, 'words_count': None}
    except asyncio.TimeoutError:
        return {'title': 'TimeOut error', 'status': ProcessingStatus.TIMEOUT.value, 'score': None, 'words_count': None}
    sanitazed_text, title = sanitize(html, plaintext=True)
    async with process_split_by_words(morph, sanitazed_text) as (splited_text, execution_time, error):
        if error:
            return {'title': title, 'status': ProcessingStatus.TIMEOUT.value, 'score': None, 'words_count': None}
        score = calculate_jaundice_rate(splited_text, charged_words)
        logging.info(f'Анализ статьи произведен за {execution_time:.2f} сек.')
    return {'title': title, 'status': ProcessingStatus.OK.value, 'score': score, 'words_count': len(splited_text)}
