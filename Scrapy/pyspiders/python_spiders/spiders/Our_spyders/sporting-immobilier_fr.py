# -*- coding: utf-8 -*-
# Author: Sounak Ghosh
import scrapy,re
from ..items import ListingItem
from ..helper import currency_parser, extract_number_only, remove_white_spaces, remove_unicode_char
# from geopy.geocoders import Nominatim
# geolocator = Nominatim(user_agent="myGeocoder")


def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 3:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 2:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)

# def getAddress(lat,lng):
#     coordinates = str(lat)+","+str(lng)
#     location = geolocator.reverse(coordinates)
#     return location.address

class HenroimmoSpider(scrapy.Spider):
    name = 'sporting-immobilier_fr_PySpider_france_fr'
    allowed_domains = ['sporting-immobilier.fr']
    start_urls = ['https://www.sporting-immobilier.fr/']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        start_urls = [
            {'url': 'https://www.sporting-immobilier.fr/toulouse/page/{}/?type_mandat=location&c-search=1&s&type_bien%5B0%5D=villa&type_bien%5B1%5D=appartement&lot_prix'}
        ]
        for url in start_urls:
            for i in range(1,6):
                yield scrapy.Request(url=url.get('url').format(i),
                                    callback=self.parse)

    def parse(self, response, **kwargs):
        listings = response.xpath("//div[@class='grid-lots-item']//div[@class='lot-thumbnail']/a/@href").extract()
        for property_item in listings:
            print("---------------->",property_item)
            yield scrapy.Request(
                url=property_item,
                callback=self.get_details
            )

    def get_details(self, response):
        item = ListingItem()
        item['external_source'] = "sporting-immobilier_fr_PySpider_france_fr"
        item['external_link'] = response.url
        property_tp = response.xpath("//h1[@class='entry-title']/text()").extract_first()
        if 'Appartement' in property_tp:
            item['property_type'] = 'apartment'
        else:
            item['property_type'] = 'house'    
        item['title'] = response.xpath("//h1[@class='entry-title']/text()").extract_first().strip()
        item['images'] = response.xpath("//div[@id='lot-gallery']//img/@src").extract()
        item['landlord_name'] = 'Sporting Immobilier'
        item['landlord_phone'] = response.xpath("//p[@class='tel']/a/@href").extract_first().replace("tel:","")
        print (response.xpath("//h1[@class='entry-title']/span/text()").extract()[-1])
        item['rent'] = getSqureMtr(response.xpath("//h1[@class='entry-title']/span/text()").extract()[-1].split("–")[1])
        
        ad_text = response.xpath("//h1[@class='entry-title']/span[contains(text(),'(')]/text()").extract()
        if ad_text:
            item['address'] = ad_text[0]
            item['city'] = ad_text[0].split("(")[0].strip()
            item['zipcode']= ad_text[0].split("(")[-1].replace(")","")
        
        item['currency'] = 'EUR'
        if getSqureMtr(response.xpath("//h1[@class='entry-title']/text()").extract_first()):
            item['room_count'] = getSqureMtr(response.xpath("//h1[@class='entry-title']/text()").extract_first())#.split(" ")[-2]
        description = ''.join(response.xpath("//div[@class='bloc-content']//p//text()").extract())
        item['description'] = remove_white_spaces(description)
        if 'parking' in description or 'Parking' in description:
            item['parking'] = True
        if 'terrace' in description or 'Terrasse' in description or 'terrasse' in description:
            item['terrace'] = True      
        sq_met =  response.xpath("//h1[@class='entry-title']//span/text()").extract()[-1].split("–")[0] 
        if getSqureMtr(extract_number_only(remove_unicode_char(sq_met))):
            item['square_meters'] = getSqureMtr(extract_number_only(remove_unicode_char(sq_met)))
        deposit = response.xpath("//dt[contains(text(),'Dépôt de garantie')]/following-sibling::dd[1]//text()").extract_first()
        if deposit and getSqureMtr(deposit):
            item['deposit'] = getSqureMtr(deposit)#.replace("€","")
        bathroom_count = response.xpath("//dt[contains(text(),'Salle de bains')]/following-sibling::dd[1]//text()").extract_first()
        if bathroom_count and getSqureMtr(bathroom_count):
            item['bathroom_count'] = getSqureMtr(bathroom_count)
        charges = response.xpath("//small[contains(text(),'charges')]/text()").extract()[0]
        if getSqureMtr(extract_number_only(remove_unicode_char(charges))):
            item['utilities'] = getSqureMtr(extract_number_only(remove_unicode_char(charges)))
        item['external_id'] = response.xpath("//p[contains(text(),'Référence')]").extract_first().split(":")[1].replace("</p>","").strip()
        geo = response.xpath("//script[contains(text(),'lotMap')]/text()").extract()[0]
        item['latitude'] = geo.split("},")[0].split(":")[2].replace(", lng","").strip()
        item['longitude'] = geo.split("},")[0].split(":")[3].strip()
        # item['address'] = getAddress(item['latitude'],item['longitude'])
        # item['city'] = item['address'].split(",")[-1].strip()
        # item['zipcode'] = item['address'].split(",")[-2].strip()
        print (item)
        yield item
