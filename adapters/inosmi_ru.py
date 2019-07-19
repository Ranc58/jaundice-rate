from bs4 import BeautifulSoup
import requests
import pytest

from .exceptions import ArticleNotFound
from .html_tools import remove_buzz_attrs, remove_buzz_tags, remove_all_tags


def sanitize(html, plaintext=False):
    soup = BeautifulSoup(html, 'html.parser')
    articles = soup.select("article.article")
    titles = soup.select("title")
    if len(articles) != 1:
        raise ArticleNotFound()

    article = articles[0]
    article.attrs = {}

    buzz_blocks = [
        *article.select('.article-disclaimer'),
        *article.select('footer.article-footer'),
        *article.select('aside'),
    ]
    for el in buzz_blocks:
        el.decompose()

    remove_buzz_attrs(article)
    remove_buzz_tags(article)

    if not plaintext:
        text = article.prettify()
        title = titles[0].prettify()
    else:
        remove_all_tags(article)
        text = article.get_text()
        title = titles[0].get_text()
    return text.strip(), title.strip()
