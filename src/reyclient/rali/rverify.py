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
from alibabacloud_credentials.models import Config as AliCredentialConfig
from alibabacloud_credentials.client import Client as AliCredentialClient
from alibabacloud_dypnsapi20170525.models import SendSmsVerifyCodeRequest as AliRequest
from alibabacloud_tea_util.models import RuntimeOptions as AliRuntimeOptions
from reydb import rorm, DatabaseEngine
from reykit.rbase import throw

from ..rbase import ClientDatabaseRecord
from .rbase import ClientAli

__all__ = (
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
    request_time: rorm.Datetime = rorm.Field(not_null=True, comment='Request time.')
    response_time: rorm.Datetime = rorm.Field(not_null=True, comment='Response time, when is stream response, then is full return after time.')
    messages: str = rorm.Field(rorm.JSONB, not_null=True, comment='Input messages data.')
    reply: str = rorm.Field(rorm.types.TEXT, not_null=True, comment='Output reply text.')
    think: str = rorm.Field(rorm.types.TEXT, comment='Output deep think text.')
    web: str = rorm.Field(rorm.JSONB, comment='Web search data.')
    token_total: int = rorm.Field(not_null=True, comment='Usage total Token.')
    token_input: int = rorm.Field(not_null=True, comment='Usage input Token.')
    token_output: int = rorm.Field(not_null=True, comment='Usage output Token.')
    token_output_think: int = rorm.Field(comment='Usage output think Token.')
    model: str = rorm.Field(rorm.types.VARCHAR(100), not_null=True, comment='Model name.')

class ClientAliVerify(ClientAli):
    """
    Ali verify client type.
    """

class ClientAliVerifySms(ClientAliVerify):
    """
    Ali verify sms client type.
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
        code_len : Code length.
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

    def send(self, phone: str) -> str:
        """
        Send random code sms.

        Parameters
        ----------
        phone : Phone number.

        Returns
        -------
        Code.
        """

        # Parameter.
        valid_time = self.valid_m * 60
        template_param = '{"code":"##code##","min":"%s"}' % self.valid_m
        request = AliRequest(
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

        return response.body.model.verify_code

    async def async_send(self, phone: str) -> str:
        """
        Asynchronous send random code sms.

        Parameters
        ----------
        phone : Phone number.

        Returns
        -------
        Code.
        """

        # Parameter.
        valid_time = self.valid_m * 60
        template_param = '{"code":"##code##","min":"%s"}' % self.valid_m
        request = AliRequest(
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

        return response.body.model.verify_code
