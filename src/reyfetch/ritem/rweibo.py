# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time    : 2024-01-22
@Author  : Rey
@Contact : reyxbo@163.com
@Explain : Weibo Web fetch methods.
"""

from typing import Any, Literal
from fake_useragent import UserAgent
from reykit.rnet import request, join_url
from reykit.rtime import now

__all__ = (
    'crawl_weibo_hot_search',
)

def crawl_weibo_hot_search() -> list[dict[Literal['rank', 'time', 'title', 'type', 'hot', 'url'], Any]]:
    """
    Crawl Weibo Web hot search table.

    Returns
    -------
    Hot search table.
        - `Key 'rank'`: Hot search rank.
        - `Key 'time'`: Hot search time.
        - `Key 'title'`: Hot search title.
        - `Key 'type'`: Hot search type.
        - `Key 'hot'`: Hot search hot value.
        - `Key 'url'`: Hot search URL.
    """

    # Request.
    url = 'https://weibo.com/ajax/side/searchBand'
    timestamp_second = now('timestamp_s')
    params = {
        'type': 'hot',
        'last_tab': 'hot',
        'last_table_time': timestamp_second
    }
    ua = UserAgent()
    headers = {
        'cookie': (
            'SUB=_2AkMf61vxf8NxqwFRmvgTzm_la4RxzAvEieKpt6oqJRMxHRl-yT9yqmIEtRB6NGt1HrGel2jwtm1TPoj0LB2qbH5Djjty; '
            'SUBP=0033WrSXqPxfM72-Ws9jqgMF55529P9D9W5LjsD9P67XdiTS.eBzcX8n; '
            'XSRF-TOKEN=JUL_aQ7hlSuI98dYZDxZdYNV; '
            'WBPSESS=9-DrhgMbGnVf8No6y5BLAa-AdtUBbe2eTM9RR6Vd3EQO6R5LLxnh_NKkxuJ_a9m2rFeEEGrQEIgK1oe4gs2SnXWX_ZT5_XC9csUnNHL-q-ZJLzj9wbKvtMB4ZYVnfrM8'
        ),
        'referer': 'https://weibo.com/newlogin?tabtype=weibo&gid=102803&openLoginLayer=0&url=https%3A%2F%2Fwww.weibo.com%2F',
        'user-agent': ua.edge,
    }
    response = request(url, params, headers=headers, check=True)

    # Extract.
    response_json = response.json()
    table: list[dict] = response_json['data']['realtime']

    # Convert.
    table = [
        {
            'title': info['word'],
            'hot': info['num'],
            'url': join_url(
                'https://s.weibo.com/weibo',
                q=f'#{info['word']}#'
            )
        }
        for info in table
        if 'flag' in info
    ]
    sort_key = lambda row: (
        0
        if row['hot'] is None
        else row['hot']
    )
    table.sort(key=sort_key, reverse=True)
    table = [
        {
            'rank': index,
            **row
        }
        for index, row in enumerate(table)
    ]

    return table
