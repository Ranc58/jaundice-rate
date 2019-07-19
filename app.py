import asyncio
import contextlib
import functools
import logging
import os
import time
import json

import aionursery
import pymorphy2
import aiohttp
from aiohttp import web
from aiocache import cached
from aiocache.serializers import JsonSerializer
from aiohttp.web_response import json_response
from aiocache.backends.redis import RedisCache

from parse_tools import process_article


@contextlib.asynccontextmanager
async def create_handy_nursery():
    try:
        async with aionursery.Nursery() as nursery:
            yield nursery
    except aionursery.MultiError as e:
        if len(e.exceptions) == 1:
            raise e.exceptions[0]
        raise


def get_charged_words():
    line_list = []
    with open('charged_dicts/positive_words.txt') as f:
        for line in f:
            line_list.append(line.rstrip('\n'))
    with open('charged_dicts/positive_words.txt') as f:
        for line in f:
            line_list.append(line.rstrip('\n'))
    return line_list


@cached(
    ttl=10, cache=RedisCache, serializer=JsonSerializer(),
    endpoint=os.environ.get('REDIS_HOST', 'localhost'),
    port=os.environ.get('REDIS_PORT', 6379),
    password=os.environ.get('REDIS_PASSWORD', 'SetPass')
)
async def process_parse(urls_list, morph, charged_words):
    results_list = []
    start_time = time.monotonic()
    async with contextlib.AsyncExitStack() as stack:
        nursery = await stack.enter_async_context(create_handy_nursery())
        session = await stack.enter_async_context(aiohttp.ClientSession())
        for article_url in urls_list:
            result_data = nursery.start_soon(
                process_article(session, morph, charged_words, article_url)
            )
            results_list.append(result_data)
        done, _ = await asyncio.wait(results_list)
        logging.info(f'Общее время анализа всех статей {time.monotonic() - start_time}')
        return [task.result() for task in done]


async def articles_handler(request, morph, charged_words):
    urls = request.query.get('urls')
    if not urls:
        return json_response(data={'error': 'no one urls'}, status=400)
    urls_list = urls.split(',')
    if len(urls_list) > 10:
        return json_response(data={'error': 'max urls count = 10'}, status=400)
    parse_result = await process_parse(urls_list, morph, charged_words)
    # json.dumps because  json_response body don't support ensure ascii
    result_data = json.dumps(parse_result, ensure_ascii=False)
    return json_response(text=result_data, status=200)


def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    morph = pymorphy2.MorphAnalyzer()
    charged_words = get_charged_words()
    app.add_routes([
        web.get(
            path='/',
            handler=functools.partial(
                articles_handler,
                morph=morph,
                charged_words=charged_words
            )
        )
    ])

    web.run_app(app)


if __name__ == '__main__':
    main()
