# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time    : 2024-01-22
@Author  : Rey
@Contact : reyxbo@163.com
@Explain : Sina Web fetch methods.
"""

from typing import TypedDict, Literal
from reykit.rbase import throw
from reykit.rnet import request
from reykit.rre import search, findall, sub
from reykit.rtime import now

__all__ = (
    'crawl_sina_search_market',
    'crawl_sina_stock_info'
)

SinaStockInfo = TypedDict(
    'SinaStockInfo',
    {
        'code': str,
        'name': str,
        'price': float,
        'open': float,
        'pre_close': float,
        'high': float,
        'low': float,
        'volume': int,
        'amount': int,
        'time': str,
        'url': str,
        'change': float,
        'change_rate': float,
        'swing': float
    }
)

def crawl_sina_search_market(keyword: str) -> list[dict[Literal['code', 'name', 'type', 'url'], str]]:
    """
    Crawl Sina Web and search market product table.

    Parameters
    ----------
    keyword : Search keyword.

    Returns
    -------
    Search result table.
    """

    # Parameter.
    url = 'https://biz.finance.sina.com.cn/suggest/lookup_n.php'
    params = {
        'country': '',
        'q': keyword
    }

    # Request.
    response = request(
        url,
        params,
        check=True
    )

    # Unique result.
    if response.request.url.startswith("https://finance.sina.com.cn"):
        pattern = "var papercode = '(.+?)'"
        stock_code = search(pattern, response.text)
        pattern = "var stockname = '(.+?)'"
        stock_name = search(pattern, response.text)
        row = {
            'code': stock_code,
            'name': stock_name,
            'type': '沪深股市(个股)',
            'url': response.request.url
        }
        table = [row]
        return table

    # Extract.
    pattern = '<div class="(market|list)"(.+?)</div>'
    labels_result: tuple[str, str] = findall(pattern, response.text)
    table = []
    for index, (label_class, div_text) in enumerate(labels_result):
        if label_class != 'list':
            continue
        stock_type_div_text = labels_result[index - 1][1]
        stock_type = stock_type_div_text.rsplit('<div>', 1)[1]
        pattern = '<label><a href="([^"]+)" target="_blank">(.+?)</label>'
        stocks_result = findall(pattern, div_text)
        for stock_url, stock_text in stocks_result:
            pattern = '<.+?>'
            stock_info = sub(pattern, stock_text)
            stock_info_split = stock_info.split(maxsplit=1)
            if len(stock_info_split) != 2:
                continue
            stock_code, stock_name = stock_info_split
            if stock_name.startswith('('):
                stock_name = stock_name[1:-1]
            row = {
                'code': stock_code,
                'name': stock_name,
                'type': stock_type,
                'url': stock_url
            }
            table.append(row)

    return table

def crawl_sina_stock_info(code: str | list[str]) -> list[SinaStockInfo]:
    """
    Crawl Sina Web stock information.

    Parameters
    ----------
    code : Stock code.

    Returns
    -------
    Stock information table.
    """

    # Parameter.
    if type(code) == str:
        code = code.split(',')
    code = [
        (
            i
            if i[-1] in '0123456789'
            else 'gb_' + i.replace('.', '$')
        )
        for i in code
    ]
    code = ','.join(code)
    code = code.lower()
    url = 'https://hq.sinajs.cn/rn=%s&list=%s' % (
        now('timestamp'),
        code
    )
    headers = {'Referer': 'https://finance.sina.com.cn'}

    # Request.
    response = request(
        url,
        headers=headers,
        check=True
    )

    # Extract.
    pattern = '([^_]+?)="([^"]*)"'
    result: list[tuple[str, str]] = findall(pattern, response.text)
    table = []
    for code, info in result:
        info_list = info.split(',')
        info_list_len = len(info_list)
        match info_list_len:

            ## A.
            case 34:
                (
                    stock_name,
                    stock_open,
                    stock_pre_close,
                    stock_price,
                    stock_high,
                    stock_low,
                    _,
                    _,
                    stock_volume,
                    stock_amount,
                    *_,
                    stock_date,
                    stock_time,
                    _,
                    _
                ) = info_list
                row = {
                    'code': code,
                    'name': stock_name,
                    'price': float(stock_price),
                    'open': float(stock_open),
                    'pre_close': float(stock_pre_close),
                    'high': float(stock_high),
                    'low': float(stock_low),
                    'volume': int(float(stock_volume)),
                    'amount': int(float(stock_amount)),
                    'time': '%s %s' % (stock_date, stock_time),
                    'url': 'https://finance.sina.com.cn/realstock/company/%s/nc.shtml' % code
                }

            # US.
            case 36 | 30:
                (
                    stock_name,
                    stock_price,
                    _,
                    stock_date_time,
                    _,
                    stock_open,
                    stock_high,
                    stock_low,
                    _, _,
                    stock_amount,
                    _, _, _, _, _, _, _, _, _, _, _, _, _, _, _,
                    stock_pre_close,
                    *_
                ) = info_list
                row = {
                    'code': code,
                    'name': stock_name,
                    'price': float(stock_price),
                    'open': float(stock_open),
                    'pre_close': float(stock_pre_close),
                    'high': float(stock_high),
                    'low': float(stock_low),
                    'amount': int(float(stock_amount)),
                    'time': stock_date_time,
                    'url': 'https://stock.finance.sina.com.cn/usstock/quotes/%s.html' % code.replace('$', '.')
                }

            ## Throw exception.
            case _:
                throw(AssertionError, info)

        row['change'] = round(row['price'] - row['pre_close'], 4)
        row['change_rate'] = round(row['change'] / row['pre_close'] * 100, 4)
        row['swing'] = round((row['high'] - row['low']) / row['high'] * 100, 4)
        table.append(row)

    return table
