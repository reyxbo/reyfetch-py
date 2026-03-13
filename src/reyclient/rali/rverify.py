# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time    : 2026-03-13
@Author  : Rey
@Contact : reyxbo@163.com
@Explain : Ali website verify methods.
"""

from alibabacloud_dypnsapi20170525.client import Client as AliClient
from alibabacloud_tea_openapi.models import Config as AliConfig
from alibabacloud_tea_openapi.exceptions import ClientException
from alibabacloud_credentials.models import Config as AliCredentialConfig
from alibabacloud_credentials.client import Client as AliCredentialClient
from alibabacloud_dypnsapi20170525.models import SendSmsVerifyCodeRequest as AliSendRequest, CheckSmsVerifyCodeRequest as AliCheckRequest
from alibabacloud_tea_util.models import RuntimeOptions as AliRuntimeOptions
from reydb import rorm, DatabaseEngine
from reykit.rbase import throw

from ..rbase import ClientDatabaseRecord
from .rbase import ClientAli

__all__ = (
    'DatabaseORMTableAliVerifySms',
    'ClientAliVerify',
    'ClientAliVerifySms'
)

class DatabaseORMTableAliVerifySms(rorm.Table):
    """
    Database `ali_verify_sms` table ORM model.
    """

    __name__ = 'ali_verify_sms'
    __comment__ = 'Ali API verify sms request record table.'
    id: int = rorm.Field(key_auto=True, comment='ID.')
    send_time: rorm.Datetime = rorm.Field(not_null=True, comment='Send code time.')
    verify_time: rorm.Datetime = rorm.Field(comment='Verification code time.')
    phone: str = rorm.Field(rorm.types.CHAR(11), not_null=True, comment='Phone number.')
    code: str = rorm.Field(rorm.types.VARCHAR(8), not_null=True, comment='Verification code.', len_min=4, len_max=8)
    verified: bool = rorm.Field(field_default='FALSE', not_null=True, comment='Is the verified.')
    note: str = rorm.Field(rorm.types.VARCHAR(500), comment='Note.')

class ClientAliVerify(ClientAli):
    """
    Ali verify client type.
    """

class ClientAliVerifySms(ClientAliVerify):
    """
    Ali verify sms client type.
    Can create database used "self.build_db" method.
    """

    def __init__(
        self,
        key_id: str,
        key_secret: str,
        db_engine: DatabaseEngine | None = None,
        code_len=4,
        valid_m: int = 5,
        interval_s = 60
    ) -> None:
        """
        Build instance attributes.

        Parameters
        ----------
        key_id : Access key ID.
        key_secret : Access key secret.
        db_engine : Database engine, insert request record to table.
        code_len : Code length, [4-8].
        valid_m : Code valid minutes.
        interval_s : Resend interval seconds.
        """

        # Build.
        self.key_id = key_id
        self.key_secret = key_secret
        self.db_engine = db_engine
        self.code_len = code_len
        self.valid_m = valid_m
        self.interval_s = interval_s

        # Client.
        credential_config = AliCredentialConfig(
                type='access_key',
                access_key_id=key_id,
                access_key_secret=key_secret
        )
        credential_client = AliCredentialClient(credential_config)
        config = AliConfig(
            credential=credential_client,
            endpoint='dypnsapi.aliyuncs.com'
        )
        self.client = AliClient(config)

        # Database.
        self.db_record = ClientDatabaseRecord(self, 'ali_verify_sms')

        ## Build Database.
        if self.db_engine is not None:
            self.build_db()

    def send(self, phone: str, note: str | None = None) -> str:
        """
        Send random verification code sms.

        Parameters
        ----------
        phone : Phone number.
        note : Note.

        Returns
        -------
        Verification code.
        """

        # Parameter.
        valid_time = self.valid_m * 60
        template_param = '{"code":"##code##","min":"%s"}' % self.valid_m
        request = AliSendRequest(
            phone_number=phone,
            sign_name='速通互联验证码',
            template_code='100001',
            template_param=template_param,
            code_length=self.code_len,
            valid_time=valid_time,
            interval=self.interval_s,
            return_verify_code=True
        )
        runtime = AliRuntimeOptions()

        # Request.
        response = self.client.send_sms_verify_code_with_options(request, runtime)

        # Check.
        if not response.body.success:
            throw(AssertionError, response.body.message)

        # Database.
        code: str = response.body.model.verify_code
        self.db_record['send_time'] = ':NOW():'
        self.db_record['phone'] = phone
        self.db_record['code'] = code
        self.db_record['note'] = note
        self.db_record.record()

        return response.body.model.verify_code

    async def async_send(self, phone: str, note: str | None = None) -> str:
        """
        Asynchronous send random verification code sms.

        Parameters
        ----------
        phone : Phone number.
        note : Note.

        Returns
        -------
        Verification code.
        """

        # Parameter.
        valid_time = self.valid_m * 60
        template_param = '{"code":"##code##","min":"%s"}' % self.valid_m
        request = AliSendRequest(
            phone_number=phone,
            sign_name='速通互联验证码',
            template_code='100001',
            template_param=template_param,
            code_length=self.code_len,
            valid_time=valid_time,
            interval=self.interval_s,
            return_verify_code=True
        )
        runtime = AliRuntimeOptions()

        # Request.
        response = await self.client.send_sms_verify_code_with_options_async(request, runtime)

        # Check.
        if not response.body.success:
            throw(AssertionError, response.body.message)

        # Database.
        code: str = response.body.model.verify_code
        self.db_record['send_time'] = ':NOW():'
        self.db_record['phone'] = phone
        self.db_record['code'] = code
        self.db_record['note'] = note
        self.db_record.record()

        return response.body.model.verify_code

    def check(self, phone: str, code: str) -> bool:
        """
        Check code.

        Parameters
        ----------
        phone : Phone number.
        code : Verification code.

        Returns
        -------
        Check result.
        """

        # Parameter.
        request = AliCheckRequest(
            phone_number=phone,
            verify_code=code
        )
        runtime = AliRuntimeOptions()

        # Request.
        try:
            self.client.check_sms_verify_code_with_options(request, runtime)
        except ClientException:
            return False

        # Database.
        sql = (
            f'UPDATE "{DatabaseORMTableAliVerifySms.__tablename__}"\n'
            'SET "verify_time" = NOW(),\n'
            '    "verified" = TRUE\n'
            'WHERE (\n'
            '    "phone" = :phone\n'
            '    AND "code" = :code\n'
            ')'
        )
        self.db_engine.execute(sql, phone=phone, code=code)

        return True

    async def async_check(self, phone: str, code: str) -> bool:
        """
        Asynchronous check code.

        Parameters
        ----------
        phone : Phone number.
        code : Verification code.

        Returns
        -------
        Check result.
        """

        # Parameter.
        request = AliCheckRequest(
            phone_number=phone,
            verify_code=code
        )
        runtime = AliRuntimeOptions()

        # Request.
        try:
            await self.client.check_sms_verify_code_with_options(request, runtime)
        except ClientException:
            return False

        # Database.
        sql = (
            f'UPDATE "{DatabaseORMTableAliVerifySms.__tablename__}"\n'
            'SET "verify_time" = NOW(),\n'
            '    "verified" = TRUE\n'
            'WHERE (\n'
            '    "phone" = :phone\n'
            '    AND "code" = :code\n'
            ')'
        )
        self.db_engine.execute(sql)

        return True

    def build_db(self) -> None:
        """
        Check and build database tables.
        """

        # Check.
        if self.db_engine is None:
            throw(ValueError, self.db_engine)

        # Parameter.

        ## Table.
        tables = [DatabaseORMTableAliVerifySms]

        ## View stats.
        views_stats = [
            {
                'table': 'stats_ali_verify_sms',
                'items': [
                    {
                        'name': 'count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "ali_verify_sms"'
                        ),
                        'comment': 'Request count.'
                    },
                    {
                        'name': 'past_day_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "ali_verify_sms"'
                            'WHERE DATE_PART(\'day\', NOW() - "send_time") = 0'
                        ),
                        'comment': 'Request count in the past day.'
                    },
                    {
                        'name': 'past_week_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "ali_verify_sms"'
                            'WHERE DATE_PART(\'day\', NOW() - "send_time") <= 6'
                        ),
                        'comment': 'Request count in the past week.'
                    },
                    {
                        'name': 'past_month_count',
                        'select': (
                            'SELECT COUNT(1)\n'
                            'FROM "ali_verify_sms"'
                            'WHERE DATE_PART(\'day\', NOW() - "send_time") <= 29'
                        ),
                        'comment': 'Request count in the past month.'
                    }
                ]
            }
        ]

        # Build.
        self.db_engine.build.build(tables=tables, views_stats=views_stats, skip=True)
