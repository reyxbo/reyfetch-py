# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time    : 2025-08-25
@Author  : Rey
@Contact : reyxbo@163.com
@Explain : Douban Web fetch methods.
"""

from typing import TypedDict
from bs4 import BeautifulSoup
from reydb import rorm, DatabaseEngine
from reykit.rbase import throw
from reykit.rnet import request
from reykit.rre import search, findall, sub
from reykit.rtime import now

from ..rbase import FetchCrawl

__all__ = (
    'DatabaseORMTableDoubanMedia',
    'FetchCrawlDouban'
)

MediaRow = TypedDict(
    'MediaRow', 
    {
        'id': int,
        'type': str,
        'name': str,
        'score': float,
        'score_count': int,
        'image': str,
        'image_low': str,
        'episode': int | None,
        'episode_now': int | None,
        'year': int,
        'country': list[str],
        'class': list[str],
        'director': list[str] | None,
        'star': list[str] | None
    }
)
type MediaTable = list[MediaRow]
MediaInfo = TypedDict(
    'MediaInfo',
    {
        'type': str,
        'name': str,
        'year': int | None,
        'score': float,
        'score_count': int,
        'director': list[str] | None,
        'scriptwriter': list[str] | None,
        'star': list[str] | None,
        'class': list[str] | None,
        'country': list[str] | None,
        'language': list[str] | None,
        'premiere': dict[str, str] | None,
        'episode': int | None,
        'minute': int | None,
        'alias': list[str] | None,
        'imdb': str | None,
        'comment': list[str],
        'image': str,
        'image_low': str
    }
)

class DatabaseORMTableDoubanMedia(rorm.Table):
    """
    Database "douban_media" table ORM model.
    """

    __name__ = 'douban_media'
    __comment__ = 'Douban media information table.'
    create_time: rorm.Datetime = rorm.Field(field_default=':time', not_null=True, index_n=True, comment='Record create time.')
    update_time: rorm.Datetime = rorm.Field(field_default=':time', arg_default=now, index_n=True, comment='Record update time.')
    id: int = rorm.Field(key=True, comment='Douban media ID.')
    imdb: str = rorm.Field(rorm.types.CHAR(10), index_u=True, comment='IMDb ID.')
    type: str = rorm.Field(rorm.types.VARCHAR(5), not_null=True, comment='Media type.')
    name: str = rorm.Field(rorm.types.VARCHAR(200), not_null=True, index_n=True, comment='Media name.')
    year: str = rorm.Field(rorm.types.SMALLINT, not_null=True, comment='Media content description.')
    desc: str = rorm.Field(rorm.types.VARCHAR(1000), comment='Media content description.')
    score: float = rorm.Field(comment='Media score, [0,10].')
    score_count: int = rorm.Field(comment='Media score count.')
    minute: int = rorm.Field(rorm.types.SMALLINT, comment='Movie or TV drama episode minute.')
    episode: int = rorm.Field(rorm.types.SMALLINT, comment='TV drama total episode number.')
    episode_now: int = rorm.Field(rorm.types.SMALLINT, comment='TV drama current episode number.')
    premiere: str = rorm.Field(rorm.JSONB, comment='Premiere region and date dictionary.')
    country: str = rorm.Field(rorm.JSONB, comment='Release country list.')
    class_: str = rorm.Field(rorm.JSONB, comment='Class list.', name='class')
    director: str = rorm.Field(rorm.JSONB, comment='Director list.')
    star: str = rorm.Field(rorm.JSONB, comment='Star list.')
    scriptwriter: str = rorm.Field(rorm.JSONB, comment='Scriptwriter list.')
    language: str = rorm.Field(rorm.JSONB, comment='Language list.')
    alias: str = rorm.Field(rorm.JSONB, comment='Alias list.')
    comment: str = rorm.Field(rorm.JSONB, comment='Comment list.')
    image: str = rorm.Field(rorm.types.VARCHAR(150), not_null=True, comment='Picture image URL.')
    image_low: str = rorm.Field(rorm.types.VARCHAR(150), not_null=True, comment='Picture image low resolution URL.')
    video: str = rorm.Field(rorm.types.VARCHAR(150), comment='Preview video Douban page URL.')

class FetchCrawlDouban(FetchCrawl):
    """
    Crawl Douban Web fetch type.
    Can create database used "self.build_db" method.
    """

    def __init__(self, db_engine: DatabaseEngine | None = None) -> None:
        """
        Build instance attributes.

        Parameters
        ----------
        db_engine : Database engine.
            - "None": Not use database.
            - "Database": Automatic record to database.
        """

        # Build.
        self.db_engine = db_engine

        # Build Database.
        if self.db_engine is not None:
            self.build_db()

    def build_db(self) -> None:
        """
        Check and build database tables.
        """

        # Check.
        if self.db_engine is None:
            throw(ValueError, self.db_engine)

        # Parameter.

        ## Table.
        tables = [DatabaseORMTableDoubanMedia]

        ## View stats.
        views_stats = [
            {
                'table': 'stats_douban',
                'items': [
                    {
                        'name': 'count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "douban_media"'
                        ),
                        'comment': 'Media count.'
                    },
                    {
                        'name': 'past_day_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "douban_media"\n'
                            'WHERE DATE_PART(\'day\', NOW() - "create_time") = 0'
                        ),
                        'comment': 'Media count in the past day.'
                    },
                    {
                        'name': 'past_week_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "douban_media"\n'
                            'WHERE DATE_PART(\'day\', NOW() - "create_time") <= 6'
                        ),
                        'comment': 'Media count in the past week.'
                    },
                    {
                        'name': 'past_month_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "douban_media"\n'
                            'WHERE DATE_PART(\'day\', NOW() - "create_time") <= 29'
                        ),
                        'comment': 'Media count in the past month.'
                    },
                    {
                        'name': 'avg_score',
                        'select': (
                            'SELECT ROUND(AVG("score")::NUMERIC, 1)\n'
                            'FROM "douban_media"'
                        ),
                        'comment': 'Media average score.'
                    },
                    {
                        'name': 'total_score',
                        'select': (
                            'SELECT TO_CHAR(SUM("score_count"), \'FM999,999,999,999,999\')\n'
                            'FROM "douban_media"'
                        ),
                        'comment': 'Media total score.'
                    },
                    {
                        'name': 'last_create_time',
                        'select': (
                            'SELECT MAX("create_time")\n'
                            'FROM "douban_media"'
                        ),
                        'comment': 'Media last record create time.'
                    },
                    {
                        'name': 'last_update_time',
                        'select': (
                            'SELECT COALESCE(MAX("update_time"), MAX("create_time"))\n'
                            'FROM "douban_media"'
                        ),
                        'comment': 'Media last record update time.'
                    }
                ]
            }
        ]

        # Build.
        self.db_engine.build.build(tables=tables, views_stats=views_stats, skip=True)

    def crawl_table(self) -> MediaTable:
        """
        Crawl media table.

        Returns
        -------
        Media table.
        """

        # Parameter.
        url_format = 'https://m.douban.com/rexxar/api/v2/subject/recent_hot/%s'
        referer_format = 'https://movie.douban.com/%s/'
        types_params = (
            ('movie', 'explore', '热门', '华语'),
            ('movie', 'explore', '热门', '欧美'),
            ('movie', 'explore', '热门', '日本'),
            ('movie', 'explore', '热门', '韩国'),
            ('tv', 'tv', 'tv', 'tv_domestic'),
            ('tv', 'tv', 'tv', 'tv_american'),
            ('tv', 'tv', 'tv', 'tv_japanese'),
            ('tv', 'tv', 'tv', 'tv_korean'),
            ('tv', 'tv', 'tv', 'tv_animation'),
            ('tv', 'tv', 'tv', 'tv_documentary'),
            ('tv', 'tv', 'show', 'show_domestic'),
            ('tv', 'tv', 'show', 'show_foreign')
        )

        # Get.
        table_dict: dict[int, MediaRow] = {}
        for type_params in types_params:
            type_ = type_params[0]
            url = url_format % type_
            referer = referer_format % type_params[1]
            params = {
                'start': 0,
                'limit': 1000,
                'category': type_params[2],
                'type': type_params[3],
                'ck': 'Id-j'
            }
            headers = {
                'referer': referer,
                'user-agent': self.ua.edge
            }

            ## Request.
            response = request(
                url,
                params,
                headers=headers,
                check=True
            )

            ## Extract.
            response_json = response.json()
            items: list[dict] = response_json['items']
            for item in items:
                id_ = int(item['id'])

                ### Exist.
                if id_ in table_dict:
                    continue

                ### Base.
                row = {
                    'id': id_,
                    'type': type_,
                    'name': item['title'],
                    'score': float(item['rating']['value']),
                    'score_count': int(item['rating']['count']),
                    'image': item['pic']['large'],
                    'image_low': item['pic']['normal']
                }

                ### Score.
                row['score'] = float(item['rating']['value']) or None
                row['score_count'] = int(item['rating']['count']) or None

                ### Episode.
                if item['episodes_info'] == '':
                    row['episode_now'] = row['episode'] = None
                else:
                    row['episode_now'] = search(r'\d+', item['episodes_info'])
                    if '全' in item['episodes_info']:
                        row['episode'] = row['episode_now']
                    else:
                        row['episode'] = None

                ### Information.
                desc = item['card_subtitle'].split(' / ', 4)
                if len(desc) == 5:
                    year, countries, classes, directors, stars = desc
                elif len(desc) == 4:
                    year, countries, classes, stars = desc
                    directors = None
                else:
                    year, countries, classes = desc
                    directors = None
                    stars = None
                row['year'] = int(year)
                row['country'] = countries.split()
                row['class'] = classes.split()
                row['director'] = directors and directors.split()
                row['star'] = stars and stars.split()

                ### Empty.
                row = {
                    key: value
                    for key, value in row.items()
                    if value
                }

                ### Add.
                table_dict[id_] = row

        ## Convert.
        table = list(table_dict.values())

        # Database.
        if self.db_engine is not None:
            update_fields = (
                'update_time',
                'id',
                'type',
                'name',
                'score',
                'score_count',
                'image',
                'image_low',
                'episode',
                'episode_now',
                'year'
            )
            self.db_engine.execute.insert(
                'douban_media',
                table,
                'id',
                update_fields,
                update_time=':NOW()'
            )

        return table

    def crawl_info(self, id_: int) -> MediaInfo:
        """
        Crawl media information.

        Parameters
        ----------
        id\\_ : Douban media ID.

        Returns
        -------
        Media information.
        """

        # Parameter.
        url = f'https://movie.douban.com/subject/{id_}/'
        headers = {'user-agent': self.ua.edge}

        # Request.
        response = request(
            url,
            headers=headers,
            check=200
        )

        # Extract.
        html = response.text
        bs = BeautifulSoup(html, 'lxml')
        attrs = {'id': 'info'}
        element = bs.find(attrs=attrs)
        pattern = r'([^\n]+?): ([^\n]+)\n'
        result = findall(pattern, element.text)
        info_dict: dict[str, str] = dict(result)
        split_chars = ' / '
        infos = {}

        ## Type.
        if (
            'class="episode_list"' in html
            or '该剧目前还未确定具体集数，如果你知道，欢迎' in bs.find(attrs='article').text
        ):
            infos['type'] = 'tv'
        else:
            infos['type'] = 'movie'

        ## Name.
        pattern = r'<title>\s*(.+?)\s*\(豆瓣\)\s*</title>'
        infos['name'] = search(pattern, html)

        ## Year.
        pattern = r'<span class="year">\((\d{4})\)</span>'
        year: str | None = search(pattern, html)
        infos['year'] = year and int(year)

        ## Description.
        selector = '#link-report-intra span[property="v:summary"]'
        elements = bs.select(selector, limit=1)
        if len(elements) == 0:
            infos['desc'] = None
        else:
            element, = bs.select(selector, limit=1)
            text = element.text.strip()
            pattern = r'\s{2,}'
            infos['desc'] = sub(pattern, text, '')

        ## Score.
        element = bs.find(attrs='ll rating_num')
        if element.text == '':
            infos['score'] = None
        else:
            infos['score'] = float(element.text)

        ## Score count.
        if infos['score'] is not None:
            attrs = {'property': 'v:votes'}
            element = bs.find(attrs=attrs)
            infos['score_count'] = int(element.text)
        else:
            infos['score_count'] = None

        ## Directors.
        directors = info_dict.get('导演')
        infos['director'] = directors and directors.split(split_chars)

        ## Scriptwriters.
        scriptwriters = info_dict.get('编剧')
        infos['scriptwriter'] = scriptwriters and scriptwriters.split(split_chars)

        ## Stars.
        stars = info_dict.get('主演')
        infos['star'] = stars and stars.split(split_chars)

        ## Classes.
        classes = info_dict.get('类型')
        infos['class'] = classes and classes.split(split_chars)

        ## Countries.
        countries = info_dict.get('制片国家/地区')
        infos['country'] = countries and countries.split(split_chars)

        ## Languages.
        languages = info_dict.get('语言')
        infos['language'] = languages and languages.split(split_chars)

        ## Premieres.
        premieres = info_dict.get('上映日期')
        premieres = premieres or info_dict.get('首播')
        infos['premiere'] = premieres and {
            countrie: date
            for premiere in premieres.split(split_chars)
            for date, countrie in (search(r'([^\(]+)\((.+)\)', premiere),)
        }

        ## Episode.
        episode = info_dict.get('集数')
        infos['episode'] = episode and int(episode)

        ## Minute.
        minute = info_dict.get('片长')
        minute = minute or info_dict.get('单集片长')
        infos['minute'] = minute and int(search(r'\d+', minute))

        ## Alias.
        alias = info_dict.get('又名')
        infos['alias'] = alias and alias.split(split_chars)

        ## IMDb.
        infos['imdb'] = info_dict.get('IMDb')

        ## Comments.
        selector = '#hot-comments .comment-content'
        elements = bs.select(selector)
        comments = [
            sub(
                r'\s{2,}',
                (
                    element.find(attrs='full')
                    or element.find(attrs='short')
                ).text.strip(),
                ''
            )
            for element in elements
        ]
        infos['comment'] = comments

        ## Image.
        selector = '.nbgnbg>img'
        element, = bs.select(selector=selector, limit=1)
        image_url = element.attrs['src']
        infos['image_low'] = image_url.replace('.webp', '.jpg', 1)
        infos['image'] = infos['image_low'].replace('/s_ratio_poster/', '/m_ratio_poster/', 1)

        ## Video.
        element = bs.find(attrs='related-pic-video')
        if element is None:
            infos['video'] = None
        else:
            url = element.attrs['href']
            infos['video'] = url.replace('#content', '', 1)

        ## Empty.
        infos = {
            key: value
            for key, value in infos.items()
            if value
        }

        # Database.
        if self.db_engine is not None:
            data = {'id': id_}
            data.update(infos)
            self.db_engine.execute.insert(
                'douban_media',
                data,
                'id',
                'update',
                update_time=':NOW()'
            )

        return infos

    def crawl_video_url(self, url: str) -> str:
        """
        Crawl video download URL from video page URL.

        Parameters
        ----------
        url : Video page URL.

        Returns
        -------
        Video download URL.
        """

        # Request.
        headers = {'user-agent': self.ua.edge}
        response = request(url, headers=headers, check=True)

        # Extract.
        pattern = r'<source src="([^"]+)"'
        result: str | None = search(pattern, response.text)

        # Check.
        if result is None:
            throw(AssertionError, result, url)

        return result
