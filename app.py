import asyncio
import contextlib
import functools
import logging
import time
import json


import aiohttp
import pymorphy2
from aiohttp import web
from aiohttp.web_response import json_response

from main import get_charged_words, create_handy_nursery, process_article


async def articles_handler(request, morph, charged_words):
    urls = request.query.get('urls')
    if not urls:
        return json_response(data={'error': 'no one urls'}, status=400)
    urls_list = urls.split(',')
    if len(urls_list) > 10:
        return json_response(data={'error': 'max urls count = 10'}, status=400)
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
        done, pending = await asyncio.wait(results_list)
    result_data = json.dumps([task.result() for task in done], ensure_ascii=False)
    logging.info(f'Общее время анализа всех статей {time.monotonic() - start_time}')
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
