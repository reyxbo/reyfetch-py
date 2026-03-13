# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time    : 2024-01-11
@Author  : Rey
@Contact : reyxbo@163.com
@Explain : Baidu website translate methods.
"""

from typing import TypedDict
from enum import StrEnum
from reydb import rorm, DatabaseEngine
from reykit.rbase import throw
from reykit.rnet import request as reykit_request
from reykit.ros import get_md5
from reykit.rrand import randn
from reykit.rtext import is_zh
from reykit.rtime import now

from ..rbase import ClientDatabaseRecord
from .rbase import ClientBaidu

__all__ = (
    'DatabaseORMTableBaiduTrans',
    'ClientBaidu',
    'ClientBaiduTranslateLangEnum',
    'ClientBaiduTranslateLangAutoEnum',
    'ClientBaiduTranslate',
)

FanyiResponseResult = TypedDict('FanyiResponseResult', {'src': str, 'dst': str})
FanyiResponse = TypedDict('FanyiResponse', {'from': str, 'to': str, 'trans_result': list[FanyiResponseResult]})

class DatabaseORMTableBaiduTrans(rorm.Table):
    """
    Database "baidu_trans" table ORM model.
    """

    __name__ = 'baidu_trans'
    __comment__ = 'Baidu API translate request record table.'
    id: int = rorm.Field(key_auto=True, comment='ID.')
    request_time: rorm.Datetime = rorm.Field(not_null=True, comment='Request time.')
    response_time: rorm.Datetime = rorm.Field(not_null=True, comment='Response time.')
    input: str = rorm.Field(rorm.types.VARCHAR(6000), not_null=True, comment='Input original text.')
    output: str = rorm.Field(rorm.types.TEXT, not_null=True, comment='Output translation text.')
    input_lang: str = rorm.Field(rorm.types.VARCHAR(4), not_null=True, comment='Input original text language.')
    output_lang: str = rorm.Field(rorm.types.VARCHAR(3), not_null=True, comment='Output translation text language.')

class ClientBaiduTranslateLangEnum(ClientBaidu, StrEnum):
    """
    Request Baidu translate APT language enumeration fetch type.
    """

    ZH = 'zh'
    EN = 'en'
    YUE = 'yue'
    KOR = 'kor'
    TH = 'th'
    PT = 'pt'
    EL = 'el'
    BUL = 'bul'
    FIN = 'fin'
    SLO = 'slo'
    CHT = 'cht'
    WYW = 'wyw'
    FRA = 'fra'
    ARA = 'ara'
    DE = 'de'
    NL = 'nl'
    EST = 'est'
    CS = 'cs'
    SWE = 'swe'
    VIE = 'vie'
    JP = 'jp'
    SPA = 'spa'
    RU = 'ru'
    IT = 'it'
    PL = 'pl'
    DAN = 'dan'
    ROM = 'rom'
    HU ='hu'

class ClientBaiduTranslateLangAutoEnum(ClientBaidu, StrEnum):
    """
    Request Baidu translate APT language auto enumeration fetch type.
    """

    AUTO = 'auto'

class ClientBaiduTranslate(ClientBaidu):
    """
    Request Baidu translate API fetch type.
    Can create database used "self.build_db" method.
    """

    url_api = 'http://api.fanyi.baidu.com/api/trans/vip/translate'
    'API request URL.'
    url_doc = 'https://fanyi-api.baidu.com/product/113'
    'API document URL.'
    LangEnum = ClientBaiduTranslateLangEnum
    LangAutoEnum = ClientBaiduTranslateLangAutoEnum

    def __init__(
        self,
        appid: str,
        appkey: str,
        db_engine: DatabaseEngine | None = None,
        max_len: int = 6000
    ) -> None:
        """
        Build instance attributes.

        Parameters
        ----------
        appid : APP ID.
        appkey : APP key.
        db : "Database" instance, insert request record to table.
        max_len : Maximun length.
        """

        # Build.
        self.appid = appid
        self.appkey = appkey
        self.db_engine = db_engine
        self.max_len = max_len

        # Database.
        self.db_record = ClientDatabaseRecord(self, 'baidu_trans')

        ## Build Database.
        if self.db_engine is not None:
            self.build_db()

    def sign(self, text: str, num: int) -> str:
        """
        Get signature.

        Parameters
        ----------
        text : Text.
        num : Number.

        Returns
        -------
        Signature.
        """

        # Check.
        if text == '':
            throw(ValueError, text)

        # Parameter.
        num_str = str(num)

        # Sign.
        data = ''.join(
            (
                self.appid,
                text,
                num_str,
                self.appkey
            )
        )
        md5 = get_md5(data)

        return md5

    def request(
        self,
        text: str,
        from_lang: ClientBaiduTranslateLangEnum | ClientBaiduTranslateLangAutoEnum,
        to_lang: ClientBaiduTranslateLangEnum
    ) -> FanyiResponse:
        """
        Request translate API.

        Parameters
        ----------
        text : Text.
        from_lang : Source language.
        to_lang : Target language.

        Returns
        -------
        Response dictionary.
        """

        # Parameter.
        rand_num = randn(32768, 65536)
        sign = self.sign(text, rand_num)
        params = {
            'q': text,
            'from': from_lang.value,
            'to': to_lang.value,
            'appid': self.appid,
            'salt': rand_num,
            'sign': sign
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        # Request.
        response = reykit_request(
            self.url_api,
            params,
            headers=headers,
            check=True
        )

        # Check.
        content_type = response.headers['Content-Type']
        if content_type.startswith('application/json'):
            response_json: dict = response.json()
            if 'error_code' in response_json:
                throw(AssertionError, response_json)
        else:
            throw(AssertionError, content_type)

        return response_json

    def get_lang(self, text: str) -> ClientBaiduTranslateLangEnum | None:
        """
        Judge and get text language type.

        Parameters
        ----------
        text : Text.

        Returns
        -------
        Language type or null.
        """

        # Hangle parameter.
        en_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

        # Judge.
        for char in text:
            if char in en_chars:
                return ClientBaiduTranslateLangEnum.EN
            elif is_zh(char):
                return ClientBaiduTranslateLangEnum.ZH

    def trans(
        self,
        text: str,
        from_lang: ClientBaiduTranslateLangEnum | ClientBaiduTranslateLangAutoEnum | None = None,
        to_lang: ClientBaiduTranslateLangEnum | None = None
    ) -> str:
        """
        Translate.

        Parameters
        ----------
        text : Text.
            - "self.is_auth is True": Maximum length is 6000.
            - "self.is_auth is False": Maximum length is 3000.
        from_lang : Source language.
            - "None": Automatic judgment.
        to_lang : Target language.
            - "None": Automatic judgment.

        Returns
        -------
        Translated text.
        """

        # Check.
        text_len = len(text)
        if len(text) > self.max_len:
            throw(AssertionError, self.max_len, text_len)

        # Parameter.
        text = text.strip()
        if from_lang is None:
            from_lang = self.get_lang(text)
            from_lang = from_lang or ClientBaiduTranslateLangAutoEnum.AUTO
        if to_lang is None:
            if from_lang == ClientBaiduTranslateLangEnum.EN:
                to_lang = ClientBaiduTranslateLangEnum.ZH
            else:
                to_lang = ClientBaiduTranslateLangEnum.EN

        # Request.
        self.db_record['request_time'] = now()
        response_dict = self.request(text, from_lang, to_lang)
        self.db_record['response_time'] = now()

        # Extract.
        trans_text = '\n'.join(
            [
                trans_text_line_dict['dst']
                for trans_text_line_dict in response_dict['trans_result']
            ]
        )

        # Database.
        self.db_record['input'] = text
        self.db_record['output'] = trans_text
        self.db_record['input_lang'] = from_lang
        self.db_record['output_lang'] = to_lang
        self.db_record.record()

        return trans_text

    def build_db(self) -> None:
        """
        Check and build database tables.
        """

        # Check.
        if self.db_engine is None:
            throw(ValueError, self.db_engine)

        # Parameter.

        ## Table.
        tables = [DatabaseORMTableBaiduTrans]

        ## View stats.
        views_stats = [
            {
                'table': 'stats_baidu_trans',
                'items': [
                    {
                        'name': 'count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "baidu_trans"'
                        ),
                        'comment': 'Request count.'
                    },
                    {
                        'name': 'past_day_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "baidu_trans"'
                            'WHERE DATE_PART(\'day\', NOW() - "request_time") = 0'
                        ),
                        'comment': 'Request count in the past day.'
                    },
                    {
                        'name': 'past_week_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "baidu_trans"'
                            'WHERE DATE_PART(\'day\', NOW() - "request_time") <= 6'
                        ),
                        'comment': 'Request count in the past week.'
                    },
                    {
                        'name': 'past_month_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "baidu_trans"'
                            'WHERE DATE_PART(\'day\', NOW() - "request_time") <= 29'
                        ),
                        'comment': 'Request count in the past month.'
                    },
                    {
                        'name': 'total_input',
                        'select': (
                            'SELECT TO_CHAR(SUM(LENGTH("input")), \'FM999,999,999,999,999\')\n'
                            'FROM "baidu_trans"'
                        ),
                        'comment': 'Input original text total character.'
                    },
                    {
                        'name': 'total_output',
                        'select': (
                            'SELECT TO_CHAR(SUM(LENGTH("output")), \'FM999,999,999,999,999\')\n'
                            'FROM "baidu_trans"'
                        ),
                        'comment': 'Output translation text total character.'
                    },
                    {
                        'name': 'avg_input',
                        'select': (
                            'SELECT TO_CHAR(ROUND(AVG(LENGTH("input"))), \'FM999,999,999,999,999\')\n'
                            'FROM "baidu_trans"'
                        ),
                        'comment': 'Input original text average character.'
                    },
                    {
                        'name': 'avg_output',
                        'select': (
                            'SELECT TO_CHAR(ROUND(AVG(LENGTH("output"))), \'FM999,999,999,999,999\')\n'
                            'FROM "baidu_trans"'
                        ),
                        'comment': 'Output translation text average character.'
                    },
                    {
                        'name': 'last_time',
                        'select': (
                            'SELECT MAX("request_time")\n'
                            'FROM "baidu_trans"'
                        ),
                        'comment': 'Last record request time.'
                    }
                ]
            }
        ]

        # Build.
        self.db_engine.build.build(tables=tables, views_stats=views_stats, skip=True)

    __call__ = trans
