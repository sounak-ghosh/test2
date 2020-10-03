import requests
from bs4 import BeautifulSoup
import re,json
import geopy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
geolocator = Nominatim(user_agent="myGeocoder")

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

def get_records(soup):
    result = []
    for di in soup.find('div',class_='row ev-search-results').find_all('div',recursive=False):
        rec = {}
        if not di.find('a',class_='ev-property-container'):
            continue
        if not di.find('div',class_='ev-teaser-title'):
            continue
        external_link = di.find('a',class_='ev-property-container')['href']
        title = di.find('div',class_='ev-teaser-title').text
        print (external_link,title)
        address = di.find('div',class_='ev-teaser-subtitle').text
        external_source = 'ENGEL & VOLKERS SABLON SPider'
        landlord_name = 'ENGEL & VOLKERS SABLON'
        room_count = '0'
        if di.find('img',title='Bedrooms'):
            room_count = di.find('img',title='Bedrooms').find_next('span').text
        rent = di.find('div',class_='ev-teaser-price').find('div',class_='ev-value').text
        city = address.split(',')[-1].strip().replace('city','').replace(')','').replace('(','')
        rec['title']= title
        rec['address']= address
        rec['external_source']= external_source
        rec['landlord_name']= landlord_name
        rec['external_link']= external_link
        if int(re.findall('\d+',room_count)[0]):
            rec['room_count']= int(re.findall('\d+',room_count)[0])
        if int(re.findall('\d+',rent)[0]):
            rec['rent']= int(re.findall('\d+',rent)[0])
        rec['city']= city
        ss= None
        try:
            ss = geolocator(city)
        except:
            pass
        resp1 = requests.get(external_link)
        soup1 = BeautifulSoup(resp1.content)


        all_tags = soup1.findAll("span",class_="ev-exposee-detail-fact-value")
        if len(all_tags) >= 5:
            for ech_tg in all_tags[:5]:
                if "utilities" in ech_tg.text.lower():
                    list_text = re.findall(r'\d+',ech_tg.text)
                    if int(list_text[0]):
                        rec["utilities"] = int(list_text[0])
                if "W-02" in ech_tg.text:
                    rec["external_id"] = ech_tg.text.strip()



        sur = 0
        if soup1.find('img',alt='Living area approx.-Icon'):
            sur =  int(re.findall('\d+',soup1.find('img',alt='Living area approx.-Icon').find_next('div').text)[0])
        
        if ss:
            rec['latitude'] = str(ss.latitude)
            rec['longitude'] = str(ss.longitude)   


        desc1= soup1.find_all('h2')[1].find_next('ul').text

        desc2 = soup1.find_all('h2')[2].find_next('ul').text

        desc = ''
        if soup1.find('p',itemprop='description'):
            desc = soup1.find('p',itemprop='description').text


        description = desc1+' '+desc2+' '+desc
        rec['description'] = description
        if 'lift' in description.lower() or 'elevator' in description.lower():
            rec.update({'elevator':True})
        if 'swimming' in description.lower():
            rec.update({'swimming_pool':True})
        if 'furnish' in description.lower():
            rec.update({'furnished':True})
        if 'balcony' in description.lower():
            rec.update({'balcony':True})
        if 'terrace' in description.lower():
            rec.update({'terrace':True})
        if 'parking' in description.lower():
            rec.update({'parking':True})
        
        rec['currency'] = 'EUR'
        if int(sur):
            rec['square_meters'] = int(sur)
        property_type=soup1.find('div',class_='ev-exposee-content ev-exposee-subtitle').text.split(',')[0].strip()

        if "student" in property_type.lower() or "étudiant" in property_type.lower() or  "studenten" in property_type.lower() and "apartment" in property_type.lower() or "appartement" in property_type.lower():
            rec['property_type'] = "student_apartment"
        elif "appartement" in property_type.lower() or "apartment" in property_type.lower():
            rec['property_type'] = "apartment"
        elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower() or "house" in property_type.lower():
            rec['property_type'] = "house"
        elif "chambre" in property_type.lower() or "kamer" in property_type.lower() or "room" in property_type.lower():
            rec['property_type'] = "room"
        elif "studio" in property_type.lower():
            rec['property_type'] = "studio"
        else:
            rec['property_type'] = "NA"

        rec['landlord_phone']=soup1.find('li',itemprop='contactPoint').text.replace('Phone:','').strip()
        images = []
        for im in soup1.find('div',class_='ev-image-gallery-frame').find_all('img'):
            images.append(im['src'])
        rec['images'] = images
        rec['external_images_count'] = len(images)
        if rec['property_type'] in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
            result.append(rec)
    return result

def get_data():
    resp = requests.get('https://www.engelvoelkers.com/en/search/?q=&startIndex=0&businessArea=residential&sortOrder=DESC&sortField=sortPrice&pageSize=18&facets=bsnssr%3Aresidential%3Bcntry%3Abelgium%3Brgn%3Abrussels_surroundings%3Btyp%3Arent%3B')

    soup = BeautifulSoup(resp.content)
    
    res = get_records(soup)
    while True:
        if not soup.find('ul',class_='ev-pager-row').find('a',class_='ev-pager-next'):
            break
        nex = soup.find('ul',class_='ev-pager-row').find('a',class_='ev-pager-next')['href']
        resp = requests.get(nex)
        soup = BeautifulSoup(resp.content)
        res.extend(get_records(soup))
    return res

def write_json():
    data = get_data()
    data = json.dumps(data,indent=4, sort_keys=True, default=str)
    with open('engelvoelkers.json','w') as f:
        f.write(data)
write_json()
