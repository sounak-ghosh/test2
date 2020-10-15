import scrapy
import js2xml
from ..loaders import ListingLoader
from ..items import ListingItem
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date
import re
from bs4 import BeautifulSoup
import requests

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city

def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = geolocator.reverse(coordinates)
    return location

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = int(list_text[0]+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return output


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

class UpgradeimmoSpider(scrapy.Spider):
    name = 'heylenvastgoed_antwerpen'
    allowed_domains = ['heylenvastgoed.be']
    start_urls = ['www.heylenvastgoed.be']
    execution_type = 'testing'
    country = 'dutch'
    locale ='nl'

    def start_requests(self):
        i = 1
        start_urls = []
        url = "https://www.heylenvastgoed.be/nl/te-huur/in-antwerpen/pagina-"
        while True:
            if requests.get(url+str(i)).status_code !=200:
                break
            else:
                start_urls.append({"url":url+str(i),"property_type":''})
            i+=1

        for urls in start_urls:
            yield scrapy.Request(url=urls.get('url'),
                                 callback=self.parse,
                                 meta={'property_type': urls.get('property_type')})

            


    def parse(self, response, **kwargs):

        soup1 = BeautifulSoup(response.body)
        for li in soup1.find('section',id='properties__list').find('ul').find_all('li',recursive=False):
            if not li.find('a',class_='property-contents'):
                continue

            rec = {}
            property_type = li.find('p',class_='category').text
            rent = li.find('p',class_='price').text
            city = li.find('p',class_='city').text
            room_count = '0'
            if li.find('li',class_='rooms'):
                room_count = li.find('li',class_='rooms').text
            else:
                room_count = '0'
            external_link = li.find('a',class_='property-contents')['href']

            yield scrapy.Request(
                url=external_link,
                callback=self.get_property_details,
                meta={'property_type': property_type,'rent':rent,'city':city,'room_count':room_count,'external_link':external_link}
            )
       


    def get_property_details(self, response):
        item = ListingItem()

        external_link = response.meta.get('external_link')
        room_count = response.meta.get('room_count')
        rent = response.meta.get('rent')
        city = response.meta.get('city')
        property_type = response.meta.get('property_type')
        temp_dic = {}
        soup2 = BeautifulSoup(response.body)

        item["external_link"] = external_link
        item["city"] = city

        if soup2.find("section",id="property__detail"):
                all_dl = soup2.find("section",id="property__detail").findAll("dl")

                for dl in all_dl:
                    all_divs = dl.findAll("div")
                    for ech_div in all_divs:
                        if ech_div.find("dt") and ech_div.find("dd"):
                            temp_dic[ech_div.find("dt").text] = ech_div.find("dd").text.strip()





        temp_dic = cleanKey(temp_dic)

        if "beschikbaarheid" in temp_dic and num_there(temp_dic["beschikbaarheid"]):
            item["available_date"] = temp_dic["beschikbaarheid"]

        if "kosten" in temp_dic:
            text_list = re.findall('\d+',temp_dic["kosten"])
            if int(text_list[0]):
                item["utilities"]=int(text_list[0])

        if "gemeubeld" in temp_dic and temp_dic["gemeubeld"] == "ja":
            item["furnished"]=True
        elif "gemeubeld" in temp_dic and temp_dic["gemeubeld"] == "nee":
            item["furnished"]=False

        if "lift" in temp_dic and temp_dic["lift"] == "ja":
            item["elevator"]=True
        elif "lift" in temp_dic and temp_dic["lift"] == "nee":
            item["elevator"]=False

        if "verdieping" in temp_dic:
            item["floor"]=temp_dic["verdieping"]

        if "balkon" in temp_dic and temp_dic["balkon"] == "ja":
            item["balcony"]=True
        elif "balkon" in temp_dic and temp_dic["balkon"] == "nee":
            item["balcony"]=False

        if "epc" in temp_dic:
            item["energy_label"]=temp_dic["epc"]

        if "badkamers" in temp_dic and getSqureMtr(temp_dic["badkamers"]):
            item["bathroom_count"]=getSqureMtr(temp_dic["badkamers"])   






        sq_mt = 0
        if soup2.find('i',class_='icon area-big'):
            sq_mt = sq_mt = re.findall('\d+',soup2.find('i',class_='icon area-big').find_previous('li').text)[0]

        item["address"]= soup2.find('section',id='property__title').find('div',class_='address').text.replace('Adres:','')

        item["title"]= soup2.find('section',id='property__title').find('div',class_='name').text

        item["description"]= soup2.find('div',id='description').text
        ss=None
        try:
            ss = geolocator.geocode(city)
        except:
            pass
            
        if int(sq_mt):
            item["square_meters"]= int(sq_mt)

        item["currency"]='EUR'

        if "tudiant" in property_type.lower() or  "studenten" in property_type.lower() and "appartement" in property_type.lower():
            property_type = "student_apartment"
        elif "appartement" in property_type.lower():
            property_type = "apartment"
        elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower():
            property_type = "house"
        elif "chambre" in property_type.lower() or "kamer" in property_type.lower():
            property_type = "room"
        elif "studio" in property_type.lower():
            property_type = "studio"
        else:
            property_type = "NA"


        rent = rent.replace('.','')
        if re.findall('\d+',rent):
            item["rent"]=int(re.findall('\d+',rent)[0])
        

        if int(re.findall('\d+',room_count)[0]):
            item["room_count"]=int(re.findall('\d+',room_count)[0])

    
        item["external_source"]='Heylen Vastgoed antwerpen Spider'

        if ss:
            item["latitude"]= str(ss.latitude)
            item["longitude"]= str(ss.longitude)



            location = getAddress(rec["latitude"],rec["longitude"])
            item["zipcode"]= location.raw["address"]["postcode"]

            
        item["landlord_phone"]= soup2.find('ul',id='sub__nav').find('a',class_=re.compile('mobile')).text
        item["landlord_email"]= soup2.find('ul',id='sub__nav').find('a',class_=re.compile('mail')).text
        item["landlord_name"]= 'Heylen Vastgoed Herentals'

        if soup2.find('div',class_='detail garage-details') and 'buitenparking' in soup2.find('div',class_='detail garage-details').text:
            item["parking"]=True

        if soup2.find('div',class_='detail layout-details') and 'terras' in soup2.find('div',class_='detail layout-details').text:
            item["terrace"]= True

        soup2.find('section',id='property__photos').find_all('a')

        images = []
        for a in soup2.find('section',id='property__photos').find_all('a'):
            images.append(a['href'])
        item["images"]= images
        item["external_images_count"]= len(images)


        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            yield item
