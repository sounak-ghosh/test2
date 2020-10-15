# -*- coding: utf-8 -*-
import scrapy
from ..helper import remove_unicode_char, remove_white_spaces, extract_number_only, currency_parser, format_date
from ..items import ListingItem


def extract_city_zipcode(_address):
    _address = remove_unicode_char(_address)
    if len(_address.split(", ")) > 1:
        zip_city_extra = _address.split(", ")[1]
        zip_city = zip_city_extra.split(" - ")[1]
        zipcode = zip_city.split(" ")[0]
        city = ' '.join(zip_city.split(" ")[1:])
        return zipcode, city
    return None, None



class GitSpider(scrapy.Spider):
    """ git """
    name = "git"
    allowed_domains = ["git.be"]
    start_urls = (
        'http://www.git.be/',
    )
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'
    position = 0

    def start_requests(self):
        start_urls = [
            {'url': 'https://www.git.be/Rechercher/Appartement%20Locations%20/Locations/\
                Type-01%7CAppartement/Localisation-/Prix-/Tri-PRIX%20DESC,COMM%20ASC,CODE',\
                     'property_type': 'apartment'},
            {'url': 'https://www.git.be/Rechercher/Maison%20Locations%20/Locations/\
                Type-02%7CMaison/Localisation-/Prix-/Tri-PRIX%20DESC,COMM%20ASC,CODE',\
                     'property_type': 'house'},
        ]
        for url in start_urls:
            yield scrapy.Request(url=url.get('url'),
                                 callback=self.parse,
                                 meta={'property_type': url.get('property_type')})

    def parse(self, response):
        listing = response.xpath(".//div[contains(@class, 'list-item')]")
        for list_item in listing:
            url = list_item.xpath(".//a/@href").extract_first()
            if 'javascript:;/Lang-FR' not in url:
                yield scrapy.Request(
                    url=response.urljoin(url),
                    callback=self.get_details,
                    meta={'property_type': response.meta.get('property_type')}
                )
        next_page = response.xpath(".//li[a//text() = '»' and \
            not(contains(@class, 'disabled'))]/a/@href").extract_first()
        if next_page:
            yield scrapy.Request(
                url=next_page,
                callback=self.parse,
                meta={'property_type': response.meta.get('property_type')}
            )

    def get_details(self, response):
        self.position += 1
        address = ''.join(response.xpath(".//p[@class='lead']//text()").extract())
        title = ''.join(response.xpath(".//h1[@class='liste-title']//text()").extract())
        external_link = response.url
        external_id = ''.join(response.xpath(".//div[@class='ref-tag']//b/text()").extract())
        images = response.xpath(".//div[@id='carousel']//a/@href").extract()
        description = ''.join(response.xpath(".//div[@id='documentsModal']\
            /following-sibling::div[1]/div[@class='col-md-6'][2]//text()").extract())
        room_count = ''.join(response.xpath(".//tr[contains(./td/text(), \
            'Chambres')]/td[2]//text()").extract())

        floor = ''.join(response.xpath('''.//tr[contains(./td/text(), "Nombre d'étages")]\
            /td[2]//text()''').extract())
        available_date = ''.join(response.xpath('''.//tr[contains(./td/text(), "Disponibilitï")]\
            /td[2]//text()''').extract())
        square_meters = ''.join(response.xpath(".//tr[contains(./td/text(),\
             'Surface habitable nette')]/td[2]//text()").extract())
        parking = ''.join(response.xpath(".//tr[contains(./td/text(),\
             'Emplacements parking')]/td[2]//text()").extract())
        rent = ''.join(response.xpath(".//tr[contains(./td/text(),\
             'Prix')]/td[2]//text()").extract())
        furniture = ''.join(response.xpath(".//tr[contains(./td/text(),\
             'Meublé')]/td[2]//text()").extract())
        terrace = ''.join(response.xpath(".//tr[contains(./td/text(),\
             'Terrasse')]/td[2]//text()").extract())
        property_type = response.meta.get('property_type')
        zipcode, city = extract_city_zipcode(address)
        item = ListingItem()
        item['external_source'] = "Git_PySpider_belgium_fr"
        item['address'] = remove_white_spaces(address)
        item['title'] = remove_white_spaces(title.lstrip('-'))
        item['external_link'] = external_link
        item['external_id'] = external_id
        item['images'] = images
        item['description'] = remove_white_spaces(description)
        item['room_count'] = extract_number_only(room_count)
        item['square_meters'] = extract_number_only(remove_unicode_char(square_meters))
        if parking:
            item['parking'] = True
        if rent:
            item['rent'] = remove_unicode_char(''.join(rent.split('.')))
            item['currency'] = currency_parser(rent)
        if furniture :
            if 'non' in furniture.lower():
                item['furnished'] = False
            else:
                item['furnished'] = True
        if terrace :
            if 'non' in terrace.lower():
                item['terrace'] = False
            else:
                item['terrace'] = True
        if floor:
            item['floor'] = floor
        item['property_type'] = property_type
        item['position'] = self.position
        item['zipcode'] = zipcode
        item['city'] = city
        item['landlord_name'] = 'GIT'
        item['landlord_email'] = 'agence@git.be'
        item['landlord_phone'] = '069/23.40.02'
        if available_date:
            item['available_date'] = format_date(available_date, '%d/%m/%Y')
        if item.get('rent', None):
            item['rent'] = int(item['rent']) if item['rent'].isdigit() else None
        if item.get('room_count', None):
            item['room_count'] = int(item['room_count']) if item['room_count'].isdigit() else None
        if item.get('square_meters', None):
            item['square_meters'] = int(item['square_meters']) if item['square_meters'].isdigit() else None
        if address:
            yield item
