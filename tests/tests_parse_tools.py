import asyncio

import asynctest
import pymorphy2
import pytest
from aiohttp import InvalidURL, ClientError

from adapters import ArticleNotFound
from parse_tools import check_for_available_parse, get_charged_words, SOURCE_LIST, process_article, ProcessingStatus


async def timeout_mock(*args, **kwargs):
    secs = kwargs.get('secs', 6)
    await asyncio.sleep(secs)


async def mock_fetch_errors(*args, **kwargs):
    url = args[0]
    if 'timeout_error' in url:
        await timeout_mock()
    elif 'invalid_url' in url:
        raise InvalidURL(url)
    elif 'client_error' in url:
        raise ClientError


@pytest.mark.asyncio
async def test_check_for_available_parse():
    with pytest.raises(ArticleNotFound) as excinfo:
        await check_for_available_parse('http://nonexistentUrl.com/test')
        assert str(excinfo) == 'Статья на nonexistentUrl.com'


@pytest.mark.asyncio
async def test_sucess_process_article():
    charged_words = get_charged_words()
    morph = pymorphy2.MorphAnalyzer()
    fetch_mock = asynctest.CoroutineMock()
    session_mock = asynctest.CoroutineMock()
    fetch_mock.return_value = '<title>test title</title> <article class="article">test article</article>'
    url = f'https://{SOURCE_LIST[0]}/test_articlle'
    with asynctest.patch(
        'parse_tools.fetch', side_effect=fetch_mock):
        result = await process_article(session_mock, morph, charged_words, url)
        assert result['title'] == 'test title'
        assert result['status'] == ProcessingStatus.OK.value
        assert result['words_count'] == 2


@pytest.mark.asyncio
async def test_non_exist_article_source():
    charged_words = get_charged_words()
    morph = pymorphy2.MorphAnalyzer()
    session_mock = asynctest.CoroutineMock()
    url = f'https://nonexistentUrl.com/test_articlle'
    expected_result = {
        'title': 'Статья на nonexistentUrl.com',
        'status': ProcessingStatus.PARSING_ERROR.value,
        'score': None,
        'words_count': None
    }
    result = await process_article(session_mock, morph, charged_words, url)
    assert result == expected_result


@pytest.mark.asyncio
async def test_fetch_timeout():
    charged_words = get_charged_words()
    morph = pymorphy2.MorphAnalyzer()
    session_mock = asynctest.CoroutineMock()
    url = f'https://{SOURCE_LIST[0]}/timeout_error'
    expected_result = {
        'title': 'TimeOut error',
        'status': ProcessingStatus.TIMEOUT.value,
        'score': None,
        'words_count': None
    }

    with asynctest.patch(
        'parse_tools.fetch', side_effect=mock_fetch_errors):
        result = await process_article(session_mock, morph, charged_words, url)
        assert result == expected_result


@pytest.mark.asyncio
async def test_invalid_url_error():
    charged_words = get_charged_words()
    morph = pymorphy2.MorphAnalyzer()
    session_mock = asynctest.CoroutineMock()
    url = f'https://{SOURCE_LIST[0]}/invalid_url'
    expected_result = {
        'title': f'URL {url} Does not exist',
        'status': ProcessingStatus.FETCH_ERROR.value,
        'score': None,
        'words_count': None
    }
    with asynctest.patch('parse_tools.fetch', side_effect=mock_fetch_errors):
        result = await process_article(session_mock, morph, charged_words, url)
        assert result == expected_result


@pytest.mark.asyncio
async def test_client_error():
    charged_words = get_charged_words()
    morph = pymorphy2.MorphAnalyzer()
    session_mock = asynctest.CoroutineMock()
    url = f'https://{SOURCE_LIST[0]}/client_error'
    expected_result = {
        'title': 'Connection error',
        'status': ProcessingStatus.FETCH_ERROR.value,
        'score': None,
        'words_count': None
    }
    with asynctest.patch('parse_tools.fetch', side_effect=mock_fetch_errors):
        result = await process_article(session_mock, morph, charged_words, url)
        assert result == expected_result


@pytest.mark.asyncio
async def test_timeout_split_text():
    charged_words = get_charged_words()
    morph = pymorphy2.MorphAnalyzer()
    url = f'https://{SOURCE_LIST[0]}/client_error'
    session_mock = asynctest.CoroutineMock()
    fetch_mock = asynctest.CoroutineMock()
    fetch_mock.return_value = '<title>test title</title> <article class="article">test article</article>'
    expected_result = {
        'title': 'test title',
        'status': ProcessingStatus.TIMEOUT.value,
        'score': None,
        'words_count': None
    }
    with asynctest.patch('parse_tools.fetch', side_effect=fetch_mock):
        with asynctest.patch('parse_tools.split_by_words', side_effect=timeout_mock):
            result = await process_article(session_mock, morph, charged_words, url)
            assert result == expected_result
