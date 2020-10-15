# -*- coding: utf-8 -*-
import scrapy
import js2xml
from ..helper import remove_white_spaces, remove_unicode_char, currency_parser, extract_number_only
from ..items import ListingItem


def extract_city_zipcode(_address):
    _address = remove_unicode_char(_address)
    zip_city = _address.split(", ")[1]
    zipcode = zip_city.split(" ")[0]
    city = ' '.join(zip_city.split(" ")[1:])
    return zipcode, city


class VastgoeddevosSpider(scrapy.Spider):
    name = 'vastgoeddevos'
    allowed_domains = ['vastgoeddevos.be']
    start_urls = []
    position = 0
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'

    def start_requests(self):
        start_urls = [
            {'url': 'http://www.vastgoeddevos.be/te-huur?category=12&priceRange=&office=1&status=te+huur',
             'property_type': 'apartment'},
            {'url': 'http://www.vastgoeddevos.be/te-huur?category=12&priceRange=&office=2&status=te+huur',
             'property_type': 'apartment'},
            {'url': 'http://www.vastgoeddevos.be/te-huur?category=3&priceRange=&office=1&status=te+huur',
             'property_type': 'house'},
            {'url': 'http://www.vastgoeddevos.be/te-huur?category=3&priceRange=&office=2&status=te+huur',
             'property_type': 'house'},
        ]
        for url in start_urls:
            yield scrapy.Request(url=url.get('url'),
                                 callback=self.parse,
                                 meta={'property_type': url.get('property_type')})

    def parse(self, response):
        listings = response.xpath(".//a[contains(@class, 'estate-picture')]/@href").extract()
        for property_url in listings:
            yield scrapy.Request(
                url=response.urljoin(property_url),
                callback=self.get_details,
                meta={'property_type': response.meta.get('property_type')}
            )

    def get_details(self, response):
        self.position += 1
        external_link = response.url
        images = response.xpath(".//div[@class='detail-slider']/a/@href").extract()
        rent = ''.join(response.xpath(".//div[@class='price']//text()").extract())
        address = ''.join(response.xpath(".//div[@class='address']//text()").extract())
        room_count = ''.join(response.xpath(".//img[contains(@alt, 'slaapkamers')]\
            /following-sibling::p[2]//text()").extract())
        square_meters = ''.join(response.xpath(".//img[contains(@alt, 'woonoppervlakte')]\
            /following-sibling::p[2]//text()").extract())
        description = ''.join(response.xpath(".//h2[contains(.//text(), 'Omschrijving')]\
            /following-sibling::p[1]//text()").extract())
        js_code = response.xpath(".//script[contains(.//text(), 'mapOptions')]//text()").extract_first()
        parsed_js = js2xml.parse(js_code)
        latitude = parsed_js.xpath(".//var[@name='mapOptions']//arguments//number[1]/@value")
        longitude = parsed_js.xpath(".//var[@name='mapOptions']//arguments//number[2]/@value")
        terrace = ''.join(response.xpath(".//div[contains(img/@alt, 'terras')]//strong//text()").extract())
        landlord_name = response.xpath(".//div[@class='detail-office'][1]//strong/text()").extract_first()
        landlord_phone = response.xpath(".//div[@class='detail-office']//a[contains(@href, 'tel:')]/text()").extract_first()
        landlord_email = response.xpath(".//div[@class='detail-office']//a[contains(@href, 'mailto:')]/text()").extract_first()
        zipcode, city = extract_city_zipcode(address)

        item = ListingItem()
        item['external_source'] = "Vastgoeddevos_PySpider_belgium_fr"
        item['external_link'] = external_link
        item['images'] = images
        if rent:
            item['rent'] = extract_number_only(remove_unicode_char(rent))
            item['currency'] = currency_parser(rent)
        item['address'] = remove_white_spaces(address)
        if room_count:
            item['room_count'] = room_count
        if square_meters:
            item['square_meters'] = extract_number_only(remove_unicode_char(square_meters))
        item['description'] = remove_white_spaces(description)
        if latitude:
            item['latitude'] = latitude[0]
        if longitude:
            item['longitude'] = longitude[0]
        if 'Ja' in terrace:
            item['terrace'] = True
        item['position'] = self.position
        item['property_type'] = response.meta.get('property_type')
        item['landlord_name'] = landlord_name
        item['landlord_phone'] = landlord_phone
        item['landlord_email'] = landlord_email
        item['zipcode'] = zipcode
        item['city'] = city
        if item.get('rent', None):
            item['rent'] = int(item['rent']) if item['rent'].isdigit() else None
        if item.get('room_count', None):
            item['room_count'] = int(item['room_count']) if item['room_count'].isdigit() else None
        if item.get('square_meters', None):
            item['square_meters'] = int(item['square_meters']) if item['square_meters'].isdigit() else None
        yield item
