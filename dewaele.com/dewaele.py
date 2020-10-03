#!/usr/bin/env python
# coding: utf-8

import requests 
from bs4 import BeautifulSoup
import re,json
import geopy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import ast
import base64
import pydash
from datetime import datetime


def strToDate(text):
	if "/" in text:
		date = datetime.strptime(text, '%d/%m/%Y').strftime('%Y-%m-%d')
	elif "-" in text:
		date = datetime.strptime(text, '%Y-%m-%d').strftime('%Y-%m-%d')
	else:
		date = text
	return date



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
		output = int(list_text[0])
	elif len(list_text) == 1:
		output = int(list_text[0])
	else:
		output=0

	return output


def scrapeSubInfo(soup):

	dic = {}
	if soup.find("div",class_="panel",id="description"):
		description = soup.find("div",class_="panel",id="description").text.strip()
		pydash.set_(dic,"description",description)


		if soup.find("div",class_="responsive-table margin-bottom full-label"):
			basicInfo = soup.find("div",class_="responsive-table margin-bottom full-label").findAll("div",class_="cell")

			rec_dic = {}
			for info in basicInfo:
				text_info = info.text.strip()
				if ":" in text_info:
					rec_dic.update({text_info.split(":")[0].strip():text_info.split(":")[1].strip()})


			rec_dic = cleanKey(rec_dic)
			if "beschikbaarvanaf" in rec_dic:
				if "-" in rec_dic["beschikbaarvanaf"]:
					pydash.set_(dic,"available_date",strToDate(rec_dic["beschikbaarvanaf"]))
					
			if "woonopp" in rec_dic:
				if getSqureMtr(rec_dic["woonopp"]):
					square_meters = getSqureMtr(rec_dic["woonopp"])
					pydash.set_(dic,"square_meters",square_meters)


			if "lift" in description.lower():
				pydash.set_(dic,"elevator",True)
			elif "geen lift" not in description.lower():
				pydash.set_(dic,"elevator",False)

			if "garage" in description.lower() or "parking" in description.lower() or "autostaanplaat" in description.lower():
				pydash.set_(dic,"parking",True)
			if "terras" in description.lower():
				pydash.set_(dic,"terrace",True)
			if "balcon" in description.lower() or "balcony" in description.lower():
				pydash.set_(dic,"balcony",True)
			if "zwembad" in description.lower() or "swimming" in description.lower():
				pydash.set_(dic,"swimming_pool",True)
			if "gemeubileerd" in description.lower() or "furnished" in description.lower():
				pydash.set_(dic,"furnished",True)
			# if "machine à laver" in description.lower():
			# 	pydash.set_(dic,"washing_machine",True)
			# if "lave" in description.lower() and "vaisselle" in description.lower():
			# 	pydash.set_(dic,"dishwasher",True)


		landlord_name = soup.find("li",class_ = "media agent").find("div",class_="bd").find("h3").text.strip()
		landlord_email = "info@dewaele.com"
		landlord_phone = "056 234 330"

		pydash.set_(dic,"landlord_name",landlord_name)
		pydash.set_(dic,"landlord_email",landlord_email)
		pydash.set_(dic,"landlord_phone",landlord_phone)

	return dic


def proprtyDeatil(list_data):

	listProprty = []
	for echData in list_data:

		rent=echData["sort_price"]
		zipcode = echData["a_postcode"]
		title = echData["a_titel"]
		latitude = echData["a_geo_lat"]
		longitude = echData["a_geo_lon"]
		city = echData["a_gemeente"]
		address = echData["a_straat"]+","+zipcode+" "+city
		bedCount = echData["a_aantal_slaapkamers"]
		external_id = echData["a_ref"]
		external_source = "dewaele.com"
		external_link = "https://www.dewaele.com"+echData["url_slugify"]

		property_type = echData["subtype_woning"]

		if "étudiant" in property_type.lower() or  "studenten" in property_type.lower() and "appartement" in property_type.lower():
		    property_type = "student_apartment"
		elif "appartement" in property_type.lower():
		    property_type = "apartment"
		elif "woning" in property_type.lower() or "maison" in property_type.lower() or "huis" in property_type.lower():
		    property_type = "house"
		elif "chambre" in property_type.lower() or "kamer" in property_type.lower():
		    property_type = "room"
		# elif "commerciale" in property_type.lower() or "reclame" in property_type.lower():
		#     property_type = "property_for_sale"
		elif "studio" in property_type.lower():
		    property_type = "studio"
		else:
		    property_type = "NA"




		imgLst = echData["lazyload"]
		if echData["picture_url"]:
			imgLst.append(echData["picture_url"])


		print (external_link)
		if property_type in ["apartment", "house", "room", "property_for_sale", "student_apartment", "studio"]:
			count = 0
			while count < 5:
				try:
					response = requests.get(external_link,timeout=30)
					count = 5
				except Exception as e:
					print (e)
				count+=1

			soup = BeautifulSoup(response.content,"html.parser")

			dic_details = scrapeSubInfo(soup)


			dic_details.update({"zipcode":zipcode,"property_type":property_type,"title":title,
				"latitude":latitude,"longitude":longitude,"city":city,"address":address,
				"external_link":external_link,"external_source":external_source,
				"external_images_count":len(imgLst),"images":imgLst,"external_id":external_id,"currency":"EUR"})


			if bedCount:
				pydash.set_(dic_details,"room_count",bedCount)
			if rent:
				pydash.set_(dic_details,"rent",rent)

			
			listProprty.append(dic_details)

	return listProprty




def scrapDetail(url):

	headers={
		"origin": "https://www.dewaele.com",
		"referer": "https://www.dewaele.com/nl/te-huur?hash=ZmlsdGVyW3JlZ2lvbl9sb25nXT0wJmZpbHRlcltyZWdpb25fbGF0XT0wJmZpbHRlcltzdGF0dXNfdHlwZV09MyZmaWx0ZXJbbGFuZ3VhZ2VdPW5sJmZpbHRlcltlX2lkXT00NjM5NSZmaWx0ZXJbZGlyXT1kZXNjJmZpbHRlcltvcmRlcl09aXNfbmV3JmZpbHRlclttaW5fcmVudF9wcmljZV09MCZmaWx0ZXJbbWF4X3JlbnRfcHJpY2VdPTAmZmlsdGVyW2Jkcm1zXT0wJmZpbHRlclttaW5fYndfb3BwXT0wJmZpbHRlclttYXhfYndfb3BwXT0wJmZpbHRlclttaW5fZ19vcHBdPTAmZmlsdGVyW21heF9nX29wcF09MCZmaWx0ZXJbcGFnZV09MQ%3D%3D&page=1",
		"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
		"X-Requested-With": "XMLHttpRequest"
	}

	count = 0
	while count < 5:
		try:
			response = requests.get(url,headers=headers,timeout = 30)
			count = 5
		except Exception as e:
			print (e)
		count+=1


	json_load = json.loads(response.content.decode("utf-8"))

	totpage = json_load["total"]/12
	temp_page = json_load["total"]//12

	if totpage != temp_page:
		totpage = int(totpage)+1
	else:
		totpage = int(totpage)


	totProprty = []
	for page in range(1,totpage+1):
		print (">>>>>>>",page)

		strTobyte = str.encode("page="+str(page))
		base64txt = base64.b64encode(strTobyte)
		url = "https://www.dewaele.com/?ACT=108&cache=off&hash=JmZpbHRlcltyZWdpb25dPSZmaWx0ZXJbcmVnaW9uX2xvbmddPTAmZmlsdGVyW3JlZ2lvbl9sYXRdPTAmZmlsdGVyW3N0YXR1c190eXBlXT0zJmZpbHRlcltwb3N0YWxdPSZmaWx0ZXJbY2l0eV09JmZpbHRlcltwYXJlbnRfY2l0eV09JmZpbHRlcltwYXJlbnRfbGFiZWxdPSZmaWx0ZXJbZl9jXT0mZmlsdGVyW2xhbmd1YWdlXT1ubCZmaWx0ZXJbZV9pZF09NDYzOTUmZmlsdGVyW2Rpcl09ZGVzYyZmaWx0ZXJbb3JkZXJdPWlzX25ldyZmaWx0ZXJbbWluX3ByaWNlXT0mZmlsdGVyW21heF9wcmljZV09JmZpbHRlclttaW5fcmVudF9wcmljZV09MCZmaWx0ZXJbbWF4X3JlbnRfcHJpY2VdPTAmZmlsdGVyW2Jkcm1zXT0wJmZpbHRlclt0eXBlXT0mZmlsdGVyW2JfaWRdPSZmaWx0ZXJbbWluX2J3X29wcF09MCZmaWx0ZXJbbWF4X2J3X29wcF09MCZmaWx0ZXJbbWluX2dfb3BwXT0wJmZpbHRlclttYXhfZ19vcHBdPTAmZmlsdGVyW2tleXdvcmRzXT0m{}".format(base64txt.decode("utf-8"))
		headers={
			"origin": "https://www.dewaele.com",
			"referer": "https://www.dewaele.com/nl/te-huur?hash=ZmlsdGVyW3JlZ2lvbl9sb25nXT0wJmZpbHRlcltyZWdpb25fbGF0XT0wJmZpbHRlcltzdGF0dXNfdHlwZV09MyZmaWx0ZXJbbGFuZ3VhZ2VdPW5sJmZpbHRlcltlX2lkXT00NjM5NSZmaWx0ZXJbZGlyXT1kZXNjJmZpbHRlcltvcmRlcl09aXNfbmV3JmZpbHRlclttaW5fcmVudF9wcmljZV09MCZmaWx0ZXJbbWF4X3JlbnRfcHJpY2VdPTAmZmlsdGVyW2Jkcm1zXT0wJmZpbHRlclttaW5fYndfb3BwXT0wJmZpbHRlclttYXhfYndfb3BwXT0wJmZpbHRlclttaW5fZ19vcHBdPTAmZmlsdGVyW21heF9nX29wcF09MCZmaWx0ZXJbcGFnZV09MQ%3D%3D&page={}".format(page),
			"user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
			"X-Requested-With": "XMLHttpRequest"
		}

		count = 0
		while count < 5:
			try:
				response = requests.get(url,headers=headers,timeout = 30)
				count = 5
			except Exception as e:
				print (e)
			count+=1

		json_load = json.loads(response.content.decode("utf-8"))
		totProprty.extend(json_load["properties"])


	return proprtyDeatil(totProprty)



url = "https://www.dewaele.com/?ACT=108&cache=off&hash=JmZpbHRlcltyZWdpb25dPSZmaWx0ZXJbcmVnaW9uX2xvbmddPTAmZmlsdGVyW3JlZ2lvbl9sYXRdPTAmZmlsdGVyW3N0YXR1c190eXBlXT0zJmZpbHRlcltwb3N0YWxdPSZmaWx0ZXJbY2l0eV09JmZpbHRlcltwYXJlbnRfY2l0eV09JmZpbHRlcltwYXJlbnRfbGFiZWxdPSZmaWx0ZXJbZl9jXT0mZmlsdGVyW2xhbmd1YWdlXT1ubCZmaWx0ZXJbZV9pZF09NDYzOTUmZmlsdGVyW2Rpcl09ZGVzYyZmaWx0ZXJbb3JkZXJdPWlzX25ldyZmaWx0ZXJbbWluX3ByaWNlXT0mZmlsdGVyW21heF9wcmljZV09JmZpbHRlclttaW5fcmVudF9wcmljZV09MCZmaWx0ZXJbbWF4X3JlbnRfcHJpY2VdPTAmZmlsdGVyW2Jkcm1zXT0wJmZpbHRlclt0eXBlXT0mZmlsdGVyW2JfaWRdPSZmaWx0ZXJbbWluX2J3X29wcF09MCZmaWx0ZXJbbWF4X2J3X29wcF09MCZmaWx0ZXJbbWluX2dfb3BwXT0wJmZpbHRlclttYXhfZ19vcHBdPTAmZmlsdGVyW2tleXdvcmRzXT0mcGFnZT0y"
data = json.dumps(scrapDetail(url),indent=4, sort_keys=True, default=str)

# print (data)

with open('dewaele.json','w') as f:
    f.write(data)