# Author: Sounak Ghosh
import scrapy
import js2xml
import re
import math
import json
from bs4 import BeautifulSoup
import requests
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
# import geopy
# from geopy.geocoders import Nominatim
# from geopy.extra.rate_limiter import RateLimiter

# locator = Nominatim(user_agent="myGeocoder")

# def getAddress(lat,lng):
#     coordinates = str(lat)+","+str(lng) # "52","76"
#     location = locator.reverse(coordinates)
#     return location

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = float(list_text[0]+"."+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return int(output)

def getPrice(text):
    list_text = re.findall(r'\d+',text)


    if "," in text:
        if len(list_text) > 1:
            output = float(list_text[0]+list_text[1])
        elif len(list_text) == 1:
            output = int(list_text[0])
        else:
            output=0
    else:
        if len(list_text) > 1:
            output = float(list_text[0]+"."+list_text[1])
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

def clean_value(text):
    if text is None:
        text = ""
    if isinstance(text,(int,float)):
        text = str(text.encode('utf-8').decode('ascii', 'ignore'))
    text = str(text.encode('utf-8').decode('ascii', 'ignore'))
    text = text.replace('\t','').replace('\r','').replace('\n','')
    return text.strip()

def clean_key(text):
    if isinstance(text,str):
        text = ''.join([i if ord(i) < 128 else ' ' for i in text])
        text = text.lower()
        text = ''.join([c if 97 <= ord(c) <= 122 or 48 <= ord(c) <= 57 else '_'                                                                                         for c in text ])
        text = re.sub(r'_{1,}', '_', text)
        text = text.strip("_")
        text = text.strip()

        if not text:
            raise Exception("make_key :: Blank Key after Cleaning")

        return text.lower()
    else:
        raise Exception("make_key :: Found invalid type, required str or unicode                                                                                        ")

def traverse( data):
    if isinstance(data, dict):
        n = {}
        for k, v in data.items():
            k = str(k)
            if k.startswith("dflag") or k.startswith("kflag"):
                if k.startswith("dflag_dev") == False:
                    n[k] = v
                    continue

            n[clean_key(clean_value(k))] = traverse(v)

        return n

    elif isinstance(data, list) or isinstance(data, tuple) or isinstance(data, set):                                                                                     
        data = list(data)
        for i, v in enumerate(data):
            data[i] = traverse(v)

        return data
    elif data is None:
        return ""
    else:
        data = clean_value(data)
        return data


class QuotesSpider(scrapy.Spider):
    name = "astonchase_PySpider_london_en"
    allowed_domains = ['www.astonchase.com']
    start_urls = ['www.astonchase.com']
    execution_type = 'testing'
    country = 'london'
    locale ='en'

    def start_requests(self):
        url ="https://www.astonchase.com/lettings/properties-to-rent/properties-to-rent-in-london/page-1"
        yield scrapy.Request(
            url=url, 
            callback=self.parse)

    def parse(self, response):
        soup = BeautifulSoup(response.body,"html.parser")
        
        if soup.find("ul",class_="pagination"):
            tot_page = soup.find("ul",class_="pagination").find_all("li")[-3].find("a")["title"]

        print (tot_page)

        for i in range(1,int(tot_page)+1):
            yield scrapy.FormRequest(
                url="https://www.astonchase.com/lettings/properties-to-rent/properties-to-rent-in-london/page-"+str(i), 
                callback=self.get_external_link)

    def get_external_link(self, response):
        soup = BeautifulSoup(response.body,"html.parser")

        if soup.find('div',class_='section-body').find('ul',class_='properties').find_all('div',class_="property-image"):
            divs = (soup.find('div',class_='section-body').find('ul',class_='properties').find_all('div',class_="property-image"))
            
            for div in divs:

                li = div.find_previous('li')
                rec = {}
                external_link = 'https://www.astonchase.com'+li.find('h5').find('a')['href']
                external_source = 'astonchase_PySpider_london_en'
                address = li.find('h5').text
                if li.find('i',class_="icon-bedrooms"):
                    room_count = int(li.find('i',class_="icon-bedrooms").find_previous('span').text)
                    rec['room_count'] = room_count

                rent = int(re.findall('\d+',li.find('div',class_="property-price per-month").text.replace(',',''))[0])
                if li.find('i',class_="icon-bathrooms"):
                    bathroom_count = int(li.find('i',class_="icon-bathrooms").find_previous('span').text)
                    rec['bathroom_count'] = bathroom_count

                rec['external_link'] = external_link
                rec['external_source'] = external_source
                rec['address'] = address
                rec['currency'] = 'EUR'
                rec['rent'] = rent


                yield scrapy.Request(
                    url=external_link, 
                    callback=self.get_property_details,
                    meta = rec
                )

    def get_property_details(self, response):
        item = ListingItem()
        sou = BeautifulSoup(response.body,"html.parser")

        for k,v in response.meta.items():
            try:
                item[k] = v
            except:
                pass


        external_link = response.url
        print(external_link)
        item["external_link"] = external_link
        if sou.find("header",class_ = "section-head"):
            text_val =  (sou.find("header",class_ = "section-head").find("h2").text.strip())
            item["title"] = text_val
            if "house" in text_val.lower():
                item["property_type"] = "house"
            else:
                item["property_type"] = "apartment"
        
        floor_image = []
        if sou.find("img",alt="floorplan"):
            floor_image = [sou.find("img",alt="floorplan")["src"]]
            item["floor_plan_images"] = floor_image

        tt = sou.find('div',id='amenities')
        if tt:
            if 'furnished' in tt.text.lower():
                item['furnished'] = True
            if 'parking' in tt.text.lower():
                item['parking'] = True
            if 'elevator' in tt.text.lower():
                item['elevator'] = True
            if 'balcony' in tt.text.lower():
                item['balcony'] = True
            if 'terrace' in tt.text.lower():
                item['terrace'] = True
            if 'swimming' in tt.text.lower():
                item['swimming_pool'] = True
            if 'washing machine' in tt.text.lower():
                item['washing_machine'] = True
            if 'dishwasher' in tt.text.lower():
                item['dishwasher'] = True
        for ss in sou.find_all('script'):
            if 'longi' in ss.text.lower():
                dic =  json.loads(ss.text)
                item['zipcode'] = dic['address']['postalCode']
                item['city'] = dic['address']['addressLocality']
                item['latitude'] = dic['geo']['latitude']
                item['longitude'] = dic['geo']['longitude']
        if sou.find('div',class_='callout-content'):
            item["landlord_name"] = sou.find('div',class_='callout-content').find_all('a')[0].text
            item["landlord_phone"] = sou.find('div',class_='callout-content').find_all('a')[1].text
            item["landlord_email"] = sou.find('div',class_='callout-content').find_all('a')[-1]['href'].replace('mailto: ','')
        imgs = set()
        for im in sou.find('div',class_='section-image').find_all('img'):
            imgs.add(im['src'])

        if imgs:
            item['images'] =  list(imgs)

        if imgs or floor_image:
            item['external_images_count'] = len(imgs)+len(floor_image)

        description = ''
        for p in sou.find('div',class_='section-content').find_all('p',recursive = False):
            description = description+ clean_value(p.text) 
        if description:
            item['description'] = description


        print (item)
        yield(item)


























        # rec = {}
        # address = soup2.find('h1').text

        # rent,room_count = re.findall('\d+',clean_value(soup2.find('h2').text.replace(',','')))

        # property_type = ''
        # if 'house' in clean_value(soup2.find('h2').text.replace(',','')).lower():
        #     property_type = 'house'
        # if 'apartment' in clean_value(soup2.find('h2').text.replace(',','')).lower():
        #     property_type = 'apartment'
        # if 'studio' in clean_value(soup2.find('h2').text.replace(',','')).lower():
        #     property_type = 'studio'
        # if 'studio' in clean_value(soup2.find('h2').text.replace(',','')).lower():
        #     property_type = 'studio'
        # else:
        #     property_type = ''
        # square_meters = 0
        # currency = 'EUR'

        # email = soup2.find('a',href=re.compile('info@')).text

        # contact = (re.findall('\d{11}',soup2.find('a',href=re.compile('info@')).find_previous('td').text.replace(' ','')))[0]

        # landlo = soup2.find('a',href=re.compile('info@')).find_previous('td').find('strong').text

        # city = address.split(',')[-1]

        # ss = None
        # try:
        #     ss = geolocator.geocode(city)
        # except:
        #     pass

        # if ss:
        #     item['latitude'] = str(ss.latitude)
        #     item['longitude'] = str(ss.longitude)

        # s = None
        # try:
        #     s = geolocator.reverse((rec['latitude'],rec['longitude']))
        # except:
        #     pass
        # if s:
        #     zipcode = s.raw['address'].get('postcode','').strip()
        #     item['zipcode'] = zipcode

        # item['city'] = city
        # item['address'] = address
        # item['rent'] = int(rent)
        # item['room_count'] = int(room_count)
        # item['property_type'] = property_type
        # item['square_meters'] = square_meters
        # item['currency'] = currency
        # item['external_link'] =external_link
        # item['external_source'] = external_source
        # item['landlord_name'] = landlo
        # item['landlord_email'] = email
        # item['landlord_phone'] = contact

        # img = set()
        # for im in soup2.find_all('img',attrs={'name':re.compile('TI')}):
        #     img.add('http://pmestates.com/'+im['src'])
        # if img:
        #     images = list(img)
        #     external_images_count = len(img)
        #     item['images'] = images
        #     item['external_images_count'] = external_images_count

        # desc = clean_value(soup2.find('h1').find_parent('tr').find_parent('tr').find_parent('tr').find_next_sibling('tr').text)
        # item['description'] = desc
        # print (item)



























        # item["external_id"] = response.meta.get('external_id')
        # item["title"] = response.meta.get('title')
        # item["address"] = response.meta.get('address')
        # item["zipcode"] = response.meta.get('zipcode')
        # item["city"] = response.meta.get('city')
        # if getSqureMtr(response.meta.get('rent')):
        #     item["rent"] = getSqureMtr(response.meta.get('rent'))
        # if response.meta.get('room_count'):
        #     item["room_count"] = response.meta.get('room_count')
        # # item["date_available"] = response.meta.get('date_available')
        # item["latitude"] = response.meta.get('lat')
        # item["longitude"] = response.meta.get('lng')
        # item["currency"]='EUR'


        # if "rent" not in item:
        #     if soup2.find("i",class_="p-calendar").find_next("span"):
        #         text_price = soup2.find("i",class_="p-calendar").find_next("span").text.strip()
        #         if getPrice(text_price) and "pcm" in text_price.lower():
        #             item["rent"] = getPrice(text_price)
        #         elif getPrice(text_price) and "pppw" in text_price.lower():
        #             item["rent"] = getPrice(text_price)*4

        # images = []
        # for img in soup2.findAll("div", class_="block-grid-item property-image-thumbnail-container"):
        #     images.append('https://www.pickardproperties.co.uk'+img.find("a")['href'].strip())
        # if images:
        #     item["images"]= images

        # floor_image = []
        # if soup2.find("div",id="floor-plan"):
        #     url_text = soup2.find("div",id="floor-plan").find("a")["href"]
        #     floor_image = ["https://www.pickardproperties.co.uk"+url_text]
        #     item["floor_plan_images"] = floor_image
        # if floor_image or images:
        #     item["external_images_count"]= len(images)+len(floor_image)

        # if soup2.find("div", id="epc"):
        #     item["energy_label"] = soup2.find("div", id="epc").find("a")['href'].split('_')[-1].replace('.png', '')[:2]

        # for dep in soup2.find("div", class_="property-spec-boxes block-grid-lg-2 block-grid-md-1 block-grid-sm-1 block-grid-xs-2").findAll("div", class_="block-grid-item"):
        #     if re.findall("(.+)deposit",str(dep.text.strip())):
        #         item["deposit"] = getSqureMtr(re.findall("(.+)deposit",str(dep.text.strip()))[0])

        # description = soup2.find("div", class_="more-property").text.strip()
        # item["description"] = description
        # if "swimming" in description.lower():
        #     item["swimming_pool"] = True
        # if "furnish" in description.lower():
        #     item["furnished"]=True
        # if "parking" in description.lower():
        #     item["parking"] = True
        # if "balcony" in description.lower():
        #     item["balcony"]=True
        # if "lift" in description.lower() or "elevator" in description.lower():
        #     item["elevator"]=True

        # if "flat" in description.lower() or "apartment" in description.lower():
        #     property_type = "apartment"
        # elif "house" in description.lower() or "maisonette" in description.lower() or "bungalow" in description.lower():
        #     property_type = "house" 
        # else:
        #     property_type = "NA"
        # item["property_type"] = property_type

        # item["external_source"] = 'pickardproperties_PySpider_england_en'

        # if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
        #     print(item)
        #     yield item
