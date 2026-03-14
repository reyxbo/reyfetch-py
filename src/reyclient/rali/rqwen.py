# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time    : 2025-07-17
@Author  : Rey
@Contact : reyxbo@163.com
@Explain : Ali website qwen methods.
"""

from typing import Any, TypedDict, NotRequired, Literal, overload, NoReturn
from collections.abc import Hashable, Iterable, Generator
from json import loads as json_loads
from reydb import rorm, DatabaseEngine
from reykit.rbase import throw
from reykit.rnet import request as reykit_request
from reykit.rtime import now

from ..rbase import ClientDatabaseRecord
from .rbase import ClientAli

__all__ = (
    'DatabaseORMTableAliQwen',
    'ClientAliQwen'
)

# Key 'role' value 'system' only in first.
# Key 'role' value 'user' and 'assistant' can mix.
type ChatRecordRole = Literal['system', 'user', 'assistant']
ChatRecordToken = TypedDict('ChatRecordToken', {'total': int, 'input': int, 'output': int, 'output_think': int | None})
ChatResponseWebItem = TypedDict('ChatResponseWebItem', {'site': str | None, 'icon': str | None, 'index': int, 'url': str, 'title': str})
type ChatResponseWeb = list[ChatResponseWebItem]
ChatRecord = TypedDict(
    'ChatRecord',
    {
        'time': int,
        'role': ChatRecordRole,
        'content': str | None,
        'len': int | None,
        'token': ChatRecordToken | None,
        'web': ChatResponseWeb | None,
        'think': str | None
    }
)
type ChatRecords = list[ChatRecord]
type ChatRecordsIndex = Hashable
type ChatRecordsData = dict[ChatRecordsIndex, ChatRecords]
ChatRecordsAppend = TypedDict('ChatRecordsAppend', {'time': NotRequired[int], 'role': NotRequired[ChatRecordRole], 'content': str})
type ChatRecordsAppends = list[ChatRecordsAppend]
ChatReplyGenerator = Generator[str, Any, None]
ChatThinkGenerator = Generator[str, Any, None]

class DatabaseORMTableAliQwen(rorm.Table):
    """
    Database `ali_qwen` table ORM model.
    """

    __name__ = 'ali_qwen'
    __comment__ = 'Ali API qwen model request record table.'
    id: int = rorm.Field(key_auto=True, comment='ID.')
    request_time: rorm.Datetime = rorm.Field(not_null=True, index_n=True, comment='Request time.')
    response_time: rorm.Datetime = rorm.Field(not_null=True, index_n=True, comment='Response time, when is stream response, then is full return after time.')
    messages: str = rorm.Field(rorm.JSONB, not_null=True, comment='Input messages data.')
    reply: str = rorm.Field(rorm.types.TEXT, not_null=True, comment='Output reply text.')
    think: str = rorm.Field(rorm.types.TEXT, comment='Output deep think text.')
    web: str = rorm.Field(rorm.JSONB, comment='Web search data.')
    token_total: int = rorm.Field(not_null=True, comment='Usage total Token.')
    token_input: int = rorm.Field(not_null=True, comment='Usage input Token.')
    token_output: int = rorm.Field(not_null=True, comment='Usage output Token.')
    token_output_think: int = rorm.Field(comment='Usage output think Token.')
    model: str = rorm.Field(rorm.types.VARCHAR(100), not_null=True, comment='Model name.')

class ClientAliQwen(ClientAli):
    """
    Ali QWen client type.
    Can create database used `self.build_db` method.
    """

    url_api = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation'
    'API request URL.'
    url_doc = 'https://help.aliyun.com/zh/model-studio/use-qwen-by-calling-api?spm=a2c4g.11186623.0.0.330e7d9dSBCaZQ'
    'API document URL.'
    model = 'qwen-turbo-latest'
    'API AI model type.'

    def __init__(
        self,
        key: str,
        db_engine: DatabaseEngine | None = None,
        system: str | None = None,
        rand: float = 0.5,
        history_max_char: int | None = None,
        history_max_time: float | None = None
    ) -> None:
        """
        Build instance attributes.

        Parameters
        ----------
        key : API key.
        db_engine : Database engine, insert request record to table.
        system : AI system description.
        rand : AI reply randomness, value range is `[0,1]`.
        history_max_char : History messages record maximum character count.
        history_max_time : History messages record maximum second.
        """

        # Check.
        if not 0 <= rand <= 1:
            throw(ValueError, rand)

        # Build.
        self.key = key
        self.auth = 'Bearer ' + key
        self.db_engine = db_engine
        self.system = system
        self.rand = rand
        self.history_max_char = history_max_char
        self.history_max_time = history_max_time
        self.data: ChatRecordsData = {}

        # Database.
        self.db_record = ClientDatabaseRecord(self, 'ali_qwen')

        ## Build Database.
        if self.db_engine is not None:
            self.build_db()

    @overload
    def request(self, json: dict, stream: Literal[True]) -> Iterable[str]: ...

    @overload
    def request(self, json: dict, stream: Literal[False]) -> dict: ...

    def request(self, json: dict, stream: bool) -> dict | Iterable[str]:
        """
        Request API.

        Parameters
        ----------
        json : Request body.
        stream : Whether use stream response.

        Returns
        -------
        Response json or iterable.
        """

        # Parameter.
        json['model'] = self.model
        json_params = json.setdefault('parameters', {})
        json_params_temperature = self.rand * 2
        if json_params_temperature == 2:
            json_params_temperature = 1.99
        json_params['temperature'] = json_params_temperature
        json_params['presence_penalty'] = self.rand * 4 - 2
        headers = {'Authorization': self.auth, 'Content-Type': 'application/json'}
        if stream:
            headers['X-DashScope-SSE'] = 'enable'
            json_params['incremental_output'] = True

        # Request.
        response = reykit_request(
            self.url_api,
            json=json,
            headers=headers,
            stream=stream,
            check=True
        )

        # Stream.
        if stream:
            iterable: Iterable[str] = response.iter_lines(decode_unicode=True)
            return iterable

        # Check.
        content_type = response.headers['Content-Type']
        if content_type.startswith('application/json'):
            response_json: dict = response.json()
            if 'code' in response_json:
                throw(AssertionError, response_json)
        else:
            throw(AssertionError, content_type)

        return response_json

    def extract_response_text(self, response_json: dict) -> str | None:
        """
        Extract reply text from response JSON.

        Parameters
        ----------
        response_json : Response JSON.

        Returns
        -------
        Reply text.
        """

        # Extract.
        output_data = response_json.get('output')
        if output_data is not None:
            response_text: str = output_data['choices'][0]['message']['content']
        else:
            response_text = None

        return response_text

    def extract_response_token(self, response_json: dict) -> ChatRecordToken | None:
        """
        Extract usage token data from response JSON.

        Parameters
        ----------
        response_json : Response JSON.

        Returns
        -------
        Usage token data.
        """

        # Extract.
        token_data: dict | None = response_json.get('usage')
        if token_data is not None:
            token_data = {
                'total': token_data['total_tokens'],
                'input': token_data['input_tokens'],
                'output': token_data['output_tokens'],
                'output_think': token_data.get('output_tokens_details', {}).get('reasoning_tokens')
            }

        return token_data

    def extract_response_web(self, response_json: dict) -> ChatResponseWeb | None:
        """
        Extract web data from response JSON.

        Parameters
        ----------
        response_json : Response JSON.

        Returns
        -------
        Web data.
        """

        # Extract.
        json_output: dict = response_json['output']
        search_info: dict = json_output.get('search_info', {})
        web_data: list[dict] = search_info.get('search_results', [])
        for item in web_data:
            item.setdefault('site_name', None)
            item.setdefault('icon', None)
            item['site'] = item.pop('site_name')
            if item['site'] == '':
                item['site'] = None
            if item['icon'] == '':
                item['icon'] = None
        web_data = web_data or None

        return web_data

    def extract_response_think(self, response_json: dict) -> str | None:
        """
        Extract deep think text from response JSON.

        Parameters
        ----------
        response_json : Response JSON.

        Returns
        -------
        Deep think text.
        """

        # Extract.
        json_message: dict = response_json['output']['choices'][0]['message']
        response_think = json_message.get('reasoning_content')
        response_think = response_think or None

        return response_think

    def extract_response_record(self, response_json: dict) -> ChatRecord:
        """
        Extract reply record from response JSON.

        Parameters
        ----------
        response_json : Response JSON.

        Returns
        -------
        Reply record.
        """

        # Extract.
        response_text = self.extract_response_text(response_json)
        response_token = self.extract_response_token(response_json)
        response_web = self.extract_response_web(response_json)
        response_think = self.extract_response_think(response_json)
        if response_text is None:
            response_text_len = None
        else:
            response_text_len = len(response_text)
        chat_record_reply = {
            'time': now('timestamp'),
            'role': 'assistant',
            'content': response_text,
            'len': response_text_len,
            'token': response_token,
            'web': response_web,
            'think': response_think
        }

        return chat_record_reply

    def extract_response_generator(self, response_iter: Iterable[str]):
        """
        Extract reply generator from response JSON.

        Parameters
        ----------
        response_iter : Response iterable.

        Returns
        -------
        Reply Generator.
        """

        # First.
        response_line_first = None
        for response_line in response_iter:
            if not response_line.startswith(('data:{', 'data: {')):
                continue
            response_line_first = response_line
            break

        ## Check.
        if response_line_first is None:
            throw(AssertionError, response_line_first)

        response_line_first = response_line_first[5:].strip()
        response_json_first: dict = json_loads(response_line_first)
        chat_record_reply = self.extract_response_record(response_json_first)
        is_think_emptied = not bool(chat_record_reply['think'])

        def _generator(mode: Literal['text', 'think']) -> Generator[str, Any, None]:
            """
            Generator function of stream response.

            Parameters
            ----------
            mode : Generate value type.
                - `Literal['text']`: Reply text.
                - `Literal['think']`: Deep think text.

            Returns
            -------
            Generator.
            """

            # Parameter.
            nonlocal is_think_emptied
            chat_record_reply['content'] = chat_record_reply['content'] or ''
            chat_record_reply['think'] = chat_record_reply['think'] or ''

            # Check.
            if (
                not is_think_emptied
                and mode == 'text'
            ):
                text = 'must first used up think generator'
                throw(AssertionError, text=text)

            # First.
            if mode == 'text':
                yield chat_record_reply['content']
            elif mode == 'think':
                yield chat_record_reply['think']

            # Next.
            for response_line in response_iter:

                ## Filter.
                if not response_line.startswith(('data:{', 'data: {')):
                    continue

                ## JSON.
                response_line = response_line[5:]
                response_line = response_line.strip()
                response_json: dict = json_loads(response_line)

                ## Token.
                response_token = self.extract_response_token(response_json)
                chat_record_reply['token'] = response_token

                ## Web.
                if chat_record_reply['web'] is None:
                    response_web = self.extract_response_web(response_json)
                    chat_record_reply['web'] = response_web

                ## Text.
                if mode == 'text':
                    response_text = self.extract_response_text(response_json)
                    if response_text is None:
                        continue
                    chat_record_reply['content'] += response_text
                    chat_record_reply['len'] += len(response_text)
                    yield response_text

                ## Think.
                elif mode == 'think':
                    response_think = self.extract_response_think(response_json)

                    ### Last.
                    if response_think is None:
                        is_think_emptied = True
                        response_text = self.extract_response_text(response_json)
                        chat_record_reply['content'] = response_text
                        if response_text is not None:
                            chat_record_reply['len'] += len(response_text)
                        break

                    chat_record_reply['think'] += response_think
                    yield response_think

            # Database.
            else:
                self.insert_db(chat_record_reply)

        generator_text = _generator('text')
        generator_think = _generator('think')

        return chat_record_reply, generator_text, generator_think

    def append_chat_records_history(
        self,
        records: ChatRecordsAppend | ChatRecordsAppends | str | list[str],
        index: ChatRecordsIndex,
        history_max_char: int | None = None,
        history_max_time: float | None = None
    ) -> None:
        """
        Append chat records.
        Delete records of beyond the range from history.

        Parameters
        ----------
        records: Chat reocrds.
            - `Key 'role'`: Message sender role, default `user`.
            - `Key 'content'`: Message content, required.
            - `str`: Message content.
            - `list[str]`: Message content list.
        index : Chat records index.
        history_max_char : History messages record maximum character count.
            - `None`: Use `self.history_max_char`.
        history_max_time : History messages record maximum second.
            - `None`: Use `self.history_max_time`.
        """

        # Parameter.
        if type(records) == str:
            records = [{'content': records}]
        elif type(records) == dict:
            records = [records]
        elif type(records) == list:
            records = [
                {'content': records}
                if type(record) == str
                else record
                for record in records
            ]
        now_timestamp = now('timestamp')
        records = [
            {
                'time': record.get('time', now_timestamp),
                'role': record.get('role', 'user'),
                'content': record['content'],
                'len': len(record['content']),
                'token': None,
                'web': None,
                'think': None
            }
            for record in records
        ]
        chat_records_history: ChatRecords = self.data.setdefault(index, [])

        # Append.
        chat_records_history.extend(records)

        # Sort.
        sort_key = lambda chat_record: chat_record['time']
        chat_records_history.sort(key=sort_key)

        # Beyond.
        self.get_chat_records_history(index, history_max_char, history_max_time, True)

    def get_chat_records_history(
        self,
        index: ChatRecordsIndex,
        history_max_char: int | None = None,
        history_max_time: float | None = None,
        delete: bool = False
    ) -> ChatRecords:
        """
        Get chat records.

        Parameters
        ----------
        index : Chat records index.
        history_max_char : History messages record maximum character count.
            - `None`: Use `self.history_max_char`.
        history_max_time : History messages record maximum second.
            - `None`: Use `self.history_max_time`.
        delete : Whether delete records of beyond the range from history.

        Returns
        -------
        Chat records.
        """

        # Parameter.
        now_timestamp = now('timestamp')
        chat_records_history: ChatRecords = self.data.setdefault(index, [])

        # Max.
        if history_max_char is None:
            history_max_char = self.history_max_char
        if history_max_time is None:
            history_max_time = self.history_max_time
        if history_max_time is not None:
            history_max_time_us = history_max_time * 1000
        char_len = 0
        chat_records_history_reverse = chat_records_history[::-1]
        beyond_index = None
        for index, chat_record in enumerate(chat_records_history_reverse):
            if (
                (
                    history_max_char is not None
                    and (char_len := char_len + chat_record['len']) > history_max_char
                )
                or (
                    history_max_time is not None
                    and now_timestamp - chat_record['time'] > history_max_time_us
                )
            ):
                beyond_index = -index
                break

        # Beyond.
        if beyond_index is not None:

            ## Delete.
            if delete:
                if beyond_index == 0:
                    chat_records_history.clear()
                else:
                    del chat_records_history[:beyond_index]

            ## Keep.
            else:
                if beyond_index == 0:
                    chat_records_history = []
                else:
                    chat_records_history = chat_records_history[beyond_index:]

        return chat_records_history

    @overload
    def chat(
        self,
        text: str,
        index: ChatRecordsIndex | None = None,
        role: str | None = None,
        web: bool = False,
        web_mark: bool = False,
        history_max_char: int | None = None,
        history_max_time: float | None = None
    ) -> ChatRecord: ...

    @overload
    def chat(
        self,
        text: str,
        index: ChatRecordsIndex | None = None,
        system: str | None = None,
        web: bool = False,
        web_mark: bool = False,
        *,
        stream: Literal[True],
        history_max_char: int | None = None,
        history_max_time: float | None = None
    ) -> tuple[ChatRecord, ChatReplyGenerator]: ...

    @overload
    def chat(
        self,
        text: str,
        index: ChatRecordsIndex | None = None,
        system: str | None = None,
        web: bool = False,
        web_mark: bool = False,
        *,
        think: Literal[True],
        stream: Literal[True],
        history_max_char: int | None = None,
        history_max_time: float | None = None
    ) -> tuple[ChatRecord, ChatReplyGenerator, ChatThinkGenerator]: ...

    @overload
    def chat(
        self,
        text: str,
        index: ChatRecordsIndex | None = None,
        system: str | None = None,
        web: bool = False,
        web_mark: bool = False,
        *,
        think: Literal[True],
        history_max_char: int | None = None,
        history_max_time: float | None = None
    ) -> NoReturn: ...

    def chat(
        self,
        text: str,
        index: ChatRecordsIndex | None = None,
        system: str | None = None,
        web: bool = False,
        web_mark: bool = False,
        think: bool = False,
        stream: bool = False,
        history_max_char: int | None = None,
        history_max_time: float | None = None
    ) -> ChatRecord | tuple[ChatRecord, ChatReplyGenerator] | tuple[ChatRecord, ChatReplyGenerator, ChatThinkGenerator]:
        """
        Chat with AI.

        Parameters
        ----------
        text : User chat text.
        index : Chat records index.
            `None`: Not use record.
        system : Extra AI system description, will be connected to `self.system`.
        web : Whether use web search.
        web_mark : Whether display web search citation mark, format is `[ref_<number>]`.
        think : Whether use deep think, when is `True`, then parameter `stream` must also be `True`.
        stream : Whether use stream response, record after full return values.
        history_max_char : History messages record maximum character count.
            - `None`: Use `self.history_max_char`.
        history_max_time : History messages record maximum second.
            - `None`: Use `self.history_max_time`.

        Returns
        -------
        Response content.
        """

        # Check.
        if text == '':
            throw(ValueError, text)
        if think and not stream:
            throw(ValueError, think, stream)

        # Parameter.
        if (
            system is not None
            and self.system is not None
        ):
            system = ''.join([self.system, system])
        elif system is None:
            system = self.system
        json = {'input': {}, 'parameters': {}}

        ## History.
        if index is not None:
            chat_records_history = self.get_chat_records_history(index, history_max_char, history_max_time, True)
        else:
            chat_records_history: ChatRecords = []

        ### Role.
        if system is not None:
            chat_record_role: ChatRecord = {
                'time': now('timestamp'),
                'role': 'system',
                'content': system,
                'len': len(system),
                'token': None,
                'web': None,
                'think': None
            }
            chat_records_role: ChatRecords = [chat_record_role]
        else:
            chat_records_role: ChatRecords = []

        ### Now.
        chat_record_now: ChatRecord= {
            'time': now('timestamp'),
            'role': 'user',
            'content': text,
            'len': len(text),
            'token': None,
            'web': None,
            'think': None
        }
        chat_records_now: ChatRecords = [chat_record_now]

        messages: ChatRecords = chat_records_role + chat_records_history + chat_records_now
        messages = [
            {
                'role': message['role'],
                'content': message['content']
            }
            for message in messages
        ]

        ## Database.
        self.db_record['messages'] = messages
        self.db_record['model'] = self.model

        ## Message.
        json['input']['messages'] = messages
        json['parameters']['result_format'] = 'message'

        ## Web.
        if web:
            json['parameters']['enable_search'] = True
            json['parameters']['search_options'] = {
                'enable_source': True,
                'enable_citation': web_mark,
                'citation_format': '[ref_<number>]',
                'forced_search': False,
                'search_strategy': 'max',
                'prepend_search_result': False,
                'enable_search_extension': True
            }
        else:
            json['parameters']['enable_search'] = False

        ## Think.
        json['parameters']['enable_thinking'] = think

        ## Stream.
        json['stream'] = stream

        # Request.
        self.db_record['request_time'] = now()
        response = self.request(json, stream)
        self.db_record['response_time'] = now()

        # Extract.

        ## Stream.
        if stream:
            response_iter: Iterable[str] = response
            chat_record_reply, generator_text, generator_think = self.extract_response_generator(response_iter)

        ## Not Stream.
        else:
            response_json: dict = response
            chat_record_reply = self.extract_response_record(response_json)

        # Record.
        if index is not None:
            chat_records_history.append(chat_record_now)
            chat_records_history.append(chat_record_reply)

        # Return.
        if stream:
            if think:
                return chat_record_reply, generator_text, generator_think
            else:
                return chat_record_reply, generator_text
        else:

            ## Database.
            self.insert_db(chat_record_reply)

            return chat_record_reply

    def polish(self, text: str) -> str:
        """
        Let AI polish text.

        Parameters
        ----------
        text : Text.

        Returns
        -------
        Polished text.
        """

        # Parameter.
        text = '润色冒号后的内容（注意！只返回润色后的内容正文，之后会直接整段使用）：' + text
        record = self.chat(text)
        result: str = record['content']
        result = result.strip()

        return result

    def build_db(self) -> None:
        """
        Check and build database tables.
        """

        # Check.
        if self.db_engine is None:
            throw(ValueError, self.db_engine)

        # Parameter.

        ## Table.
        tables = [DatabaseORMTableAliQwen]

        ## View stats.
        views_stats = [
            {
                'table': 'stats_ali_qwen',
                'items': [
                    {
                        'name': 'count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "ali_qwen"'
                        ),
                        'comment': 'Request count.'
                    },
                    {
                        'name': 'past_day_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "ali_qwen"'
                            'WHERE DATE_PART(\'day\', NOW() - "request_time") = 0'
                        ),
                        'comment': 'Request count in the past day.'
                    },
                    {
                        'name': 'past_week_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "ali_qwen"'
                            'WHERE DATE_PART(\'day\', NOW() - "request_time") <= 6'
                        ),
                        'comment': 'Request count in the past week.'
                    },
                    {
                        'name': 'past_month_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "ali_qwen"'
                            'WHERE DATE_PART(\'day\', NOW() - "request_time") <= 29'
                        ),
                        'comment': 'Request count in the past month.'
                    },
                    {
                        'name': 'total_token',
                        'select': (
                            'SELECT TO_CHAR(SUM("token_total"), \'FM999,999,999,999,999\')\n'
                            'FROM "ali_qwen"'
                        ),
                        'comment': 'Usage total Token.'
                    },
                    {
                        'name': 'total_token_input',
                        'select': (
                            'SELECT TO_CHAR(SUM("token_input"), \'FM999,999,999,999,999\')\n'
                            'FROM "ali_qwen"'
                        ),
                        'comment': 'Usage input total Token.'
                    },
                    {
                        'name': 'total_token_output',
                        'select': (
                            'SELECT TO_CHAR(SUM("token_output"), \'FM999,999,999,999,999\')\n'
                            'FROM "ali_qwen"'
                        ),
                        'comment': 'Usage output total Token.'
                    },
                    {
                        'name': 'total_token_output_think',
                        'select': (
                            'SELECT TO_CHAR(SUM("token_output_think"), \'FM999,999,999,999,999\')\n'
                            'FROM "ali_qwen"'
                        ),
                        'comment': 'Usage output think total Token.'
                    },
                    {
                        'name': 'avg_token',
                        'select': (
                            'SELECT TO_CHAR(ROUND(AVG("token_total")), \'FM999,999,999,999,999\')\n'
                            'FROM "ali_qwen"'
                        ),
                        'comment': 'Usage average Token.'
                    },
                    {
                        'name': 'avg_token_input',
                        'select': (
                            'SELECT TO_CHAR(ROUND(AVG("token_input")), \'FM999,999,999,999,999\')\n'
                            'FROM "ali_qwen"'
                        ),
                        'comment': 'Usage input average Token.'
                    },
                    {
                        'name': 'avg_token_output',
                        'select': (
                            'SELECT TO_CHAR(ROUND(AVG("token_output")), \'FM999,999,999,999,999\')\n'
                            'FROM "ali_qwen"'
                        ),
                        'comment': 'Usage output average Token.'
                    },
                    {
                        'name': 'avg_token_output_think',
                        'select': (
                            'SELECT TO_CHAR(ROUND(AVG("token_output_think")), \'FM999,999,999,999,999\')\n'
                            'FROM "ali_qwen"'
                        ),
                        'comment': 'Usage output think average Token.'
                    },
                    {
                        'name': 'last_time',
                        'select': (
                            'SELECT MAX("request_time")\n'
                            'FROM "ali_qwen"'
                        ),
                        'comment': 'Last record request time.'
                    }
                ]
            }
        ]

        # Build.
        self.db_engine.build(tables=tables, views_stats=views_stats, skip=True)

    def insert_db(self, record: ChatRecord) -> None:
        """
        Insert record to table of database.

        Parameters
        ----------
        record : Record data.
        """

        # Parameter.
        self.db_record['reply'] = record['content']
        self.db_record['think'] = record['think']
        self.db_record['web'] = record['web']
        self.db_record['token_total'] = record['token']['total']
        self.db_record['token_input'] = record['token']['input']
        self.db_record['token_output'] = record['token']['output']
        self.db_record['token_output_think'] = record['token']['output_think']

        # Insert.
        self.db_record.record()

    __call__ = chat
