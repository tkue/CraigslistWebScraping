import requests
import json
import sqlite3

from bs4 import BeautifulSoup
from bs4.element import Tag

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from enum import Enum

import urllib.parse

START_URL = 'https://washingtondc.craigslist.org/d/apts-housing-for-rent/search/apa'
POST_URL = 'https://washingtondc.craigslist.org/mld/apa/d/newly-renovated-2-bedroom/6607509502.html'
CONFIG_PATH = 'config.json'


class TagNotFoundException(Exception):
    pass


class WebDriverType(Enum):
    CHROME = 'chrome'


class Utility(object):
    @staticmethod
    def try_to_get_tag_class(tag: Tag):
        ret = ''
        try:
            ret = tag['class'][0]
        except:
            pass

        return ret

    @staticmethod
    def try_to_get_tag_contents(tag: Tag):
        ret = ''
        try:
            # # ret = tag.contents[0]
            # contents = []
            # for content in tag.contents:
            #     contents.append(content)
            #     # if type(content) == str:
            #     #     contents.append(content)
            #     # else:
            #     #     contents.append(content.text)
            #
            # ret = ''.join(contents)
            ret = tag.text
        except:
            pass

        return ret

    @staticmethod
    def get_tag_class_and_content_as_dict(tag: Tag):
        if not tag:
            return

        key = Utility.try_to_get_tag_class(tag)
        val = Utility.try_to_get_tag_contents(tag)

        if not key and not val:
            return

        if not key:
            key = val

        if not val:
            val = key

        m = {key: val}

        return m


class CraigslistConfig(object):
    @staticmethod
    def get_entire_config():
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)

    @staticmethod
    def get_database_name():
        return CraigslistConfig.get_entire_config()['database']['name']

    @staticmethod
    def get_database_schema_script():
        return CraigslistConfig.get_entire_config()['database']['schema_script']

    @staticmethod
    def get_driver_arguments(driver_type: WebDriverType):
        if not driver_type == WebDriverType.CHROME:
            raise NotImplementedError

        config = CraigslistConfig.get_entire_config()

        args = []
        for arg in config['selenium']['chrome_driver_arguments']:
            args.append(arg)

        return args

    @staticmethod
    def get_driver_path(driver_type: WebDriverType):
        ret = ''
        if driver_type == WebDriverType.CHROME:
            ret = CraigslistConfig.get_entire_config()['selenium']['chrome_driver_path']

        return ret


class CraigslistDatabase(object):

    @staticmethod
    def get_conn():
        return sqlite3.connect(CraigslistConfig.get_database_name())

    @staticmethod
    def create_schema():
        try:
            conn = CraigslistDatabase.get_conn()
            # with open(CraigslistConfig.get_database_schema_script(), 'r') as f:
            #     query = f.readlines()
            cur = conn.cursor()
            cur.executescript(CraigslistConfig.get_database_schema_script())

            conn.commit()
        except sqlite3.Error as se:
            print('Failed to create database: \n{0}'.format(se))
            conn.rollback()
        except Exception as e:
            print('Failed to create database: \n{0}'.format(e))
            conn.rollback()
        finally:
            conn.close()


class Session(object):
    def __init__(self, start_url: str, comment: str = None):
        if None == comment:
            comment = ''
        self.comment = comment
        self.batch_id = 0
        self.start_url = start_url

        self.insert_batch()

    def insert_batch(self):
        import datetime

        try:
            conn = CraigslistDatabase.get_conn()
            cur = conn.cursor()

            cur.execute("""INSERT INTO Batch (
                                StartDate
                                ,Comment
                            )
                            VALUES(?, ?)""", (datetime.datetime.now(),
                                              self.comment)
                        )
            conn.commit()
            self.batch_id = cur.lastrowid
        except sqlite3.Error as e:
            conn.rollback()
            print('Failed to insert batch: {0}'.format(e))
        finally:
            conn.close()

    def update_batch_end(self):
        import datetime

        try:
            conn = CraigslistDatabase.get_conn()
            cur = conn.cursor()

            cur.execute('UPDATE Batch SET EndDate = ? WHERE BatchId = ?', (datetime.datetime.now(), self.batch_id))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            print('Failed to update end date for batch: {0}'.format(e))
        finally:
            conn.close()

    def process_page(self, url: str):
        print('Processing: {0}'.format(url))

        r = requests.get(url)

        soup = BeautifulSoup(r.text, 'html.parser')
        page = SearchResultsPage(soup, self, START_URL)
        page.process_search_results_page()

        next_url = page.get_next_page_url()

        if not (not next_url):
            self.process_page(next_url)


class SearchResultsPage(object):
    def __init__(self, soup: BeautifulSoup, session: Session, page_url: str):
        self.soup = soup
        self.session = session
        self.page_url = page_url

    def get_all_result_items(self):
        if not self.soup:
            return

        results = self.soup.find('ul', class_='rows')
        if not results:
            raise TagNotFoundException('No tag found for ul tags with class = rows')

        result_items = results.find_all('li', class_='result-row')

        search_result_items = []

        for row in result_items:
            search_result_items.append(SearchResultItem(row))

        return search_result_items

    def get_existing_urls(self):
        conn = CraigslistDatabase.get_conn()
        cur = conn.cursor()

        existing_urls = []
        try:
            cur.execute('SELECT DISTINCT Url FROM SearchResult')
            for row in cur.fetchall():
                existing_urls.append(str(row[0]).strip().lower())
        except sqlite3.Error as e:
            print('Unable to get URLs: \n{0}'.format(e))

        return existing_urls

    # TODO: Check to make sure records are not duplicated
    def insert_records(self, records: []):
        if not records:
            return

        conn = CraigslistDatabase.get_conn()
        cur = conn.cursor()

        existing_urls = self.get_existing_urls()

        for result in records:
            try:
                if None != result.href and str(result.href).strip().lower() in existing_urls:
                    continue
                cur.execute("""INSERT INTO SearchResult (
                                        BatchId
                                        ,Name
                                        ,Url
                                        ,Timestamp
                                        ,Price
                                    )
                                    VALUES (
                                        ?, ?, ?, ?, ?
                                    )
                                """, (self.session.batch_id,
                                      result.name,
                                      result.href,
                                      result.timestamp,
                                      result.price))
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                print('Failed to insert row: {0}'.format(e))

    def process_search_results_page(self):
        records = self.get_all_result_items()
        self.insert_records(records)

    def get_next_page_url(self):
        url = ''
        try:
            try:
                url = self.soup.find('div', class_='paginator buttongroup firstpage').find(class_='buttons').find(
                    class_='button next').attrs['href']
            except:
                url = self.soup.find('div', class_='paginator buttongroup').find(class_='buttons').find(
                    class_='button next').attrs['href']
            url = urllib.parse.urljoin(self.page_url, url)
        except:
            pass

        return url


class SearchResultItem(object):
    def __init__(self, tag: Tag):
        self.tag = tag
        self._result_info = self.__get_result_info()

        self.name = self.__get_name()
        self.price = self.__get_price()
        self.timestamp = self.__get_timestamp()
        self.href = self.__get_href()
        self.metadata = self.__get_metadata()

    def __get_result_info(self):
        try:
            ret = self.tag.find(class_='result-info')

            if not ret:
                raise TagNotFoundException
        except TagNotFoundException:
            print('Failed to find result-info tag')

        return ret

    def __get_name(self):
        try:
            ret = self.tag.find(class_='result-title hdrlnk').text

            if not ret:
                return ''

            return ret
        except:
            return ''

    def __get_price(self):
        # price_str = ''
        try:
            price_str = self.tag.find('span', class_='result-price').text
        except:
            return -1

        import re

        if not price_str:
            return -1

        ret = re.sub('[^\d]', '', price_str)

        if not ret:
            return -1

        return ret

    def __get_timestamp(self):
        try:
            ret = self._result_info.find('time', class_='result-date').attrs['datetime']
            if not ret:
                return ''
            return ret
        except:
            return ''

    def __get_href(self):
        try:
            ret = self._result_info.find(class_='result-title hdrlnk').attrs['href']
            if not ret:
                return ''
            return ret
        except:
            return ''

    def __get_metadata(self):
        m = {}
        listing_metadata = self._result_info.find_all('span')

        if not listing_metadata:
            return

        # TODO: only getting first metadata item for each item
        for metadata_item in listing_metadata:
            key = None
            value = None
            try:
                if metadata_item.attrs['class']:
                    key = metadata_item.attrs['class'][0]
                if metadata_item.contents:
                    value = metadata_item.contents[0]
            except:
                pass

            m[key] = value

        if not m:
            m = {''}

        return m


class CraigslistPost(object):
    def __init__(self, url: str, driver: webdriver):
        self.url = url
        self.driver = driver

        self.title = self.__get_title()
        self.price = self.__get_price()
        self.post_description = self.__get_post_description()

        map_attrs = self.__get_map_attributes()
        self.latitude = map_attrs['data-latitude']
        self.longitude = map_attrs['data-longitude']
        self.data_accuracy = map_attrs['data-accuracy']

        self.attributes = self._get_post_attributes()

    def __get_title(self):
        try:
            return self.driver.find_element_by_xpath('/html/body/section/section/h2').text
        except NoSuchElementException:
            return ''

    def __get_price(self):
        try:
            price_str = self.driver.find_element_by_xpath('/html/body/section/section/h2/span[2]/span[1]').text
            if not price_str:
                return -1

            import re

            return re.sub('[^\d]', '', price_str)
        except NoSuchElementException:
            return -1

    def __get_post_description(self):
        try:
            return self.driver.find_element_by_xpath('//*[@id="postingbody"]').text
        except NoSuchElementException:
            return ''

    def __get_attribute_html(self):
        return self.driver.find_element_by_xpath('/html/body/section/section/section/div[1]').get_attribute('innerHTML')

    def __get_map_attributes(self):
        soup = BeautifulSoup(attr_html, 'html.parser')
        map = soup.find('div', class_='mapbox').find(id='map')

        return map.attrs

        # return {
        #     'latitude': map.attrs['data-latitude'],
        #     'longitude': map.attrs['data-longitude'],
        #     'data_accuracy': map.attrs['data-accuracy']
        # }

    def _get_post_attributes(self):
        spans = []

        for attr in soup.find_all(class_='attrgroup'):
            attr_spans = attr.find_all('span')
            for span in attr_spans:
                spans.append(span)

        attributes = []
        for span in spans:
            attributes.append(span.text)

        return attributes


def get_driver_options(driver_type: WebDriverType):
    opts = None
    if driver_type == WebDriverType.CHROME:
        opts = ChromeOptions()

        args = CraigslistConfig.get_driver_arguments(driver_type)
        if not args:
            return opts

        for arg in args:
            opts.add_argument(arg)

    return opts


def get_webdriver(driver_type: WebDriverType):
    opts = get_driver_options(driver_type)
    if driver_type == WebDriverType.CHROME:
        return webdriver.Chrome(executable_path=CraigslistConfig.get_driver_path(driver_type), chrome_options=opts)


def main():
    CraigslistDatabase.create_schema()
    session = Session(start_url=START_URL)
    session.process_page(START_URL)


if __name__ == '__main__':
    # main()

    post_url = 'https://washingtondc.craigslist.org/nva/apa/d/quiet-cul-de-sac-3-brfenced/6600199455.html'

    driver_type = WebDriverType.CHROME
    driver = get_webdriver(driver_type)

    driver.get(post_url)

    title = driver.find_element_by_xpath('/html/body/section/section/h2').text
    price = driver.find_element_by_xpath('/html/body/section/section/h2/span[2]/span[1]').text
    house_description = driver.find_element_by_xpath('/html/body/section/section/h2/span[2]/span[2]').text
    post_description = driver.find_element_by_xpath('//*[@id="postingbody"]').text

    attr_html = driver.find_element_by_xpath('/html/body/section/section/section/div[1]').get_attribute('innerHTML')

    soup = BeautifulSoup(attr_html, 'html.parser')
    map = soup.find('div', class_='mapbox').find(id='map')
    latitude = map.attrs['data-latitude']
    longitude = map.attrs['data-longitude']
    data_accuracy = map.attrs['data-accuracy']

    attributes = {}
    # spans = soup.find_all('span')
    spans = []

    for attr in soup.find_all(class_='attrgroup'):
        attr_spans = attr.find_all('span')
        for span in attr_spans:
            spans.append(span)

    all_attributes = []
    for span in spans:
        all_attributes.append(span.text)

    for a in all_attributes:
        print(a)

    # soup.find_all(class_='attrgroup')[1].find_all('span')

    # for span in spans:
    #     key = None
    #     value = None
    #     print(span.text)
    #
    #     d = Utility.get_tag_class_and_content_as_dict(span)
    #
    #     if not d:
    #         continue
    #
    #     for k, v in d.items():
    #         attributes[k] = v
    #
    # for k, v in attributes.items():
    #     print(k)
    #     print(v)
    #     print('\n')

    print('')

    #

    # r = requests.get(START_URL)
    #
    # soup = BeautifulSoup(r.text, 'html.parser')
    # page = SearchResultsPage(soup, session, START_URL)
    # page.process_search_results_page()

    # page.soup.find('div', class_='paginator buttongroup firstpage').find(class_='buttons').find(class_='button next').attrs['href']
    # urllib.parse.urljoin(page.page_url, page.soup.find('div', class_='paginator buttongroup firstpage').find(class_='buttons').find(class_='button next').attrs['href'])
    print('')

    # r = requests.get(START_URL)
    #
    # soup = BeautifulSoup(r.text, 'html.parser')
    #
    # page = SearchResultsPage(soup)
    # results = page.get_all_result_items()
    #
    #
    #
    # conn = CraigslistDatabase.get_conn()
    # cur = conn.cursor()
    #
    # existing_urls = []
    # try:
    #     cur.execute('SELECT DISTINCT Url FROM SearchResult')
    #     for row in cur.fetchall():
    #         existing_urls.append(str(row[0]).strip().lower())
    # except sqlite3.Error as e:
    #     print('Unable to get URLs: \n{0}'.format(e))
    #
    # print(existing_urls)
    #
    # for result in results:
    #     try:
    #         if None != result.href and str(result.href).strip().lower() in existing_urls:
    #             continue
    #         cur.execute("""INSERT INTO SearchResult (
    #                             BatchId
    #                             ,Name
    #                             ,Url
    #                             ,Timestamp
    #                             ,Price
    #                         )
    #                         VALUES (
    #                             ?, ?, ?, ?, ?
    #                         )
    #                     """, (session.batch_id,
    #                           result.name,
    #                           result.href,
    #                           result.timestamp,
    #                           result.price))
    #         conn.commit()
    #     except sqlite3.Error as e:
    #         conn.rollback()
    #         print('Failed to insert row: {0}'.format(e))
    #         # print(sql)

    # print(ConfigOption.get_database_name())

    # print(CraigslistConfig.get_database_name())
    # cfg = CraigslistConfig(path='config.json')
    # print(cfg.get_database_name())
    # file = ''
    # with open(CONFIG, 'r') as f:
    #     file = json.load(f)
    #
    # print(file['database']['name'])

    # r = requests.get(START_URL, 'html.parser')
    #
    # soup = BeautifulSoup(r.text)
    #
    #
    # results_page = SearchResultsPage(soup)
    #
    # search_results = results_page.get_all_result_items()

    # for result in search_results:
    #     print(result.name)
    #     print(result.href)
    #     print('\n')

    # results = soup.find('ul', class_='rows')
    # result_items = results.find_all('li', class_='result-row')
    #
    # for row in result_items:
    #     search_result_item = SearchResultItem(row)
    #
    #     print(search_result_item.name)
    #     print(search_result_item.href)
    #     # print(search_result_item.metadata)
    #     print('\n')

    # timestamp = result_items[0].find(class_='result-info').find('time', class_='result-date').attrs['datetime']
    # link_to_post = result_items[0].find(class_='result-info').find(class_='result-title hdrlnk').attrs['href']
    # metadata = result_items[0].find(class_='result-info').find(class_='result-meta').find_all('span')
    # metadata_key = result_items[0].find(class_='result-info').find(class_='result-meta').find_all('span')[0].attrs['class']
    # metadata_value = result_items[0].find(class_='result-info').find(class_='result-meta').find_all('span')[0].contents[0]

    # print(result_items[0])
