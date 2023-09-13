import os
from urllib.parse import urlsplit, quote
from constants import TWITTER_BASE_URL


def is_allowed_media_url(value):
    try:
        url = urlsplit(value)
        return url.scheme == 'https' and url.hostname == 'pbs.twimg.com' and url.port in (None, 443) and not url.username and not url.password and url.path.startswith('/media/')
    except (TypeError, ValueError):
        return False


class Crawler:
    def __init__(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        driver_path = os.getenv('CHROMEDRIVER_PATH')
        if not driver_path or not os.path.isfile(driver_path):
            raise RuntimeError('Provide an explicitly installed trusted ChromeDriver')
        options = Options()
        options.add_argument('--headless=new')
        self.driver = webdriver.Chrome(service=Service(driver_path), options=options)
        self.driver.set_page_load_timeout(15)

    def get_image_links(self, handle):
        from bs4 import BeautifulSoup
        self.driver.get(TWITTER_BASE_URL + quote(handle, safe=''))
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        links = [image.get('src') for image in soup.find_all('img') if is_allowed_media_url(image.get('src'))]
        return list(dict.fromkeys(links))[:5]

    def close(self):
        self.driver.quit()
