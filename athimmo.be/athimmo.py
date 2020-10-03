import requests
from bs4 import BeautifulSoup
import re,json

unicode_dic = {
    "-":"",
    ".":"",
    "+":"",
    "'":"",
    ",":"",
    "/":"",
    " ":"-",
    "à":"a",
    "ç":"c",
    "è":"e",
    "é":"e"
}


def replaceUnicode(text):
    for k,v in unicode_dic.items():
        if k in text:
            text = text.replace(k,v)
    return text

def clean_value(text):
    if text is None:
        text = ""
    if isinstance(text,(int,float)):
        text = str(text.encode('utf-8').decode('ascii', 'ignore'))
    text = str(text.encode('utf-8').decode('ascii', 'ignore'))
    text = text.replace('\t','').replace('\r','').replace('\n','')
    return text.strip()

def getAddress(lat,lng):
    coordinates = str(lat)+","+str(lng)
    location = locator.reverse(coordinates)
    return location

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
    resp = requests.get('https://www.athimmo.be/')
    soup = BeautifulSoup(resp.content)

    a = 'https://www.athimmo.be/'+soup.find('button',class_='btn btn-tertiary btn-for-rent').find_previous('a')['href']

    resp1 = requests.get(a)
    soup1 = BeautifulSoup(resp1.content)

    li = 'https://www.athimmo.be/'+soup1.find('link',attrs={'as':'fetch'})['href']
    print (li)

    resp2 = requests.get(li)

    dic  = resp2.json()

    # print (json.dumps(dic))
    # exit()
    result = []
    for rec in dic['pageContext']['data'][u'contentRow'][0]['data']['propertiesList']:
        if rec['language'] == 'fr':
            l = {}
            l['title'] = rec['TypeDescription']
            l['external_source'] = 'Athimmo2000Spider'
            l['description'] = rec['DescriptionA']
            if int(rec['NumberOfBedRooms']):
                l['room_count'] = int(rec['NumberOfBedRooms'])
            if int(rec["Price"]):
                l['rent'] = int(rec['Price'])
            l['images'] = rec['LargePictures']
            l['city'] = rec['City']
            if rec['GoogleX']:
                l['latitude'] = rec['GoogleX']
            if rec["GoogleY"]:
                l['longitude'] = rec['GoogleY']
            l['landlord_name'] = 'Athimmo'
            l['landlord_phone'] = soup.find('a',title='Phone').text.strip()
            l['landlord_email'] = soup.find('a',title='Mail').text.strip()
            l['zipcode'] = rec['Zip']
            l['address'] = rec['Street']+' '+str(rec['HouseNumber'])+' '+' '+rec['Zip']+rec['City']
            l["currency"] = "EUR"

            ####################property types##################
            if "étudiant" in rec['MainTypeName'].lower() or  "studenten" in rec['MainTypeName'].lower() and "appartement" in rec['MainTypeName'].lower():
                l['property_type'] = "student_apartment"
            elif "appartement" in rec['MainTypeName'].lower():
                l['property_type'] = "apartment"
            elif "woning" in rec['MainTypeName'].lower() or "maison" in rec['MainTypeName'].lower() or "huis" in rec['MainTypeName'].lower():
                l['property_type'] = "house"
            elif "chambre" in rec['MainTypeName'].lower() or "kamer" in rec['MainTypeName'].lower():
                l['property_type'] = "room"
            # elif "commerciale" in rec['MainTypeName'].lower() or "reclame" in rec['MainTypeName'].lower():
            #     l['property_type'] = "property_for_sale"
            elif "studio" in rec['MainTypeName'].lower():
                l['property_type'] = "studio"
            else:
                l['property_type'] = "NA"
            #####################################################

            if 'lift' in rec['DescriptionA'].lower() or 'elevator' in rec['DescriptionA'].lower():
                l.update({'elevator':True})
            if 'swimming' in rec['DescriptionA'].lower():
                l.update({'swimming_pool':True})
            if 'furnish' in rec['DescriptionA'].lower():
                l.update({'furnished':True})
            if 'balcony' in rec['DescriptionA'].lower():
                rec.update({'balcony':True})
            if 'parking' in rec['DescriptionA'].lower():
                l.update({'parking':True})
            l['terrace'] = rec['HasTerrace']
            l['external_images_count'] = len(rec['LargePictures'])

            TypeDescription = rec['TypeDescription']
            if len(rec['TypeDescription']) > 70:
                TypeDescription = rec['TypeDescription'][:70].strip()
            
            ext_li = 'https://www.athimmo.be/fr/a-louer/'+replaceUnicode(rec['City'].lower())+'/'+replaceUnicode(TypeDescription.lower())+'/'+str(rec["ID"])
            res = requests.get(ext_li).status_code
            l['external_link'] = ext_li
            l['external_id'] = str(rec['ID'])
            if l['property_type'] in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
                result.append(l)

    return result

def write_json():
    data = get_data()
    data = json.dumps(data,indent=4, sort_keys=True, default=str)
    with open('athimmo.json','w') as f:
        f.write(data)

write_json()

