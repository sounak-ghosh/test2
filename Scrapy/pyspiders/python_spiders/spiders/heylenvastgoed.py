# -*- coding: utf-8 -*-

import re
import scrapy
from ..items import ListingItem
from ..helper import remove_unicode_char, remove_white_spaces, currency_parser, extract_number_only


def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city



class HeylenvastgoedSpider(scrapy.Spider):
    """ heylenvastgoed """
    name = "heylenvastgoed"
    allowed_domains = ["heylenvastgoed.be"]
    start_urls = (
        'http://www.heylenvastgoed.be/',
    )
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'
    current_page = 1
    position = 0

    def start_requests(self):
        start_urls = [
            {'url': 'https://www.heylenvastgoed.be/nl/te-huur/woningen',\
                 'property_type': 'house'},
            {'url': 'https://www.heylenvastgoed.be/nl/te-huur/appartementen',\
                 'property_type': 'apartment'},
        ]
        for url in start_urls:
            yield scrapy.Request(url=url.get('url'),
                                 callback=self.parse,
                                 meta={'property_type': url.get('property_type'),
                                       'url': url.get('url')})

    def parse(self, response):
        listings = response.xpath(
            ".//a[contains(@class, 'property-contents') and not(contains(@href,\
                 'referenties'))]/@href")
        for property_item in listings:
            property_url = property_item.extract()
            yield scrapy.Request(url=property_url,
                                 callback=self.get_details,
                                 meta={'property_type': response.meta.get('property_type'),
                                       'url': response.meta.get('url')})

        if listings:
            self.current_page += 1
            next_page_url = "{}/pagina-{}".format(response.meta.get('url') ,self.current_page)
            yield scrapy.Request(
                url=next_page_url,
                meta={'property_type': response.meta.get('property_type'),
                      'url': response.meta.get('url')}
            )

    def get_details(self, response):
        self.position += 1
        property_type = response.meta.get('property_type')
        images = response.xpath(".//li[@class='photo']//a/@href").extract()
        external_link = response.url
        title = ''.join(response.xpath(".//section[@id='property__title']\
            //div[@class='name']//text()").extract())
        rent = ''.join(response.xpath(".//section[@id='property__title']\
            //div[@class='price']//text()").extract())
        room_count = ''.join(response.xpath(".//section[@id='property__title']\
            //li[@class='rooms']/text()").extract())
        square_meters = ''.join(response.xpath(".//section[@id='property__title']\
            //li[@class='area']/text()").extract())
        address = ''.join(response.xpath(".//section[@id='property__title']\
            //div[@class='address']/text()").extract())
        description = ''.join(response.xpath(".//div[@id='description']//text()").extract())
        floor = ''.join(response.xpath(
            ".//div[contains(.//dt//text(), 'verdieping') and \
                not(contains(.//dt//text(), '(en)'))]/dd/text()").extract())
        terrace = ''.join(response.xpath(".//div[contains(.//dt//text(), \
            'terras')]/dd/text()").extract())
        elevator = ''.join(response.xpath(".//div[contains(.//dt//text(), \
            'lift')]/dd/text()").extract())
        furnished = ''.join(response.xpath(
            ".//div[contains(.//dt//text(), 'gemeubeld') and\
                 not(contains(.//dt//text(), '(en)'))]/dd/text()").extract())
        parking = ''.join(response.xpath(".//li[contains(@class,\'garages')]/text()").extract())
        js_code = response.xpath(".//script[contains(., 'markerContent')]//text()").extract_first()
        js_code = remove_white_spaces(js_code).split(';')
        landlord_phone = '03 260 46 66'
        landlord_name = 'Heylen Vastgoed Turnhout'
        landlord_email = 'info@heylenvastgoed.be'
        zipcode, city = extract_city_zipcode(address)

        item = ListingItem()
        item['external_source'] = "Heylenvastgoed_PySpider_belgium_fr"
        item['images'] = images
        item['external_link'] = external_link
        item['title'] = remove_white_spaces(title)
        item['address'] = remove_white_spaces(address)
        if rent:
            item['rent'] = extract_number_only(remove_unicode_char(rent))
            item['currency'] = currency_parser(rent)
        if room_count:
            item['room_count'] = extract_number_only(room_count)
        if square_meters:
            item['square_meters'] = extract_number_only(remove_unicode_char(square_meters))
        item['description'] = remove_white_spaces(description)
        if floor:
            item['floor'] = floor
        if 'ja' in furnished.lower():
            item['furnished'] = True
        if 'ja' in parking.lower():
            item['parking'] = True
        if len(js_code) >= 2:
            item['latitude'] = re.search(r"[+-]?\d+\.\d+", js_code[0]).group(0)
            item['longitude'] = re.search(r"[+-]?\d+\.\d+", js_code[1]).group(0)
        item['position'] = self.position
        item['property_type'] = property_type
        item['landlord_phone'] = landlord_phone
        item['landlord_name'] = landlord_name
        item['landlord_email'] = landlord_email
        item['zipcode'] = zipcode
        item['city'] = city
        if terrace:
            if 'ja' in terrace:
                item['terrace'] = True
            else:
                item['terrace'] = False
        if elevator:
            if 'ja' in elevator:
                item['elevator'] = True
            else:
                item['elevator'] = False
        if item.get('rent', None):
            item['rent'] = int(item['rent']) if item['rent'].isdigit() else None
        if item.get('room_count', None):
            item['room_count'] = int(item['room_count']) if item['room_count'].isdigit() else None
        if item.get('square_meters', None):
            item['square_meters'] = int(item['square_meters']) if item['square_meters'].isdigit() else None
        yield item
