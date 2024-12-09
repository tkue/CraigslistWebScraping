import json
import logging

from enum import Enum
from StringUtil import StringUtil

import os


# from .WebScrapingSession import WebDriverType

class WebDriverType(Enum):
    CHROME = 'chrome'


class NullValueError(Exception):
    pass


class InvalidConfigError(Exception):
    pass


class Config(object):
    __DEFAULT_LOGGING_LEVEL = logging.DEBUG

    # TODO: Handle logger here?
    # TODO: Better initialization
    def __init__(self, config_path: str):
        if not config_path:
            raise NullValueError

        self.config_path = os.path.abspath(config_path)
        self.config = self.__read_config(self.config_path)

        if not self.config:
            raise InvalidConfigError

    @staticmethod
    def __read_config(config_path: str):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except:
            pass

    def __get_logging_level(self):
        level = self.config['logging']['level']
        if not level:
            return self.__DEFAULT_LOGGING_LEVEL

        level = str(level).strip().lower()

        if level == 'critical':
            return logging.CRITICAL
        elif level == 'error':
            return logging.ERROR
        elif level == 'warning':
            return logging.WARNING
        elif level == 'info':
            return logging.INFO
        elif level == 'debug':
            return logging.DEBUG
        elif level == 'notset':
            return logging.NOTSET
        else:
            return self.__DEFAULT_LOGGING_LEVEL

    def get_logger(self):
        logging.basicConfig(level=self.__get_logging_level())
        return logging.getLogger(__name__)


class WebScrapingConfig(Config):
    def __init__(self, config_path: str):
        super(WebScrapingConfig, self).__init__(config_path)

    def get_database_name(self):
        return self.config['database']['name']

    def get_database_schema_script(self):
        return self.config['database']['schema_script']

    def get_driver_arguments(self, driver_type: WebDriverType):
        if driver_type.value == WebDriverType.CHROME.value:

            args = []
            for arg in self.config['selenium']['chrome_driver_arguments']:
                args.append(arg)
        else:
            raise NotImplementedError

        return args

    def get_driver_options(self, driver_type: WebDriverType):
        if driver_type.value == WebDriverType.CHROME.value:
            from selenium.webdriver.chrome.options import Options as ChromeOptions

            opts = ChromeOptions()

            for arg in self.get_driver_arguments(driver_type):
                opts.add_argument(arg.strip())

            return opts

        else:
            raise NotImplementedError



    def get_driver_path(self, driver_type: WebDriverType):
        if driver_type.value == WebDriverType.CHROME.value:
            path = self.config['selenium']['chrome_driver_path']
            return os.path.abspath(path)
        else:
            raise NotImplementedError

    def get_start_url(self):
        return self.config['session']['start_url']

    def get_original_ip(self):
        """
        Original host IP address
        *** The IP address you want to mask ***
        :return:
        :rtype:
        """
        return self.config['connection']['original_public_ip']

    def get_is_need_mask_ip(self):
        is_need_mask_ip = self.config['connection']['is_need_mask_ip'].strip()
        return StringUtil.get_boolean_from_string(is_need_mask_ip)
