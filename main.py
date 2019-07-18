import contextlib
import logging
import time
from enum import Enum

import aiohttp
import asyncio
from concurrent.futures import FIRST_COMPLETED

import aionursery
from aiohttp import InvalidURL, ClientConnectorError, ClientError
from async_timeout import timeout

from adapters import ArticleNotFound
from adapters.inosmi_ru import sanitize
from text_tools import split_by_words, calculate_jaundice_rate


TEST_ARTICLES = [
    'https://inosmi.ru/economic/20190629/245384784.html',
    'https://inosmi.ru/politic/20190710/245447320.html',# todo change!
    'https://inosmi.ru/politic/20190710/245447244.html',
    'http://tra',
    'https://inosmi.ru/politic/20190710/245446326.html',
    'https://inosmi.ru/politic/20190710/245444854.html',
    'ffsdfsgf'
]


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


@contextlib.asynccontextmanager
async def create_handy_nursery():
    try:
        async with aionursery.Nursery() as nursery:
            yield nursery
    except aionursery.MultiError as e:
        if len(e.exceptions) == 1:
            raise e.exceptions[0]
        raise


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


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


async def check_for_available_parse(url):
    if url == 'http://tra':  # todo del!
        raise ArticleNotFound
    return True


async def process_article(session, morph, charged_words, url):
    try:
        await check_for_available_parse(url)
    except ArticleNotFound: #todo change title
        return {'title': 'URL Does not exist',  'status': ProcessingStatus.PARSING_ERROR.value, 'score': None, 'words_count': None}
    try:
        # async with timeout(5): # todo back
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

