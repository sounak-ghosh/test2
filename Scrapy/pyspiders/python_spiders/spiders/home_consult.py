# -*- coding: utf-8 -*-

import scrapy
import js2xml
from ..helper import remove_white_spaces, remove_unicode_char, extract_number_only, currency_parser, format_date
from ..items import ListingItem


def extract_city_zipcode(_address):
    _address = remove_white_spaces(_address)
    zipcode = _address.split(" ")[-2]
    city = _address.split(" ")[-1]
    # city = ' '.join(zip_city.split(" ")[1:])
    return city, zipcode

class HomeConsultSpider(scrapy.Spider):
    """ website_name """
    name = "home_consult"
    allowed_domains = ["home-consult.be"]
    start_urls = ['https://www.home-consult.be/en/for-rent/houses/apartments/']
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'
    position = 0

    def parse(self, response, **kwargs):
        listings = response.xpath(".//ul[@id='props']//a[@class='prop-images-container']/@href").extract()
        for property_url in listings:
            yield scrapy.Request(
                url=property_url,
                callback=self.get_details
            )
        next_page_url = ''.join(response.xpath(".//div[contains(@class, 'bottom')]"
                                               "//li[contains(@class, 'right')]//text()").extract())
        if next_page_url:
            url = "{}order-by-date/page-{}/".format(self.start_urls[0], remove_white_spaces(next_page_url))
            yield scrapy.Request(
                url=url,
                callback=self.parse
            )

    def get_details(self, response):
        self.position +=1
        external_link = response.url
        title = ''.join(response.xpath(".//div[@id='content']//h1//text()").extract())
        address = ''.join(response.xpath(".//address//text()").extract())
        city, zipcode = extract_city_zipcode(address)
        room_count = ''.join(response.xpath(".//li[@class='bedroom']//text()").extract())
        square_meters = ''.join(response.xpath(".//li[@class='terracearea']//text()").extract())
        if not square_meters:
            square_meters = ''.join(response.xpath(".//li[@class='area']//text()").extract())
        rent = ''.join(response.xpath(".//div[contains(.//dt//text(), 'Price')]/dd//text()").extract())
        available_date = ''.join(response.xpath(".//div[contains(.//dt//text(), 'Available')]/dd//text()").extract())
        elevator = ''.join(response.xpath(".//div[contains(.//dt//text(), 'Elevator')]/dd//text()").extract())
        furnished = ''.join(response.xpath(".//div[contains(.//dt//text(), 'Furnished')]/dd//text()").extract())
        # floor = ''.join(response.xpath(".//div[contains(.//dt//text(), 'Floor')]/dd//text()").extract())
        images = response.xpath(".//ul[@id='images']//img/@src").extract()
        description = ''.join(response.xpath(".//div[@id='description']//text()").extract())
        landlord_phone = '+32 2 731 07 07'
        landlord_email = 'immo@home-consult.be'
        landlord_name = 'Home Consult'
        js_code = response.xpath(".//script[contains(.//text(), 'var lat')]//text()").extract_first()
        parsed_js = js2xml.parse(js_code)
        latitude = ''.join(parsed_js.xpath(".//var[@name='lat']//number/@value"))
        longitude = ''.join(parsed_js.xpath(".//var[@name='lng']//number/@value"))

        item = ListingItem()
        item['external_source'] = "HomeConsult_PySpider_belgium_fr"
        item['external_link'] = external_link
        item['title'] = remove_white_spaces(title)
        item['address'] = remove_white_spaces(address)
        item['zipcode'] = zipcode
        item['city'] = city

        if room_count:
            item['room_count'] = room_count
        if square_meters:
            item['square_meters'] = extract_number_only(remove_unicode_char(square_meters))
        if rent:
            item['rent'] = extract_number_only(remove_unicode_char(''.join(rent.split('.'))))
            item['currency'] = currency_parser(rent)
        if available_date and available_date=='Immediately':
            item['available_date'] = format_date(remove_white_spaces(available_date), '%d %B %Y')
        if elevator:
            if 'yes' in elevator.lower():
                item['elevator'] = True
            else:
                item['elevator'] = False
        if furnished:
            if 'yes' in furnished.lower():
                item['furnished'] = True
            else:
                item['furnished'] = False
        # if floor:
        #     item['floor'] = remove_white_spaces(floor)
        item['images'] = images
        item['description'] = remove_white_spaces(description)
        item['landlord_name'] = landlord_name
        item['landlord_email'] = landlord_email
        item['landlord_phone'] = landlord_phone
        item['position'] = self.position
        item['latitude'] = latitude
        item['longitude'] = longitude
        if 'house' in title.lower() or \
            'villa' in title.lower() or \
            'bungalow' in title.lower() or \
            'MAISON DE MAITRE' in title:
            item['property_type'] = 'house'
        else:
            item['property_type'] = 'apartment'
        if item.get('rent', None):
            item['rent'] = int(item['rent']) if item['rent'].isdigit() else None
        if item.get('room_count', None):
            item['room_count'] = int(item['room_count']) if item['room_count'].isdigit() else None
        if item.get('square_meters', None):
            item['square_meters'] = int(item['square_meters']) if item['square_meters'].isdigit() else None
        yield item