import os
import sqlite3
import logging
import datetime

from enum import Enum
from logging import Logger

from Config import Config
from Config import WebScrapingConfig

import sys

sys.path.append('../BaseUtils')

import DatabaseUtils
from NetworkUtil import NetworkUtil
from Validator import Validator


class WebDriverType(Enum):
    CHROME = 'chrome'

class TagNotFoundException(Exception):
    pass


class WebScrapingSession(object):
    logger = ...  # type: Logger

    def __init__(self, config_path: str, batch_comment=None):
        self.config = WebScrapingConfig(config_path=config_path)
        self.logger = self.config.get_logger()

        if not self.is_can_continue_with_connection():
            self.logger.critical('IP address is not masked and should be. Exiting')
            exit(1)

        self.database = DatabaseUtils.Sqlite3Database(
            database_path=self.config.get_database_name(),
            logger=self.logger,
            schema_script_path=self.config.get_database_schema_script()
        )
        self.batch_id = 0
        self.batch_comment = batch_comment

    @staticmethod
    def get_current_ip():
        return NetworkUtil.get_public_ip()

    def is_ip_masked(self):
        original_ip = self.config.get_original_ip().strip()
        current_ip = WebScrapingSession.get_current_ip()

        if not Validator.is_valid_ip_address(original_ip) or not Validator.is_valid_ip_address(current_ip):
            self.logger.critical(
                'Unable to determine if IP is masked or not because one or both IPs compared are invalid')
            self.logger.critical('Original IP: {0}\nCurrent IP: {1}'.format(original_ip, current_ip))
            raise Exception

        if original_ip != current_ip:
            return True
        else:
            self.logger.info('IP address not masked:\n\tOriginal IP: {0}\n\tCurrent IP: {1}'.format(original_ip, current_ip))
            return False

    def is_can_continue_with_connection(self):
        """
        Can we continue with everything if we need to mask our IP and the IP is successfully masked?
        :return:
        :rtype:
        """

        if not self.config.get_is_need_mask_ip():
            return True

        if self.config.get_is_need_mask_ip() and self.is_ip_masked():
            return True

        return False

    def start_session(self):
        """
        What to do at start of a webscraping session
        :return:
        :rtype:
        """
        self._insert_batch()

    def end_session(self):
        """
        What to do at end of webscraping session
        :return:
        :rtype:
        """
        self._update_batch_end()

    def _insert_batch(self):
        """
        Insert record into Batch at start
        :return:
        :rtype:
        """
        import datetime

        conn = self.database.get_conn()
        try:
            cur = conn.cursor()

            cur.execute("""INSERT INTO Batch (
                                        StartDate
                                        ,Comment
                                    )
                                    VALUES(?, ?)""", (datetime.datetime.now(),
                                                      self.batch_comment)
                        )
            conn.commit()
            self.batch_id = cur.lastrowid
        except sqlite3.Error as e:
            conn.rollback()
            self.logger.error('Failed to insert batch: {0}'.format(e))
        finally:
            conn.close()

    def _update_batch_end(self):
        import datetime

        conn = self.database.get_conn()
        try:
            cur = conn.cursor()

            cur.execute('UPDATE Batch SET EndDate = ? WHERE BatchId = ?', (datetime.datetime.now(), self.batch_id))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            self.logger.error('Failed to update end date for batch (BatchId = {0}): {1}'.format(self.batch_id, e))
        finally:
            conn.close()


if __name__ == '__main__':
    session = WebScrapingSession('Craigslist/config.json')
