# -*- coding: utf-8 -*-
import os
from time import sleep
import scrapy
from selenium import webdriver
from scrapy import Selector
import selenium.webdriver.support.ui as ui
from selenium.webdriver.common.keys import Keys
from ..helper import remove_unicode_char, remove_white_spaces, extract_number_only, currency_parser
from ..items import ListingItem


class ImmocomSpider(scrapy.Spider):
    name = 'orta'
    allowed_domains = ['orta.be']
    start_urls = ['https://www.orta.be/fr/residentiel/louer-bien-immobilier/maison']
    position = 0
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'

    def getDriver(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless"')
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1904x950')
        chrome_options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(os.getcwd() + '/chromedriver-mac', chrome_options=chrome_options)

        driver.create_options()
        driver.implicitly_wait(10)
        return driver

    def parse(self, response, **kwargs):
        start_urls = [
            {'url': 'https://www.orta.be/fr/residentiel/louer-bien-immobilier/maison',
             'property_type': 'house'},
            # {'url': 'http://www.orta.be/fr/residentiel/louer-bien-immobilier/appartement',
            #  'property_type': 'apartment'},
            # {'url': 'http://www.orta.be/fr/residentiel/louer-bien-immobilier/flat',
            #  'property_type': 'apartment'},
        ]
        property_urls = []
        for url in start_urls:
            driver = self.getDriver()
            driver.get(url.get('url'))
            driver.implicitly_wait(10)
            sleep(10)
            len_of_page = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage="
                                              "document.body.scrollHeight;return lenOfPage;")
            # Scroll till end logic
            match = False
            while not match:
                last_count = len_of_page
                sleep(5)
                len_of_page = driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);var lenOfPage="
                    "document.body.scrollHeight;return lenOfPage;")
                if last_count == len_of_page:
                    match = True
            # Scroll till end logic end
            listing_selector = Selector(text=driver.page_source)
            listings = listing_selector.xpath(".//div[contains(@class, 'liste_biens')]//a/@href").extract()
            new_json = [{'url': response.urljoin(property_item), 'property_type': url.get('property_type')} for
                        property_item in listings]
            property_urls.extend(new_json)
        print("Selenium portion done, doing scrapy work")
        for property_url in property_urls:
            yield scrapy.Request(
                url=property_url.get('url'),
                callback=self.get_details,
                meta={'property_type': property_url.get('property_type')}
            )

    def get_details(self, response):
        self.position += 1
        property_type = response.meta.get('property_type')
        external_link = response.url
        images = response.xpath(".//div[@class='slide']//a/@href").extract()
        external_id = ''.join(response.xpath(".//p[contains(.//text(), 'Référence')]//b//text()").extract())
        title = response.xpath(".//div[@class='bien__content']//h2//text()").extract_first()
        rent = ''.join(response.xpath(".//td[contains(.//text(), 'Loyer / mois')]"
                                      "/following-sibling::td[1]//text()").extract())
        square_meters = ''.join(response.xpath(".//td[contains(.//text(), 'Superficie habitable')]"
                                      "/following-sibling::td[1]//text()").extract())
        room_count = ''.join(response.xpath(".//td[contains(.//text(), 'Nbre de chambres')]"
                                      "/following-sibling::td[1]//text()").extract())
        city_zip = ''.join(response.xpath(".//td[contains(.//text(), 'Code postal')]"
                                      "/following-sibling::td[1]//text()").extract())
        floor = ''.join(response.xpath(".//td[contains(.//text(), 'Etage')]"
                                      "/following-sibling::td[1]//text()").extract())
        furniture = ''.join(response.xpath(".//td[contains(.//text(), 'Meublé')]"
                                      "/following-sibling::td[1]//text()").extract())
        description = ''.join(response.xpath(".//div[@class='bien__content']//p//text()").extract())

        landlord_name = 'Trevi Orta'
        landlord_phone = ''.join(response.xpath(".//div[contains(@class, 'bien__contact')]//a[contains(@href, 'tel:')]//text()").extract())

        item = ListingItem()
        item['external_source'] = "Orta_PySpider_belgium_fr"
        item['property_type'] = property_type
        item['external_link'] = external_link
        item['images'] = images
        item['external_id'] = external_id
        item['title'] = remove_white_spaces(title)
        if rent:
            item['rent'] = extract_number_only(remove_unicode_char(''.join(rent.split('.'))))
            item['currency'] = currency_parser(rent)
        if square_meters:
            item['square_meters'] = extract_number_only(remove_unicode_char(square_meters))
        if square_meters:
            item['room_count'] = extract_number_only(room_count)
        if city_zip:
            item['city'], item['zipcode'] = city_zip.split(' - ')
        item['description'] = remove_white_spaces(description)
        if floor:
            item['floor'] = floor
        if furniture:
            if 'Oui' in furniture:
                item['furnished'] = True
            else:
                item['furnished'] = False
        item['landlord_name'] = landlord_name
        item['landlord_phone'] = landlord_phone
        item['position'] = self.position
        if item.get('rent', None):
            item['rent'] = int(item['rent']) if item['rent'].isdigit() else None
        if item.get('room_count', None):
            item['room_count'] = int(item['room_count']) if item['room_count'].isdigit() else None
        if item.get('square_meters', None):
            item['square_meters'] = int(item['square_meters']) if item['square_meters'].isdigit() else None
        yield item
