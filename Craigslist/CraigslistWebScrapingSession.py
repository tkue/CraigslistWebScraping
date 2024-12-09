import urllib

import sys

import requests

sys.path.append('..')
from WebScrapingSession import *

sys.path.append('../../BaseUtils')
from StringUtil import StringUtil

from bs4 import BeautifulSoup
from bs4.element import Tag

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import NoSuchElementException

__CONFIG_PATH = 'config.json'
__SESSION_DESCRIPTION = 'Craigslist session'


class CraigslistConfig(WebScrapingConfig):
    def __init__(self, config_path: str):
        super(CraigslistConfig, self).__init__(config_path=config_path)


class AttributeType(Enum):
    BATHROOM = 'bathroom'
    BEDROOM = 'bedroom'


class CraigslistPost(object):

    def __init__(self, url: str, driver: webdriver):
        self.url = url
        self.driver = driver

        self.driver.get(url)

        self.title = self.__get_title()
        self.price = self.__get_price()
        self.post_description = self.__get_post_description()

        map_attrs = self.__get_map_attributes()
        self.latitude = map_attrs['data-latitude']
        self.longitude = map_attrs['data-longitude']
        self.data_accuracy = map_attrs['data-accuracy']

        self.attributes = self._get_post_attributes()

        self.number_of_bedrooms = self._get_number_of_bedrooms()
        self.number_of_bathrooms = self._get_number_bathrooms()
        self.amount_square_feet = self._get_size_square_ft()
        self.post_date = self._get_post_date()

    def __get_title(self):
        try:
            return self.driver.find_element_by_xpath('/html/body/section/section/h2').text
        except NoSuchElementException:
            return None

    def __get_price(self):
        try:
            price_str = self.driver.find_element_by_xpath('/html/body/section/section/h2/span[2]/span[1]').text
            if not price_str:
                return None

            # import re
            #
            # return re.sub('[^(\d|\.)]', '', price_str)
            return StringUtil.get_money_from_string(price_str)
        except NoSuchElementException:
            return None

    def __get_post_description(self):
        try:
            return self.driver.find_element_by_xpath('//*[@id="postingbody"]').text
        except NoSuchElementException:
            return None

    def __get_attribute_html(self):
        return self.driver.find_element_by_xpath('/html/body/section/section/section/div[1]').get_attribute('innerHTML')

    def __get_map_attributes(self):
        attr_html = self.driver.find_element_by_xpath('/html/body/section/section/section/div[1]').get_attribute('innerHTML')
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

        attr_html = self.driver.find_element_by_xpath('/html/body/section/section/section/div[1]').get_attribute(
            'innerHTML')
        soup = BeautifulSoup(attr_html, 'html.parser')

        for attr in soup.find_all(class_='attrgroup'):
            attr_spans = attr.find_all('span')
            for span in attr_spans:
                spans.append(span)

        attributes = []
        for span in spans:
            attributes.append(span.text)

        return attributes

    def _get_post_date(self):
        return self.driver.find_element_by_xpath('//*[@id="display-date"]/time').get_attribute('datetime')

    def _get_size_square_ft(self):
        if not self.attributes:
            return

        import re

        for attr in self.attributes:
            if not attr:
                continue

            attr = StringUtil.strip_tolower(attr)

            if 'ft2' in attr:
                attr = re.sub('ft2', '', attr)
                attr = StringUtil.remove_everything_but_numbers(attr)
                return attr

    def _get_attribute(self, attr_type: AttributeType):
        """
        Mainly used for getting number of bedrooms or bathrooms
        :param attr_type:
        :type attr_type:
        :return: number of bedrooms or bathrooms
        :rtype: float (e.g 2.5 bath) or int (e.g. 2 bath)
        """
        if not self.attributes:
            return

        import re

        pat_int = None  # regex to math ints with
        pat_decimal = None  # regex to match decimals with
        pat_basic = None  # basic value to see if that string is in the attribute

        ret = None

        # Bedrooms
        if attr_type.value == AttributeType.BEDROOM.value:
            pat_decimal = '\d\.\d(?=bd)'
            pat_int = '\d+(?=bd)'
            pat_basic = 'bd'
        # Bathrooms
        elif attr_type.value == AttributeType.BATHROOM.value:
            pat_decimal = '\d\.\d(?=ba)'
            pat_int = '\d+(?=ba)'
            pat_basic = 'ba'
        else:
            raise NotImplementedError

        for attr in self.attributes:
            if not attr:
                continue

            attr = StringUtil.strip_tolower(attr)

            if pat_basic in attr:
                # Example: '4BR / 3.5Ba'

                # Check to see if number we want is a decimal
                ret = re.findall(pat_decimal, attr)

                if ret:
                    is_contains_decimal = True
                else:
                    is_contains_decimal = False

                # When we don't find a decimal
                if not ret:
                    ret = re.findall(pat_int, attr)
                    if ret:
                        is_contains_decimal = False

                # Didn't find anything
                if not ret:
                    continue

                # Assume first result is good
                if ret and type(ret) in [list, tuple]:
                    ret = ret[0]

                # Shouldn't hit this point, but makes sure to remove everything but numbers or decimals
                if not str(ret).isnumeric() or is_contains_decimal:
                    if is_contains_decimal:
                        ret = float(StringUtil.remove_everything_but_decimals(ret))
                    if not is_contains_decimal:
                        ret = int(StringUtil.remove_everything_but_numbers(ret))

                break

        return ret

    def _get_number_of_bedrooms(self):
        return self._get_attribute(AttributeType.BEDROOM)

    def _get_number_of_bedrooms(self):
        return self._get_attribute(AttributeType.BEDROOM)

    def _get_number_bathrooms(self):
        """

        :return: number of bathrooms
        :rtype: float (e.g. 2.5 bath) or int (e.g. 2 bath)
        """
        import re

        bathrooms = None

        for attr in self.attributes:
            if 'ba' in attr:

                # Example: '4BR / 3.5Ba'

                # Check to see if number we want is a decimal
                bathrooms = re.findall('\d\.\d(?=ba)', attr)

                if bathrooms:
                    is_contains_decimal = True
                else:
                    is_contains_decimal = False

                # When we don't find a decimal
                if not bathrooms:
                    bathrooms = re.findall('\d+(?=ba)', attr)
                    if bathrooms:
                        is_contains_decimal = False

                # Assume first result is good
                if bathrooms and type(bathrooms) in [list, tuple]:
                    bathrooms = bathrooms[0]

                # Shouldn't hit this point, but makes sure to remove everything but numbers or decimals
                if not str(bathrooms).isnumeric() or is_contains_decimal:
                    if is_contains_decimal:
                        bathrooms = float(StringUtil.remove_everything_but_decimals(bathrooms))
                    if not is_contains_decimal:
                        bathrooms = int(StringUtil.remove_everything_but_numbers(bathrooms))

                break

        return bathrooms


class CraigslistWebScrapingSession(WebScrapingSession):
    def __init__(self,
                 config_path: str,
                 batch_comment: str = None):
        super(CraigslistWebScrapingSession, self).__init__(config_path=config_path,
                                                           batch_comment=batch_comment)

        self.web_driver_type = WebDriverType.CHROME
        self.existing_urls = self.__get_existing_urls()
        self.driver = self.__get_webdriver()

        self.start_url = self.config.get_start_url()


    def start_session(self):
        self.process_search_results_page(self.start_url)

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

        key = CraigslistWebScrapingSession.try_to_get_tag_class(tag)
        val = CraigslistWebScrapingSession.try_to_get_tag_contents(tag)

        if not key and not val:
            return

        if not key:
            key = val

        if not val:
            val = key

        m = {key: val}

        return m

    def __get_existing_urls(self):
        """
        Get URLs that have already been scraped
        :return:
        :rtype:
        """
        conn = self.database.get_conn()
        cur = conn.cursor()

        existing_urls = []
        try:
            cur.execute('SELECT DISTINCT Url FROM Product')
            for row in cur.fetchall():
                existing_urls.append(str(row[0]).strip().lower())
        except sqlite3.Error as e:
            self.logger.error('Unable to get URLs: \n{0}'.format(e))

        return existing_urls

    def process_craistlist_post(self, post: CraigslistPost):
        # location

        if not post:
            return

        if not post.latitude and not post.longitude:
            self.logger.info('Page does not have latitude or longitude. Skipping for {0}'.format(post.url))
            return

        address_id = None

        conn = self.database.get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                            INSERT INTO Location (
                                Latitude
                                ,Longitude
                            )
                            VALUES (?, ?)
                        """, post.latitude, post.longitude)
            conn.commit()
            address_id = conn.cur.lastrowid
        except sqlite3.Error as e:
            conn.rollback()
            self.logger.error('Failed to insert latitude and longitude for {0}'.format(post.url))
        finally:
            cur.close()

        # Product
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO Product (
                    BatchId
                    ,LocationId
                    ,Url
                    ,Name
                    ,Price
                    ,Title
                    ,DescriptionBody
                    ,BedroomNumber
                    ,BathroomNumber
                    ,AmountSpaceSquareFt
                    ,CraigslistPostDate
                    ,IsActive
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            """, self.batch_id,
                        address_id,
                        post.url,
                        post.title,
                        post.post_description,
                        post.number_of_bedrooms,
                        post.number_of_bathrooms,
                        post.amount_square_feet,
                        post.post_date,
                        1
                        )
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            self.logger.error('Failed to insert record for post {0}\nException: {1}'.format(post.url, e))
        finally:
            cur.close()

    def process_search_results_page(self, url):
        if not url:
            self.logger.error('No URL passed to process search results page')
            return

        self.logger.info('Processing: {0}'.format(url))

        page = SearchResultsPage(self, url)

        # TODO: Take out enumerate
        for i, post in enumerate(page.get_craigslist_posts()):
            if i > 2:
                break
            try:
                self.process_craistlist_post(post)
            except:
                pass

    def process_page(self, url: str):
        if not url:
            return

        self.logger.info('Processing: {0}'.format(url))

    def __get_webdriver(self):
        if self.web_driver_type.value == WebDriverType.CHROME.value:
            opts = self.config.get_driver_options(self.web_driver_type)
            return webdriver.Chrome(executable_path=self.config.get_driver_path(self.web_driver_type),
                                    chrome_options=opts)
        else:
            raise NotImplementedError


class SearchResultsPage(object):
    def __init__(self,
                 session: CraigslistWebScrapingSession,
                 page_url: str):

        self.session = session
        self.page_url = page_url

        r = requests.get(self.page_url)
        self.soup = BeautifulSoup(r.text, 'html.parser')

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

    def get_craigslist_posts(self):
        """
        Get list of Craigslist posts
        :return: pages
        :rtype: list of CraigslistPost
        """
        pages = []
        records = self.get_all_result_items()
        existing_urls = self.session.existing_urls


        # TODO: Remember to take out check for first few records
        for i, record in enumerate(records):
            if i > 2:
                break
            if StringUtil.strip_tolower(record.href) in existing_urls:
                continue

            try:
                page = CraigslistPost(record.href, self.session.driver)
                pages.append(page)
            except Exception as e:
                self.session.logger.error('Failed to process page {0}: {1}'.format(record.href, e))

        return pages

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


if __name__ == '__main__':
    post_url = 'https://washingtondc.craigslist.org/doc/apa/d/beautiful-house-across-from/6642890739.html'
    search_url = 'https://washingtondc.craigslist.org/search/doc/apa'

    url = 'https://washingtondc.craigslist.org/nva/apa/d/3-bedroom-car-wash-area-extra/6638719660.html'

    session = CraigslistWebScrapingSession('config.json')
    session.start_session()

    # driver = session.driver


    # search_page = SearchResultsPage(session, search_url)
    # items = search_page.get_all_result_items()
    #
    # for item in items:
    #     print(item.href)

    # post = CraigslistPost(url, driver)

    print('')
