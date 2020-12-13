import scrapy
import re
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
#     coordinates = str(lat)+","+str(lng) 
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
    name = "santoni_fr_PySpider_france_fr"
    allowed_domains = ['www.santoni.fr']
    start_urls = ['www.santoni.fr']
    execution_type = 'testing'
    country = 'france'
    locale ='fr'

    def start_requests(self):
        url = 'https://www.santoni.fr/fr/liste.htm?page=1&menuSave=2&TypeModeListeForm=text&vlc=4&LibMultiType=Tous+types+de+bien&lieu-alentour=0'
        
        yield scrapy.Request(
            url=url,
            callback=self.parse)




    def parse(self,response):
        soup = BeautifulSoup(response.body)

        page_count = int(soup.find("span",class_="nav-page-position").text.split("/")[-1])

        for ech_page in range(1,page_count+1):
            url = 'https://www.santoni.fr/fr/liste.htm?page={}&menuSave=2&TypeModeListeForm=text&vlc=4&LibMultiType=Tous+types+de+bien&lieu-alentour=0'.format(ech_page)
            print (url)
            yield scrapy.Request(url=url,
                                 callback=self.get_page_detail)



    def get_page_detail(self, response):
        external_link = []
        property_type = []
        soup1 = BeautifulSoup(response.body)

        ex_link = soup1.findAll("ul", {"class":"liste-bien-buttons"})
        for el in ex_link:
            external_link.append(el.find("a").attrs['href'])

        p_type = soup1.findAll("h2",{"class":"liste-bien-type"})
        for pt in p_type:
            property_type.append(pt.text)

        for i, idx in enumerate(external_link, 0):
            yield scrapy.Request(
                url=external_link[i],
                callback=self.get_property_details,
                meta={'property_type': property_type[i],'external_link':external_link[i]}
            )  

    def get_property_details(self, response):
        item = ListingItem()

        external_link = response.meta.get('external_link')
        property_type = response.meta.get('property_type')
        
        soup2 = BeautifulSoup(response.body)
        address = soup2.find("div",{"class":"detail-bien-specs"}).find("li",{"class":"detail-bien-ville"}).text.strip()
        city = address.split(' ')[0]
        rent = soup2.find("div",{"class":"detail-bien-prix"}).text
        description = soup2.find("div",{"class":"detail-bien-desc-content clearfix"}).find("p").text.strip()
        
        images = []
        for img in soup2.findAll("div",{"class":"diapo is-flap"}):
            images.append(img.find("div", {"class" : "bg-blur-image"}).find("img").get("data-src").split('?')[0])
        if images:
            item["images"]= images
            item["external_images_count"]= len(images)

        # location = getAddress(soup2.find("li", {"class": "gg-map-marker-lat"}).text,soup2.find("li", {"class": "gg-map-marker-lng"}).text)
        item["latitude"] = soup2.find("li", {"class": "gg-map-marker-lat"}).text.strip()
        item["longitude"] = soup2.find("li", {"class": "gg-map-marker-lng"}).text.strip()
        # item["zipcode"]= location.raw["address"]["postcode"]
        # item["address"] = location.address


        temp_dic = {}
        all_li = soup2.findAll("div", {"class" : "detail-infos-sup"})
        for al in all_li:
            for l in al.findAll("li"):
                all_span = l.findAll("span")
                if len(all_span) == 2:
                    key = all_span[0].text
                    val = all_span[1].text
                    temp_dic[key] = val

        temp_dic = cleanKey(temp_dic)

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

        if "salled_eau" in temp_dic and getSqureMtr(temp_dic["salled_eau"]):
            item["bathroom_count"]=getSqureMtr(temp_dic["salled_eau"])  


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


        if "garage" in description.lower() or "parking" in description.lower():
            item["parking"] = True
        if "terras" in description.lower():
            item["terrace"] = True
        if "zwembad" in description.lower() or "swimming" in description.lower():
            item["swimming_pool"] = True
        if "gemeubileerd" in description.lower()or "aménagées" in description.lower() or "furnished" in description.lower():
            item["furnished"]=True
        if "garage" in description.lower() or "parking" in description.lower():
            item["parking"] = True


        if "consommation-" in soup2.find("div", {"class" : "detail-bien-dpe clearfix"}).findAll("img")[0].get("src"):
            item["energy_label"] = soup2.find("div", {"class" : "detail-bien-dpe clearfix"}).findAll("img")[0].get("src").split('consommation-')[1].split('.')[0] + ' kWhEP/m2'
        

        if soup2.find("span",class_="cout_charges_mens") and num_there(soup2.find("span",class_="cout_charges_mens").text):
            item["utilities"] = getSqureMtr(soup2.find("span",class_="cout_charges_mens").text)

        if soup2.find("span",class_="cout_honoraires_loc") and num_there(soup2.find("span",class_="cout_honoraires_loc").text):
            item["deposit"] = getSqureMtr(soup2.find("span",class_="cout_honoraires_loc").text)


        item["room_count"]= int(re.findall(r'\d+', soup2.find("h1", {"class" : "side-detail-titre"}).text.split(',')[1])[0])
        item["currency"]='EUR'
        item["external_link"] = external_link
        item["city"] = city
        item["title"] = soup2.find("h1", {"class" : "side-detail-titre"}).text
        item["rent"] = int(re.findall(r'\d+', rent)[0])
        item["description"] = soup2.find("div",{"class":"detail-bien-desc-content clearfix"}).find("p").text.strip()
        item["square_meters"] = int(re.findall('\d+',temp_dic["habitable"])[0])
        item["external_source"] = 'santoni_fr_PySpider_france_fr'
        item["external_id"] = soup2.findAll("span",itemprop="productID")[1].text.strip()
        item["landlord_name"] = soup2.find("strong", itemprop="name").text.strip()
        item["landlord_phone"] = soup2.find("li", itemprop="telephone").find("a").text.strip()
        item["property_type"] = property_type

        if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            print(item)
            yield item
        




