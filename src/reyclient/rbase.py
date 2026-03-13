# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time    : 2023-12-29
@Author  : Rey
@Contact : reyxbo@163.com
@Explain : Base methods.
"""

from typing import Any, Protocol
from types import MethodType
from threading import get_ident as threading_get_ident
from reydb import Database
from reykit.rbase import Base

__all__ = (
    'ClientBase',
    'Client',
    'ClientWithDatabase',
    'ClientDatabaseRecord'
)

class ClientBase(Base):
    """
    Client base type.
    """

class ClientWithDatabase(ClientBase, Protocol):
    """
    With database method reuqest API fetch type.
    Can create database used `self.build_db` method.
    """

    db_engine: Database | None
    build_db: MethodType

class ClientDatabaseRecord(ClientBase):
    """
    Request API fetch type of record into the database, can multi threaded.
    """

    def __init__(
        self,
        api: ClientWithDatabase | None = None,
        table: str | None = None
    ) -> None:
        """
        Build instance attributes.

        Parameters
        ----------
        api : `API` instance.
            - `None`: Not record.
        table : Table name.
        """

        # Build.
        self.api = api
        self.table = table
        self.data: dict[int, dict[str, Any]] = {}

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Update record data parameter.

        Parameters
        ----------
        key : Parameter key.
        value : Parameter value.
        """

        # Check.
        if self.api.db_engine is None:
            return

        # Parameter.
        thread_id = threading_get_ident()
        record = self.data.setdefault(thread_id, {})

        # Update.
        record[key] = value

    def record(self) -> None:
        """
        Insert record to table of database.
        """

        # Check.
        if self.api.db_engine is None:
            return

        # Parameter.
        thread_id = threading_get_ident()
        record = self.data.setdefault(thread_id, {})

        # Insert.
        self.api.db_engine.execute.insert(self.table, record)

        # Delete.
        del self.data[thread_id]
