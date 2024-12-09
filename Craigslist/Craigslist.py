from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement

from enum import Enum


CHROME_DRIVER_PATH = '../drivers/chromedriver'

APT_URL = 'https://washingtondc.craigslist.org/d/apts-housing-for-rent/search/apa'


class CraigslistResultsView(Enum):
    THUMBNAIL = 'thumbnail'
    GALLERY = 'gallery'
    LIST = 'list'



class ListingSearchResult(object):
    def __init__(self, element: WebElement):
        self.element = element

        if not self.element.get_attribute('result-row') == 'result-row':
            raise NotImplementedError





def set_results_view(driver: webdriver, view_type: CraigslistResultsView):
    if not driver:
        return

    try:
        view_dropdown = driver.find_element_by_xpath('//*[@id="searchform"]/div[3]/div[1]/div/ul')

        if view_type == CraigslistResultsView.GALLERY:
            view_dropdown.find_element_by_xpath('//*[@id="gridview"]').click()
        elif view_type == CraigslistResultsView.THUMBNAIL:
            view_dropdown.find_element_by_xpath('//*[@id="picview"]').click()
        elif view_dropdown == CraigslistResultsView.LIST:
            view_dropdown.find_element_by_xpath('//*[@id="listview"]').click()
    except NoSuchElementException as ex:
        print('Unable to find view dropdown')


if __name__ == '__main__':
    opts = ChromeOptions()
    opts.add_argument('--start-maximized')

    driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, chrome_options=opts)
    driver.get(APT_URL)





cla    print('end')