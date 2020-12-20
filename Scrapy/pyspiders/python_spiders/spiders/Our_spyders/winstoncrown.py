# -*- coding: utf-8 -*-
# Author: Sounak Ghosh
import scrapy
from ..items import ListingItem
from ..helper import currency_parser, extract_number_only, remove_white_spaces, remove_unicode_char
import json
# import geopy
# from geopy.geocoders import Nominatim
# geolocator = Nominatim(user_agent="myGeocoder")

# def getAddress(lat,lng):
#     coordinates = str(lat)+","+str(lng)
#     location = geolocator.reverse(coordinates)
#     return location.address

class HenroimmoSpider(scrapy.Spider):
    name = 'winstoncrown_com_PySpider_unitedkingdom_en'
    allowed_domains = ['winstoncrowns.com']
    start_urls = ['https://www.winstoncrowns.com/']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_urls = [
            {'url': 'https://www.winstoncrowns.com/lettings/?filter-rental-type=&filter-type=&filter-location=&filter-price-rent-min=&filter-price-rent-max=&filter-price-buy-min=&filter-price-buy-max=&filter-bedrooms='}
        ]
        for url in start_urls:
            yield scrapy.Request(url=url.get('url'),callback=self.parse)

    def parse(self, response, **kwargs):
        listings = response.xpath("//article[contains(@class,'property-tile')]/a/@href").extract()
        listings = list(dict.fromkeys(listings))
        for property_item in listings:
            # property_item = 'https://www.2a-immo.fr'+property_item
            print("---------------->",property_item)
            yield scrapy.Request(
                url=property_item,
                callback=self.get_details
            )

    def get_details(self, response):
        item = ListingItem()
        item['external_source'] = "winstoncrown_com_PySpider_unitedkingdom_en"
        item['external_link'] = response.url
        item['title'] = response.xpath("//h1[@class='property-name']/text()").extract_first().strip()
        if 'Apartment' in item['title']:
            item['property_type'] = 'apartment'
        else:
            item['property_type'] = 'house'    
        item['images'] = response.xpath("//div[@class='carousel-inner']//img/@src").extract()
        item['landlord_name'] = 'winstoncrowns.com'
        item['landlord_phone'] = '+44 (0) 20 7493 3888'
        item['landlord_email'] = 'info@winstoncrowns.com'
        item['rent'] = int(response.xpath("//h4[@class='property-price']//span[@class='number']/text()").extract()[0].replace(',','')) * 4
        
        
        item['currency'] = 'GBP'
        item['room_count'] = int(response.xpath("//div[@class='col-xs-3 col-md-2']/span/span/text()").extract_first())
        description = response.xpath("//section[@id='description']//text()").extract()
        description = "".join([x for x in description if x.strip()])
        item['description'] = remove_white_spaces(description)
        features = response.xpath("//span[@class='property-feature']/text()").extract()
        for f in features:
            if 'lift' in f.lower():
                item['elevator'] = True
            if 'parking' in f.lower():
                item['parking'] = True
            if 'terrace' in f.lower():
                item['terrace'] = True 
            if 'balcony' in f.lower():
                item['balcony'] = True 
        item['floor_plan_images'] =   response.xpath("//a[contains(text(),'Floor Plan')]/@href").extract()[0]
        item['bathroom_count'] =   int(response.xpath("//div[@class='col-xs-3 col-md-2']/span/span/text()").extract()[1])
    #     sq_met =  response.xpath("//label[contains(text(),'Surface habitable')]/following-sibling::text()").extract()[0]
    #     item['square_meters'] = extract_number_only(remove_unicode_char(sq_met))
    #     item['deposit'] = response.xpath("//label[contains(text(),'Dépôt de garantie')]/following-sibling::text()").extract_first()
    #     if item['deposit']:
    #         item['deposit'] = item['deposit'].replace("€","")
    #     charges = response.xpath("//label[contains(text(),'Charges')]/following-sibling::text()").extract()[0]
    #     item['utilities'] = extract_number_only(remove_unicode_char(charges))
    #     item['external_id'] = response.xpath("//label[contains(text(),'Référence')]/following-sibling::text()").extract_first().strip()
    #     geo = response.xpath('//script[contains(text(),"ajaxPageState")]/text()').extract()[0].split("jQuery.extend(Drupal.settings,")[1].split(");")[0]
    #     j_data = json.loads(geo)
    #     item['latitude'] = j_data['acreat']['leaflet']['defaults']['map']['center']['lat']
    #     item['longitude'] = j_data['acreat']['leaflet']['defaults']['map']['center']['lng']
       
    #     item['address'] = getAddress(item['latitude'],item['longitude'])
    #     item['city'] = item['address'].split(",")[-1]
    #     item['zipcode'] = item['address'].split(",")[-2]
  
        yield item
