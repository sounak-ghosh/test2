# Author: Sounak Ghosh
import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re,json
from bs4 import BeautifulSoup
import requests,time
import sys
# from geopy.geocoders import Nominatim
# import timestring
# from word2number import w2n

# geolocator = Nominatim(user_agent="myGeocoder")

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

# def getAddress(lat,lng):
#     coordinates = str(lat)+","+str(lng)
#     location = geolocator.reverse(coordinates)
#     return location

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) > 1:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)

def getPrice(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) > 1:
        output = float(list_text[0]+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)


def cleanText(text):
    text = ''.join(text.split())
    text = re.sub(r'[^a-zA-Z0-9]', ' ', text).strip()
    return text.replace(" ","_").lower()


def num_there(s):
    return any(i.isdigit() for i in s)


def cleanKey(data):
    if isinstance(data,dict):
        dic = {}
        for k,v in data.items():
            dic[cleanText(k)]=cleanKey(v)
        return dic
    else:
        return data

def strToDate(text):
    if "/" in text:
        date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
    elif "-" in text:
        date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
    # else:
    #     date = str(timestring.Date(text)).replace("00:00:00","").strip()
    return date


class QuotesSpider(scrapy.Spider):
    name = 'ramestateagent_PySpider_united_kingdom_en'
    allowed_domains = ['www.ramestateagent.com']
    start_urls = ['www.ramestateagent.com']
    execution_type = 'testing'
    country = 'united_kingdom'
    locale ='en'


    def start_requests(self):
        url = "https://www.ramestateagent.com/search.vbhtml/properties-to-rent"
        yield scrapy.Request(
            url = url,
            callback=self.parse
            )

    def parse(self,response,**kwargs):
        soup = BeautifulSoup(response.body,"html.parser")
        pages = int(soup.find('ul',class_='pagination').find_all('li')[-2].text)

        for i in range(1,pages+1):
            di = {'salerent': 'nr',
                'area': '',
                'type': '',
                'minbeds': '',
                'minbaths': '',
                'minprice': '',
                'maxprice': '',
                'PropPerPage': '12',
                'order': 'high',
                'radius': '0',
                'grid': 'grid',
                'search': 'yes',
                'links': str(i)}


            yield scrapy.FormRequest(
                url = "https://www.ramestateagent.com/search.vbhtml/properties-to-rent",
                formdata = di,
                callback=self.get_page_details,
                )

    def get_page_details(self,response,**kwargs):
        soup = BeautifulSoup(response.body,"html.parser")

        for lo in soup.find_all('div',class_='col-xs-4 animation'):
            rec = {}
            city = lo.find('p').text.strip()

            external_link = 'https://www.ramestateagent.com/'+lo.find('a')['href']
            external_source = 'www.ramestateagent.com'
            address = lo.find('h3').text+' '+city

            property_type = lo.find('strong').text

           
                
             
            price_pw = getPrice(re.findall('\d+',lo.find('span',class_='label price').text.strip())[0])
            rent = price_pw*4
            # try:
            #     rec['room_count'] = int(clean_value(lo.find('i',class_='icon-bedroom').find_previous('li').text.strip()))
            # except:
            #     try:
            #         room = soup.find('p',class_='photos-pad').text.split('/')
            #         for r in room:
            #             if 'Bedroom' in r:
            #                 rec['room_count'] = r.split()[0].strip() 
            #     except:
            #         pass               

            # try:
            #     rec['bathroom_count'] = int(clean_value(lo.find('i',class_='icon-bathroom').find_previous('li').text.strip()))
            # except:
            #     try:
            #         bathroom = soup.find('p',class_='photos-pad').text.split('/')
            #         for br in bathroom:
            #             if 'Bathroom' in br:
            #                 rec['bathroom_count'] = br.split()[0].strip() 
            #     except:
            #         pass
            title = lo.find('h3').text
            rec['city'] = city
            rec['external_source'] = external_source
            rec['address'] = address
            rec['rent'] = rent
            rec['currency'] = 'GBP'
            rec['title'] = title
            
            


            if "tudiant" in property_type.lower() or  "studenten" in property_type.lower() and ("appartement" in property_type.lower() or "apartment" in property_type.lower()):
                property_type = "student_apartment"
            elif "appartement" in property_type.lower() or "apartment" in property_type.lower() or "flat" in property_type.lower() or "duplex" in property_type.lower()  or "building" in property_type.lower() :
                property_type = "apartment"
            elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower() or "house" in property_type.lower():
                property_type = "house"
            elif "chambre" in property_type.lower() or "kamer" in property_type.lower() or "room" in property_type.lower():
                property_type = "room"
            elif "studio" in property_type.lower():
                property_type = "studio"
            else:
                property_type = "NA"
                
            if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
                rec['property_type'] = property_type

                yield scrapy.Request(
                    url = external_link,
                    callback=self.get_property_details,
                    meta = rec
                    )
            

    def get_property_details(self, response, **kwargs):
        item = ListingItem()
        soup = BeautifulSoup(response.body,"html.parser")
        print (response.url)

        for key,val in response.meta.items():
            try:
                item[key] = val
            except:
                pass


        item["external_link"] = response.url

        imgs = set()
        for im in soup.find('div',class_="fotorama").find_all('img'):
            imgs.add('https://www.ramestateagent.com/'+im['src'])

        if imgs:
            item["images"] = list(imgs)
            item["external_images_count"] = len(imgs)

        desc = soup.find('p',class_='lead').text
        if "garage" in desc.lower() or "parking" in desc.lower() or "autostaanplaat" in desc.lower():
            item["parking"] = True
        if "terras" in desc.lower() or "terrace" in desc.lower():
            item["terrace"] = True
        if "balcon" in desc.lower() or "balcony" in desc.lower():
            item["balcony"] = True
        if "zwembad" in desc.lower() or "swimming" in desc.lower():
            item["swimming_pool"] = Tru
        if "machine à laver" in desc.lower() or"washing" in desc.lower():
            item["washing_machine"] = True
        if ("lave" in desc.lower() and "vaisselle" in desc.lower()) or "dishwasher" in desc.strip():
            item["dishwasher"] = True
        if "lift" in desc.lower() or "elevator" in desc.lower():
            item["elevator"] = True
        # print(">>>>>>>>>>>>>>>>>>>>>>>>>>",soup.find('p',class_='photos-pad').text.split('/'))
        try:
            bathroom = soup.find('p',class_='photos-pad').text.split('/')
            for br in bathroom:
                if 'Bathroom' in br:
                    item['bathroom_count'] = int(br.split()[0].strip())
        except:
            pass
        try:
            room = soup.find('p',class_='photos-pad').text.split('/')
            for r in room:
                if 'Bedroom' in r:
                    item['room_count'] = int(r.split()[0].strip())
        except:
            pass      
        # f=open('try.html','wb')
        # f.write(response.body)
        latlong=None
        for sc in response.xpath("//script[contains(text(),'LatLng')]/text()").extract():
            if 'LatLng(' in sc:
                latlong = re.findall('LatLng\((.*?)\)',sc)[0]
                break
        if latlong:
            lat,lng = latlong.split(',')
            item['latitude'] = lat
            item['longitude'] = lng
        # else:
        # try:
        #     map_rec = soup.findAll('script') 
        #     for each in map_rec:
        #         if 'new google.maps.LatLng' in each.text:
        #             # req_text = each.get_text().split('new google.maps.LatLng')[1]
        #             print("<<<<<<<<<<<<<<",each)
        #             # req_text = each.get_text().split('new google.maps.LatLng(')[1].split(");")[0]    
        #             # item['latitude'] = req_text.split(',')[0].strip()
        #             # item['longitude'] = req_text.split(',')[1].strip()
        #             # break
        # except Exception as e:
        #     print("--------------------->",e)
        # sys.exit()           
            # location=getAddress(lat,lng)
            # address = location.address

            # if "city" in location.raw["address"]:
            #     item["city"] = location.raw["address"]["city"]
            # elif "town" in location.raw["address"]:
            #     item["city"] = location.raw["address"]["town"]
            # elif "village" in location.raw["address"]:
            #     item["city"] = location.raw["address"]["village"]

            # item["address"] = address
            # item["zipcode"] = location.raw["address"]["postcode"]
        item["external_source"] = 'ramestateagent_PySpider_united_kingdom_en'    
        price_pw = getPrice(soup.find('span',class_='fullprice2').text.strip())  
        item['rent'] = price_pw*4    
        con = soup.find('i',class_='fas fa-phone')

        cont_no = con.find_parent('p').text.split('\n')[2].strip()
        email = con.find_parent('p').text.split('\n')[3].strip()
        
        item['description'] = desc
        item['landlord_phone'] = cont_no
        item['landlord_email'] = email
        item['landlord_name'] = 'ramestateagent'
        print (item)
        yield item
