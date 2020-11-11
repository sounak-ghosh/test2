# -*- coding: utf-8 -*-
import scrapy
from ..items import ListingItem
from ..helper import currency_parser, extract_number_only, remove_white_spaces, remove_unicode_char
import geopy
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="myGeocoder")
import json,re

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 3:
        output = float(list_text[0]+list_text[1])
    elif len(list_text) == 2:
        output = float(list_text[0]+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)


def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = geolocator.reverse(coordinates)
    return location.address

class HenroimmoSpider(scrapy.Spider):
    name = '2a-immo.fr_PySpider_france_fr'
    allowed_domains = ['2a-immo.fr']
    start_urls = ['https://www.2a-immo.fr/']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [
            {'url': 'https://www.2a-immo.fr/location/appartement--maison?page={}'}
        ]
        for url in start_urls:
            for i in range(0,12):
                yield scrapy.Request(url=url.get('url').format(i),
                                    callback=self.parse)

    def parse(self, response, **kwargs):
        listings = response.xpath("//article[contains(@id,'node-')]//h2/a/@href").extract()
        for property_item in listings:
            property_item = 'https://www.2a-immo.fr'+property_item
            print("---------------->",property_item)
            yield scrapy.Request(
                url=property_item,
                callback=self.get_details
            )

    def get_details(self, response):
        item = ListingItem()
        item['external_source'] = "2a-immo.fr_PySpider_france_fr"
        item['external_link'] = response.url
        property_tp = response.xpath("//div[@class='container']//h1/text()").extract_first()
        if 'Appartement' in property_tp:
            item['property_type'] = 'apartment'
        else:
            item['property_type'] = 'house'    
        item['title'] = response.xpath("//div[@class='container']//h1/text()").extract_first().strip()
        item['images'] = response.xpath("//div[@class='main-slider']//img[contains(@class,'photo-')]/@src").extract()
        item['landlord_name'] = '2a-immo.fr'
        item['landlord_phone'] = response.xpath("//p[@class='telephone']//text()").extract_first().strip()
        item['landlord_email'] = '2a-immo@2a-immo.fr'
        item['rent'] = getSqureMtr(response.xpath("//div[@class='price']//text()").extract()[0])#.split("€")[0]
        
        
        item['currency'] = 'EURO'
        if getSqureMtr(response.xpath("//label[contains(text(),'Nombre de pièces')]/following-sibling::text()").extract_first()):
            item['room_count'] = getSqureMtr(response.xpath("//label[contains(text(),'Nombre de pièces')]/following-sibling::text()").extract_first())
        description = ''.join(response.xpath("//div[@class='content rendered-content']/p/text()").extract())
        item['description'] = remove_white_spaces(description)
        if 'parking' in description:
            item['parking'] = True
        sq_met =  response.xpath("//label[contains(text(),'Surface habitable')]/following-sibling::text()").extract()[0]
        if getSqureMtr(extract_number_only(remove_unicode_char(sq_met))):
            item['square_meters'] = getSqureMtr(extract_number_only(remove_unicode_char(sq_met)))
        deposit = response.xpath("//label[contains(text(),'Dépôt de garantie')]/following-sibling::text()").extract_first()
        if getSqureMtr(deposit):
            item['deposit'] = getSqureMtr(deposit)#.replace("€","")
        charges = response.xpath("//label[contains(text(),'Charges')]/following-sibling::text()").extract()[0]
        if getSqureMtr(extract_number_only(remove_unicode_char(charges))):
            item['utilities'] = getSqureMtr(extract_number_only(remove_unicode_char(charges)))
        item['external_id'] = response.xpath("//label[contains(text(),'Référence')]/following-sibling::text()").extract_first().strip()
        geo = response.xpath('//script[contains(text(),"ajaxPageState")]/text()').extract()[0].split("jQuery.extend(Drupal.settings,")[1].split(");")[0]
        j_data = json.loads(geo)
        item['latitude'] = j_data['acreat']['leaflet']['defaults']['map']['center']['lat']
        item['longitude'] = j_data['acreat']['leaflet']['defaults']['map']['center']['lng']
       
        item['address'] = getAddress(item['latitude'],item['longitude'])
        item['city'] = item['address'].split(",")[-1].strip()
        item['zipcode'] = item['address'].split(",")[-2].strip()
        
        print (item)
        yield item
