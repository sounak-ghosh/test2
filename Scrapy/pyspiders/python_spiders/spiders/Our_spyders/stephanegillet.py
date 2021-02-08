# -*- coding: utf-8 -*-
# Author: Mitesh Pandav/Sounak Ghosh
import scrapy
from ..items import ListingItem
from ..helper import currency_parser, extract_number_only, remove_unicode_char, remove_white_spaces

class StephanegilletSpider(scrapy.Spider):
    name = 'Stephanegillet_PySpider_belgium_fr'
    allowed_domains = ['stephanegillet.be']
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'
    def start_requests(self):
        start_urls = [
            {'url': 'https://www.stephanegillet.be/destination/appartementlocation/',
             'property_type': 'apartment'},
            {'url': 'https://www.stephanegillet.be/destination/maisonslocation/',
             'property_type': 'house'}
        ]
        for url in start_urls:
            yield scrapy.Request(url=url.get('url'),
                                 callback=self.parse,
                                 meta={'property_type': url.get('property_type')})

    def parse(self, response):
        listings = response.xpath(".//a[@class='read-more']/@href").extract()
        for property_item in listings:
            yield scrapy.Request(
                url=property_item,
                callback=self.get_details,
                meta={'property_type': response.meta.get('property_type')}
            )

    def get_details(self, response):
        item = ListingItem()
        item['external_source'] = "Stephanegillet_PySpider_belgium_fr"
        item['external_link'] = response.url
        title = remove_unicode_char(''.join(response.xpath(".//h1[@class='titrebien']//text()").extract()))
        item['title'] = title
        rent = ''.join(response.xpath(".//div[contains(@class, 'et_pb_column_5')]//text()").extract())
        if rent:
            item['rent'] = extract_number_only(remove_unicode_char(''.join(rent.split('.'))))
            item['currency'] = currency_parser(rent)
        room_count = extract_number_only(''.join(response.xpath(".//img[contains(@src, 'chambre.png')]/following-sibling::span[1]//text()").extract()))
        if room_count:
            item['room_count'] = room_count
        item['latitude'] = ''.join(response.xpath(".//div[@class='et_pb_map_pin']/@data-lat").extract())
        item['longitude'] = ''.join(response.xpath(".//div[@class='et_pb_map_pin']/@data-lng").extract())

        city_zip = title.split(" - ")[-1]
        city = city_zip.split(" ")[0]
        zipcode = extract_number_only(city_zip.split(" ")[-1])
        item['city'] = city
        item['zipcode'] = zipcode
        description = ''.join(response.xpath(".//div[contains(@class, 'et_pb_column_14')]//text()").extract())
        item['description'] = remove_white_spaces(description)
        item['images'] = response.xpath(".//div[contains(@class, 'et_pb_gallery_image')]//img/@src").extract()
        item['property_type'] = response.meta.get('property_type')
        energy_label = ''.join(response.xpath(".//div[contains(.//h3//text(), 'Bilan PEB')]//li[2]//text()").extract())
        item['energy_label'] = energy_label
        item['address'] = ''.join(response.xpath("//h1[@class='titrebien']/text()").extract()).split('-')[-1].strip()
        bathroom_count = ''.join(response.xpath("//li[contains(text(),'Salles de bain')]/text()").extract()).split(':')[-1]
        item['landlord_name'] = 'Agence d’Havelange'
        item['landlord_phone'] = '083/21 83 33'
        item['landlord_email'] = 'stephane.gillet@stephanegillet.be'

        if 'Parkings' in response.body.decode('utf-8') or 'Garages' in response.body.decode('utf-8'):
            item['parking'] = True
        if 'Terrasse' in  response.body.decode('utf-8'):
            item['terrace'] = True
        if bathroom_count:
            item['bathroom_count'] = int(bathroom_count)
        if item.get('rent', None):
            item['rent'] = int(item['rent']) if item['rent'].isdigit() else None
        if item.get('room_count', None):
            item['room_count'] = int(item['room_count']) if item['room_count'].isdigit() else None
        if item.get('square_meters', None):
            item['square_meters'] = int(item['square_meters']) if item['square_meters'].isdigit() else None
        yield item
