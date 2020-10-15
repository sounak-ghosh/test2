# -*- coding: utf-8 -*-
import scrapy
from ..items import ListingItem
from ..helper import currency_parser, extract_number_only, remove_white_spaces, remove_unicode_char

class HenroimmoSpider(scrapy.Spider):
    name = 'henroimmo'
    allowed_domains = ['henro-immo.be']
    start_urls = ['http://henro-immo.be/']
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'

    def start_requests(self):
        start_urls = [
            {'url': 'https://www.henro-immo.be/Chercher-bien-accueil--L--resultat?statut=L&localiteS=&prixmaxS=&refS=&typeS=Appartement/Loft&chambreS=&facadeS=',
             'property_type': 'apartment'},
            {'url': 'https://www.henro-immo.be/Chercher-bien-accueil--L--resultat?statut=L&localiteS=&prixmaxS=&refS=&typeS=Maison&chambreS=&facadeS=',
             'property_type': 'house'},
            {'url': 'https://www.henro-immo.be/Chercher-bien-accueil--L--resultat?statut=L&localiteS=&prixmaxS=&refS=&typeS=Villa&chambreS=&facadeS=',
             'property_type': 'house'},
        ]
        for url in start_urls:
            yield scrapy.Request(url=url.get('url'),
                                 callback=self.parse,
                                 meta={'property_type': url.get('property_type')})

    def parse(self, response, **kwargs):
        listings = response.xpath(".//a[contains(.//h4/@class, 'title')]/@href").extract()
        for property_item in listings:
            yield scrapy.Request(
                url=response.urljoin(property_item),
                callback=self.get_details,
                meta={'property_type': response.meta.get('property_type')}
            )

    def get_details(self, response):
        external_link = response.url
        property_type = response.meta.get("property_type")
        title = ''.join(response.xpath(".//div[@class='container']//h1//text()").extract())
        images = response.xpath(".//a[@class='image-popup']/@href").extract()
        landlord_name = ''.join(response.xpath(".//div[@align='right']/text()").extract())
        landlord_phone = ''.join(response.xpath(".//div[@align='right']/div/text()").extract())
        rent = ''.join(response.xpath(".//div[@align='left']//text()").extract())
        room_count = ''.join(response.xpath(".//div[@class='service-item' and .//i/@class='flaticon-bed']//text()").extract())
        room_count = remove_white_spaces(room_count)
        garage = ''.join(response.xpath(".//div[@class='service-item' and .//i/@class='flaticon-garage']//text()").extract())
        square_meters = ''.join(response.xpath(".//div[@class='service-item' and .//i/@class='flaticon-resize']//text()").extract())
        description = ''.join(response.xpath(".//div[@class='sec-title']//text()").extract())

        item = ListingItem()
        item['external_source'] = "Henroimmo_PySpider_belgium_fr"
        item['external_link'] = external_link
        item['property_type'] = property_type
        item['title'] = title
        city = title.split(" à ")[-1]
        if city:
            item['city'] = city
        item['images'] = images
        item['landlord_name'] = remove_white_spaces(landlord_name)
        item['landlord_phone'] = landlord_phone
        if rent and 'price not communicated' not in rent.lower():
            item['rent'] = extract_number_only(remove_unicode_char(rent))
            item['currency'] = currency_parser(rent)
        if room_count:
            item['room_count'] = extract_number_only(room_count)
        if garage:
            item['parking'] = True
        if square_meters:
            item['square_meters'] = extract_number_only(remove_unicode_char(square_meters))
        item['description'] = remove_white_spaces(description)
        item['landlord_email'] = 'info@henro-immo.be'
        if item.get('rent', None):
            item['rent'] = int(item['rent']) if item['rent'].isdigit() else None
        if item.get('room_count', None):
            item['room_count'] = int(item['room_count']) if item['room_count'].isdigit() else None
        if item.get('square_meters', None):
            item['square_meters'] = int(item['square_meters']) if item['square_meters'].isdigit() else None

        print (item)
        yield item
