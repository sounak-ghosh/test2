# -*- coding: utf-8 -*-
# Author: Mitesh Pandav/Sounak Ghosh
import scrapy
import js2xml
from ..items import ListingItem
from ..helper import remove_white_spaces, remove_unicode_char, extract_number_only,\
    currency_parser, property_type_lookup,format_date


def extract_city_zipcode(_address):
    _address = remove_unicode_char(_address)
    zip_city = _address.split(", ")[1]
    zipcode = zip_city.split(" ")[0]
    city = ' '.join(zip_city.split(" ")[1:])
    return zipcode, city


class ImmonoordSpider(scrapy.Spider):
    name = 'Immonoord_PySpider_belgium_fr'
    allowed_domains = ['immonoord.be']
    start_urls = ['https://www.immonoord.be/te-huur?type%5B0%5D=47001&type%5B1%5D=47005']
    position = 0
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'

    def parse(self, response):
        listing = response.xpath(".//a[@class='property-item__link']/@href")
        for property_item in listing:
            property_url = property_item.extract()
            yield scrapy.Request(url=property_url, callback=self.get_details)

        next_page_url = response.xpath(".//a[@rel='next']/@href").extract_first()
        if next_page_url:
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse
            )

    def get_details(self, response):
        self.position += 1
        external_link = response.url
        images = response.xpath(".//div[@id='property-gallery-desktop']//a/@href").extract()
        title = ''.join(response.xpath(".//h1[@class='property__title long']/text()").extract())
        rent = ''.join(response.xpath(".//div[@class='property__price']//text()").extract())
        address = ''.join(response.xpath(".//div[@class='property__location']//text()").extract())
        room_count = ''.join(response.xpath(".//i[contains(@class, 'icon-bed')]/following-sibling::span[1]//text()").extract())
        square_meters = ''.join(response.xpath(".//i[contains(@class, 'icon-house')]/following-sibling::span[1]//text()").extract())
        property_type = ''.join(response.xpath(".//dd[@class='type']//text()").extract())
        description = ''.join(response.xpath(".//div[@id='beschrijving']//text()").extract())
        floor = ''.join(response.xpath(".//dd[@class='floors.number_of_floors']//text()").extract())
        js_code = response.xpath("//script[contains(., 'mapData')]/text()").extract_first()
        parsed_js = js2xml.parse(js_code)
        # print(js2xml.pretty_print(parsed_js))
        latitude = parsed_js.xpath(".//property[@name='lat']//number/@value")[0]
        longitude = parsed_js.xpath(".//property[@name='long']//number/@value")[0]
        zipcode, city = extract_city_zipcode(address)
        landlord_name = 'ERA - Immo Noord'
        landlord_email = 'hoogstraten@immonoord.be'
        landlord_phone = '03 314 81 91'

        item = ListingItem()
        item['external_source'] = "Immonoord_PySpider_belgium_fr"
        item['external_link'] = external_link
        item['images'] = images
        item['title'] = title
        if 'Terras' in response.body.decode('utf-8'):
            item['terrace'] = True
        if 'Parkeerplaats' in response.body.decode('utf-8'):
            item['parking'] = True    
        availability = ''.join(response.xpath("//dd[@class='availability.available_from']/text()").extract())
        if availability:
            item['available_date'] = format_date(availability)
        utilities = ''.join(response.xpath("//dd[@class='rental_charges']/text()").extract())
        if utilities:
            item['utilities'] = int(utilities.replace('EUR','').strip())  
        if rent:
            item['rent'] = ''.join(remove_unicode_char(rent).split(' '))
            item['currency'] = currency_parser(rent)
        item['address'] = remove_white_spaces(address)
        if room_count:
            item['room_count'] = room_count
        if square_meters:
            item['square_meters'] = extract_number_only(remove_unicode_char(square_meters))
        item['property_type'] = property_type_lookup.get(property_type)
        item['description'] = remove_white_spaces(description)
        item['latitude'] = latitude
        item['longitude'] = longitude
        item['position'] = self.position
        if floor:
            item['floor'] = floor
        item['zipcode'] = zipcode
        item['city'] = city
        item['landlord_name'] = landlord_name
        item['landlord_email'] = landlord_email
        item['landlord_phone'] = landlord_phone
        if item.get('rent', None):
            item['rent'] = int(item['rent']) if item['rent'].isdigit() else None
        if item.get('room_count', None):
            item['room_count'] = int(item['room_count']) if item['room_count'].isdigit() else None
        if item.get('square_meters', None):
            item['square_meters'] = int(item['square_meters']) if item['square_meters'].isdigit() else None
        yield item
