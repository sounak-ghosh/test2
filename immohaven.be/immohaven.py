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


def cleanText(text):
    text = ''.join(text.split())
    text = re.sub(r'[^a-zA-Z0-9]', ' ', text).strip()
    return text.replace(" ","_").lower()



def cleanKey(data):
    if isinstance(data,dict):
        dic = {}
        for k,v in data.items():
            dic[cleanText(k)]=cleanKey(v)
        return dic
    else:
        return data

def getSqureMtr(text):
    list_text = re.findall(r'\d+',text)

    if len(list_text) == 2:
        output = int(list_text[0]+list_text[1])
    elif len(list_text) == 1:
        output = int(list_text[0])
    else:
        output=0

    return output


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
    result = []
    resp = requests.get('https://www.immohaven.be/nl/te-huur')

    soup = BeautifulSoup(resp.content)

    link = 'https://www.immohaven.be/nl/te-huur?view=list&task=showAjaxList&page='

    address = soup.find('div',class_='contact_details').find('div',class_='contact_address').text

    contact = soup.find('div',class_='contact_details').find('div',class_='contact_details_telephone').text

    email = soup.find('div',class_='contact_details').find('div',class_='contact_details_emailto').text

    i = 1
    while True:
        url = link+str(i)
        resp1 = requests.get(url)
        data = resp1.json()
        if not data['list']['Items']:
            break

        for dd in data['list']['Items']:
            external_link = 'https://www.immohaven.be/nl/te-huur?view=detail&id='+str(dd['ID'])
            external_source = 'Immo HavenSpider'
            title = dd['MainTypeName']+' TE '+dd['City']+'('+dd['Zip']+')'
            description = dd['DescriptionA']
            room_count = str(dd['NumberOfBedRooms'])
            rent = str(dd['Price'])

            img_resp = requests.get(external_link)
            img_soup = BeautifulSoup(img_resp.content)

            temp_dic={}
            if img_soup.find("div",class_="span4 panel-left"):
                print (True)
                fields = img_soup.find("div",class_="span4 panel-left").find_all("div",class_="field")
                for fd in fields:
                    if fd.find("div",class_="name") and fd.find("div",class_="value"):
                        kys = fd.find("div",class_="name").text.strip()
                        vals = fd.find("div",class_="value").text.strip()
                        temp_dic.update({kys:vals})

            cln_dic = cleanKey(temp_dic)

            utilities = 0
            if "algemeneonkosten" in cln_dic and getSqureMtr(cln_dic["algemeneonkosten"]):
                utilities = getSqureMtr(cln_dic["algemeneonkosten"])

            imgs = set()
            if img_soup.find('div',class_='picswiper'):
                for im in img_soup.find('div',class_='picswiper').find_all('img'):
                    imgs.add(im['src'])
            else:
                imgs = set()
            images = list(imgs)
            external_images_count = len(images)

            city = dd['City']
            latitude = dd['GoogleX']
            longitude = dd['GoogleY']
            zipcode = dd['Zip'] 

            property_type = dd['WebIDName']

            l = {}
            if "SurfaceTotal" in dd:
                l.update({'square_meters':int(dd['SurfaceTotal'])})
            if 'lift'  in dd['DescriptionA'] or 'elevator' in dd['DescriptionA']:
                l.update({'elevator':True})
            if 'swimming' in dd['DescriptionA']:
                l.update({'swimming_pool':True})
            if 'furnish' in dd['DescriptionA']:
                l.update({'furnished':True})
            if 'balcony' in dd['DescriptionA']:
                l.update({'balcony':True})
            if 'terrace' in dd['DescriptionA']:
                l.update({'terrace':True})
            if 'parking' in dd['DescriptionA']:
                l.update({'parking':True})

            l['external_link'] = external_link
            l['external_source'] = external_source
            l['title'] = title
            l['description'] = description

            if int(re.findall('\d+',room_count)[0]):
                l['room_count'] = int(re.findall('\d+',room_count)[0])

            if int(re.findall('\d+',rent)[0]):
                l['rent'] = int(re.findall('\d+',rent)[0])


            if utilities:
                l["utilities"] = utilities

            if "NumberOfBathRooms" in dd and dd["NumberOfBathRooms"]:
                l["bathroom_count"] = dd["NumberOfBathRooms"]

            if images:
                l['images'] = images
                l['external_images_count'] = external_images_count

            l['city'] = city
            l['latitude'] = latitude
            l['longitude'] = longitude
            l['zipcode'] = zipcode
            l['landlord_phone'] = contact
            l['landlord_email'] = email

            if ("student" in property_type.lower() or "étudiant" in property_type.lower() or  "studenten" in property_type.lower()) and ("apartment" in property_type.lower() or "appartement" in property_type.lower()):
                l['property_type'] = "student_apartment"
            elif "appartement" in property_type.lower() or "apartment" in property_type.lower():
                l['property_type'] = "apartment"
            elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower() or "house" in property_type.lower():
                l['property_type'] = "house"
            elif "chambre" in property_type.lower() or "kamer" in property_type.lower() or "room" in property_type.lower():
                l['property_type'] = "room"
            # elif "commerciale" in property_type.lower() or "reclame" in property_type.lower() or "commercial" in property_type.lower():
            #     l['property_type'] = "property_for_sale"
            elif "studio" in property_type.lower():
                l['property_type'] = "studio"
            else:
                l['property_type'] = "NA"

            l["currency"] = "EUR"

            if img_soup.find('div',class_='span4 panel-left'):
                for div in img_soup.find('div',class_='span4 panel-left').find_all('div',class_='field'):
                    if 'Adres' in div.text:
                        add = div.text.strip().replace('\n',' ').replace('Adres : ','')
                        l['address'] = add

            if "address" not in l:
                location = getAddress(latitude,longitude)

                l['address'] = location.address


            if l["property_type"] in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
                result.append(l)
        i = i+1
    return result

def write_json():
    data = get_data()
    data = json.dumps(data,indent=4, sort_keys=True, default=str)
    with open('immohaven.json','w') as f:
        f.write(data)
write_json()
