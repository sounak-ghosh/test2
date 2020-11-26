# -*- coding: utf-8 -*-
import scrapy
from ..items import ListingItem
from ..helper import currency_parser, extract_number_only, remove_white_spaces, remove_unicode_char
import geopy
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="myGeocoder")
import json
import sys

def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = geolocator.reverse(coordinates)
    return location.address

class HenroimmoSpider(scrapy.Spider):
    name = 'eson2_co_uk_PySpider_unitedkingdom_en'
    allowed_domains = ['eson2.co.uk']
    start_urls = ['https://eson2.co.uk/']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'

    def start_requests(self):
        start_urls = [
            {'url': 'https://eson2.co.uk/properties/page/{}/'}
        ]
        for url in start_urls:
            for i in range(1,7):
                yield scrapy.Request(url=url.get('url').format(i),callback=self.parse)

    def parse(self, response, **kwargs):
        listings = response.xpath("//h2[@class='posttitle']/a/@href").extract()
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
        item['external_source'] = "eson2_co_uk_PySpider_unitedkingdom_en"
        item['external_link'] = response.url
        item['title'] = response.xpath("//h1[@class='prop-title']/text()").extract_first().strip()
   
        item['images'] = response.xpath("//li[contains(@style,'background-image')]/a/@href").extract()
        item['images'] = list(dict.fromkeys(item['images']))
        item['external_id'] = response.xpath("//p[@class='prop-id']/text()").extract()[0].split(":")[1].strip()
        item['landlord_name'] = 'eson2.co.uk'
        item['landlord_phone'] = '+44 (0) 2039 417 034'
        item['landlord_email'] = 'info@eson2.co.uk'
        item['rent'] = int(response.xpath("//span[@class='property-price']/text()").extract()[0].replace('from £','').replace('p/w','').replace(',','').strip()) * 4
        
        
        item['currency'] = 'GBP'
        try:
            sq_met =  response.xpath("//span[@class='property-size']/text()").extract()[0]
            item['square_meters'] = int(extract_number_only(remove_unicode_char(sq_met)))
        except:
            pass    
        item['room_count'] = int(response.xpath("//p[contains(text(),'Bedroom')]/text()").extract_first().replace('Bedrooms','').replace('Bedroom','').strip())
        try:
            item['bathroom_count'] =   int(response.xpath("//p[contains(text(),'Bathroom')]/text()").extract_first().replace('Bathrooms','').replace('Bathroom','').strip())
        except:
            pass
        description = response.xpath("//div[@class='prop-single-content']//text()").extract()
        description = "".join([x for x in description if x.strip()])
        item['description'] = remove_white_spaces(description)
        if 'apartment' in item['description']:
            item['property_type'] = 'apartment'
        else:
            item['property_type'] = 'house' 
        try:    
            elevator = response.xpath("//span[text()='Elevator: ']/following-sibling::text()").extract()[0]
            if 'Yes' in elevator:
                item['elevator'] = True
        except:
            pass
        try:              
            balcony = response.xpath("//span[text()='More info: ']/following-sibling::text()").extract()[0] 
            if 'balcony' in elevator.lower():
                item['balcony'] = True 
        except:
            pass           

        geo = response.xpath("//script[contains(text(),'gmaps_latitude')]/text()").extract()[0].split("var gmaps_var = ")[1].replace(';','')
       
        json_geo = json.loads(geo)
        item['latitude'] = json_geo['gmaps_latitude']
        item['longitude'] = json_geo['gmaps_longitude']
        
        item['address'] = getAddress(item['latitude'],item['longitude'])
        print(item['address'])
        item['city'] = item['address'].split(",")[-4]
        item['zipcode'] = item['address'].split(",")[-2]
  
        yield item
