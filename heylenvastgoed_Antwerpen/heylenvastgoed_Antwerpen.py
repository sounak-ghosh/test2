import requests
from bs4 import BeautifulSoup
import re,json
import geopy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
geolocator = Nominatim(user_agent="myGeocoder")

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


def get_data():
    resp = requests.get('https://www.heylenvastgoed.be/nl/te-huur')

    soup =BeautifulSoup(resp.content)

    temp_list = []
    # for l in soup.find('div',id='offices__footer').find_all('li'):
    #     offices.append({'city':l.strong.text,'telephone':l.text.replace(l.strong.text,'').strip()})

    landlord_phone = soup.find('ul',id='sub__nav').find('a',class_=re.compile('mobile')).text
    landlord_email = soup.find('ul',id='sub__nav').find('a',class_=re.compile('mail')).text
    landlord_name = 'Heylen Vastgoed Herentals'

    result=[]
    lix = 'https://www.heylenvastgoed.be/nl/te-huur/in-antwerpen/pagina-'
    i = 1
    while True:
        url = lix+str(i)
        resp1 = requests.get(url)
        if resp1.status_code !=200:
            break

        soup1 = BeautifulSoup(resp1.content)
        i = i+1
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
            resp2 = requests.get(external_link)
            soup2 = BeautifulSoup(resp2.content)


            temp_dic = {}
            if soup2.find("section",id="property__detail"):
                all_dl = soup2.find("section",id="property__detail").findAll("dl")

                for dl in all_dl:
                    all_divs = dl.findAll("div")
                    for ech_div in all_divs:
                        if ech_div.find("dt") and ech_div.find("dd"):
                            temp_dic[ech_div.find("dt").text] = ech_div.find("dd").text.strip()


            temp_dic = cleanKey(temp_dic)

            if "beschikbaarheid" in temp_dic and num_there(temp_dic["beschikbaarheid"]):
                rec["available_date"] = temp_dic["beschikbaarheid"]

            if "kosten" in temp_dic:
                text_list = re.findall('\d+',temp_dic["kosten"])
                if int(text_list[0]):
                    rec["utilities"]=int(text_list[0])

            if "gemeubeld" in temp_dic and temp_dic["gemeubeld"] == "ja":
                rec["furnished"]=True
            elif "gemeubeld" in temp_dic and temp_dic["gemeubeld"] == "nee":
                rec["furnished"]=False

            if "lift" in temp_dic and temp_dic["lift"] == "ja":
                rec["elevator"]=True
            elif "lift" in temp_dic and temp_dic["lift"] == "nee":
                rec["elevator"]=False

            if "verdieping" in temp_dic:
                rec["floor"]=temp_dic["verdieping"]

            if "balkon" in temp_dic and temp_dic["balkon"] == "ja":
                rec["balcony"]=True
            elif "balkon" in temp_dic and temp_dic["balkon"] == "nee":
                rec["balcony"]=False

            if "epc" in temp_dic:
                rec["energy_label"]=temp_dic["epc"]

            if "badkamers" in temp_dic and getSqureMtr(temp_dic["badkamers"]):
                rec["bathroom_count"]=getSqureMtr(temp_dic["badkamers"])   



            
            sq_mt = 0
            if soup2.find('i',class_='icon area-big'):
                sq_mt = sq_mt = re.findall('\d+',soup2.find('i',class_='icon area-big').find_previous('li').text)[0]

            address = soup2.find('section',id='property__title').find('div',class_='address').text.replace('Adres:','')

            title = soup2.find('section',id='property__title').find('div',class_='name').text

            description = soup2.find('div',id='description').text
            ss=None
            try:
                ss = geolocator.geocode(city)
            except:
                pass
                
            if int(sq_mt):
                rec['square_meters'] = int(sq_mt)
            rec['currency'] = 'EUR'

            if "étudiant" in property_type.lower() or  "studenten" in property_type.lower() and "appartement" in property_type.lower():
                rec['property_type'] = "student_apartment"
            elif "appartement" in property_type.lower():
                rec['property_type'] = "apartment"
            elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower():
                rec['property_type'] = "house"
            elif "chambre" in property_type.lower() or "kamer" in property_type.lower():
                rec['property_type'] = "room"
            elif "studio" in property_type.lower():
                rec['property_type'] = "studio"
            else:
                rec['property_type'] = "NA"


            rent = rent.replace('.','')
            if re.findall('\d+',rent):
                rec['rent'] =int(re.findall('\d+',rent)[0])
            

            if int(re.findall('\d+',room_count)[0]):
                rec['room_count'] =int(re.findall('\d+',room_count)[0])

            rec['city'] =city
            rec['external_link'] =external_link
            rec['external_source'] = 'Heylen Vastgoed antwerpen Spider'
            rec['address'] =address

            rec['title'] =title

            rec['description'] =description
            if ss:
                rec['latitude'] = str(ss.latitude)
                rec['longitude'] = str(ss.longitude)

                location = getAddress(rec["latitude"],rec["longitude"])
                rec["zipcode"] = location.raw["address"]["postcode"]

                
            rec['landlord_phone'] = landlord_phone
            rec['landlord_email'] = landlord_email
            rec['landlord_name'] = landlord_name

            if soup2.find('div',class_='detail garage-details') and 'buitenparking' in soup2.find('div',class_='detail garage-details').text:
                rec['parking'] =True

            if soup2.find('div',class_='detail layout-details') and 'terras' in soup2.find('div',class_='detail layout-details').text:
                rec['terrace'] = True

            soup2.find('section',id='property__photos').find_all('a')

            images = []
            for a in soup2.find('section',id='property__photos').find_all('a'):
                images.append(a['href'])
                rec['images'] = images
                rec['external_images_count'] = len(images)
            if rec['property_type'] in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
                result.append(rec)

    # print (json.dumps(temp_list))
    return result

def write_json():
    data = get_data()
    data = json.dumps(data,indent=4, sort_keys=True, default=str)
    with open('heylenvastgoed_Antwerpen.json','w') as f:
        f.write(data)
write_json()
