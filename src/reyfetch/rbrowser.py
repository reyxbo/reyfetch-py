# !/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time    : 2025-10-24
@Author  : Rey
@Contact : reyxbo@163.com
@Explain : Browser methods.
"""

from typing import Any, Literal
from traceback import format_exc
from enum import StrEnum
from selenium.webdriver import Edge, Chrome, EdgeOptions, ChromeOptions
from reydb import rorm, DatabaseEngine
from reykit.rbase import throw
from reykit.rnet import join_url
from reykit.rtime import TimeMark, now, sleep

from .rbase import FetchCrawl

__all__ = (
    'CrawlBrowserPageStatusEnum',
    'DatabaseORMTableCrawlBrowserPage',
    'FetchCrawlBrowser',
    'crawl_page',
    'add_db_crawl_task',
    'wait_db_crawl_task',
    'crawl_page_use_db'
)

class CrawlBrowserPageStatusEnum(StrEnum):
    """
    Crawl browser page status enumeration type.
    """

    WAIT = 'wait'
    'Wait crawl.'
    SUCCESS = 'success'
    'Crawl successded.'
    FAIL = 'fail'
    'Crawl failed.'
    CANCEL = 'cancel'
    'Crawl cancelled.'

class DatabaseORMTableCrawlBrowserPage(rorm.Table):
    """
    Database `crawl_browser_page` table ORM model.
    """

    __name__ = 'crawl_browser_page'
    __comment__ = 'Crawl browser page HTML text table.'
    create_time: rorm.Datetime = rorm.Field(field_default=':time', not_null=True, index_n=True, comment='Record create time.')
    update_time: rorm.Datetime = rorm.Field(field_default=':time', arg_default=now, index_n=True, comment='Record update time.')
    id: int = rorm.Field(key_auto=True, comment='ID.')
    url: str = rorm.Field(rorm.types.VARCHAR(8182), not_null=True, comment='Target URL.')
    html: str = rorm.Field(rorm.types.TEXT, comment='Crawled HTML text.')
    status: int = rorm.Field(rorm.ENUM(CrawlBrowserPageStatusEnum), field_default=CrawlBrowserPageStatusEnum.WAIT, not_null=True, comment='Crawl status.')
    note: str = rorm.Field(rorm.types.VARCHAR(500), comment='Note.')

class FetchCrawlBrowser(FetchCrawl):
    """
    Control browser fetch type.
    """

    def __init__(
        self,
        driver: Literal['edge', 'chrome'] = 'edge',
        headless: bool = True,
        echo: bool = False,
        db_engine: DatabaseEngine | None = None
    ) -> None:
        """
        Build instance attributes.

        Parameters
        ----------
        driver : Browser driver type.
            - `Literal['edge']`: Edge browser.
            - `Literal['chrome']`: Chrome browser.
        headless : Whether use headless mode.
        echo : Whether to print the report.
        db_engine : Database engine.
            - `None`: Not use database.
            - `Database`: Automatic crawl page by database table.
        """

        # Parameter.
        self.echo = echo
        self.db_engine = db_engine
        match driver:
            case 'edge':
                driver_type = Edge
                driver_option_type = EdgeOptions
            case 'chrome':
                driver_type = Chrome
                driver_option_type = ChromeOptions

        # Build.

        ## Build Database.
        if self.db_engine is not None:
            self.build_db()

        ## Driver.
        options = driver_option_type()
        if headless:
            options.add_argument('--headless')
        self.driver = driver_type(options)

        ## Crawl by database.
        if self.db_engine is not None:
            self.__loop_crawl_by_db()

    def build_db(self) -> None:
        """
        Check and build database tables.
        """

        # Check.
        if self.db_engine is None:
            throw(ValueError, self.db_engine)

        # Parameter.

        ## Table.
        tables = [DatabaseORMTableCrawlBrowserPage]

        # Build.

        ## WeChat.
        self.db_engine.build.build(tables=tables, skip=True)

    def __loop_crawl_by_db(self) -> None:
        """
        Loop crawl by database table.
        """

        # Echo.
        if self.echo:
            print('Start loop crawl by database table.')

        # Loop.
        while True:

            ## Crawl.
            self.__crawl_by_db()

            ## Sleep.
            sleep(1)

    def __crawl_by_db(self) -> None:
        """
        Crawl by database table.
        """

        # Get task.
        task_table = self.db_engine.execute.select(
            'crawl_browser_page',
            ['id', 'url'],
            f'"status" = \'{CrawlBrowserPageStatusEnum.WAIT}\'',
            order='"create_time" ASC'
        )

        # Crawl.
        for id_, url in task_table:
            try:
                self.request(url)
            except BaseException:
                exc_text = format_exc()
                print(exc_text)
                status = CrawlBrowserPageStatusEnum.FAIL
            else:
                status = CrawlBrowserPageStatusEnum.SUCCESS

            ## Database.
            data = {
                'id': id_,
                'update_time': ':NOW()',
                'html': self.page,
                'status': status
            }
            self.db_engine.execute.update('crawl_browser_page', data)

    def request(
        self,
        url: str,
        params: dict[str, Any] | None = None
    ) -> None:
        """
        Request URL.

        Parameters
        ----------
        url : URL.
        params : URL parameters.
        """

        # Parameter.
        params = params or {}
        url = join_url(url, **params)

        # Echo.
        if self.echo:
            print(f'Crawl URL "{url}"')

        # Request.
        self.driver.get(url)

    @property
    def page(self) -> str:
        """
        Return page elements document.

        Returns
        -------
        Page elements document.
        """

        # Parameter.
        page_source = self.driver.page_source

        return page_source

    __call__ = request

def crawl_page(
    url: str,
    params: dict[str, Any] | None = None
) -> str:
    """
    Crawl page elements document.

    Parameters
    ----------
    url : URL.
    params : URL parameters.

    Returns
    -------
    Page elements document.
    """

    # Parameter.
    browser = FetchCrawlBrowser(headless=True)

    # Request.
    browser.request(url, params)

    # Page.
    page = browser.page

    return page

def add_db_crawl_task(
    db_engine: DatabaseEngine,
    url: str,
    params: dict[str, Any] | None = None,
    note: str | None = None
) -> int:
    """
    Add crawl task into database table.

    Parameters
    ----------
    db_engine : Database engine.
    url : Target URL.
    params : URL parameters.
    note : Note.

    Returns
    -------
    Record ID.
    """

    # Parameter.
    params = params or {}
    url = join_url(url, **params)

    # Inesrt.
    data = {'url': url, 'note': note}
    result = db_engine.execute.insert(
        'crawl_browser_page',
        data,
        returning='id'
    )
    record_id: int = result.scalar()

    return record_id

def wait_db_crawl_task(
    db_engine: DatabaseEngine,
    record_id: int,
    timeout: int = 60
) -> str:
    """
    Wait crawl task of database table, and get HTML text.

    Parameters
    ----------
    db_engine : Database engine.
    record_id : Record ID.
    timeout : Timeout seconds.

    Returns
    -------
    HTML text.
    """

    # Loop.
    tm = TimeMark()
    tm()
    while True:

        # Select.
        result = db_engine.execute.select(
            'crawl_browser_page',
            ['html', 'status'],
            '"id" = :record_id',
            limit=1,
            record_id=record_id
        )

        # Check.
        if result.empty:
            throw(AssertionError, record_id)

        # Complete.
        row = result.to_row()
        if row['status'] == CrawlBrowserPageStatusEnum.SUCCESS:
            html = row['html']
            return html

        # Timeout.
        tm()
        if tm.total_spend > timeout:
            throw(TimeoutError, record_id)

        # Sleep.
        sleep(1)

def crawl_page_use_db(
    db_engine: DatabaseEngine,
    url: str,
    params: dict[str, Any] | None = None,
    note: str | None = None,
    timeout: int = 60
) -> str:
    """
    Add crawl task into database table, wait and get HTML text.

    Parameters
    ----------
    db_engine : Database engine.
    url : Target URL.
    params : URL parameters.
    note : Note.
    timeout : Timeout seconds.

    Returns
    -------
    HTML text.
    """

    # Add.
    record_id = add_db_crawl_task(db_engine, url, params, note)

    # Wait.
    html = wait_db_crawl_task(db_engine, record_id, timeout)

    return html
