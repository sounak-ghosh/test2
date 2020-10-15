# -*- coding: utf-8 -*-
import scrapy
from ..helper import remove_unicode_char, remove_white_spaces, extract_number_only, currency_parser
from ..items import ListingItem


class ResidentievastgoedSpider(scrapy.Spider):
    name = 'residentievastgoed'
    allowed_domains = ['residentievastgoed.be']
    start_urls = ['http://residentievastgoed.be/']
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'

    def start_requests(self):
        start_urls = [
            {'url': 'https://www.residentievastgoed.be/te-huur?sorts=Dwelling&pagename=woningen', 'property_type': 'house'},
            {'url': 'https://www.residentievastgoed.be/te-huur?sorts=Flat&pagename=Appartementen', 'property_type': 'apartment'},
        ]
        for url in start_urls:
            yield scrapy.Request(url=url.get('url'),
                                 callback=self.parse,
                                 meta={'property_type': url.get('property_type')})

    def parse(self, response):
        listings = response.xpath(".//a[contains(@class, 'publication')]/@href").extract()
        for property_url in listings:
            yield scrapy.Request(
                url=response.urljoin(property_url),
                callback=self.get_details,
                meta={'property_type': response.meta.get('property_type')}
            )

    def get_details(self, response):
        external_link = response.url
        property_type = response.meta.get("property_type")
        images = response.xpath(".//div[@id='detail-camera']//a/@href").extract()
        rent = ''.join(response.xpath(".//a[contains(@class, 'price')]//text()").extract())
        external_id = ''.join(response.xpath(".//tr[contains(.//td//text(), 'Referentie')]//td[@class='kenmerk']//text()").extract())
        square_meters = ''.join(response.xpath(".//tr[contains(.//td//text(), 'Bewoonbare opp')]//td[@class='kenmerk']//text()").extract())
        room_count = ''.join(response.xpath(".//tr[contains(.//td//text(), 'Slaapkamers')]//td[@class='kenmerk']//text()").extract())
        description = ''.join(response.xpath(".//div[@id='detail-detail']//text()").extract())
        landlord_phone = ''.join(response.xpath(".//a[contains(@class, 'phone')]//text()").extract())
        landlord_email = 'info@residentievastgoed.be'
        landlord_name = 'Residentie Vastgoed'

        item = ListingItem()
        item['external_source'] = "Residentievastgoed_PySpider_belgium_fr"
        item['external_link'] = external_link
        item['images'] = images
        if rent:
            item['rent'] = extract_number_only(remove_unicode_char(rent))
            item['currency'] = currency_parser(rent)
        item['property_type'] = property_type
        item['external_id'] = external_id
        if room_count:
            item['room_count'] = room_count
        if square_meters:
            item['square_meters'] = extract_number_only(remove_unicode_char(square_meters))
        item['landlord_phone'] = remove_white_spaces(landlord_phone)
        item['landlord_email'] = landlord_email
        item['landlord_name'] = landlord_name
        item['description'] = remove_white_spaces(description)
        if item.get('rent', None):
            item['rent'] = int(item['rent']) if item['rent'].isdigit() else None
        if item.get('room_count', None):
            item['room_count'] = int(item['room_count']) if item['room_count'].isdigit() else None
        if item.get('square_meters', None):
            item['square_meters'] = int(item['square_meters']) if item['square_meters'].isdigit() else None
        yield item
