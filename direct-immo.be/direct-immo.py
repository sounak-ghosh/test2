# -*- coding: utf-8 -*-
import ssl,requests,json,time,csv,random
import re
from bs4 import BeautifulSoup
import sys
from multiprocessing import Process, Pool
import random
import json
import os
from lxml.html import fromstring
from geopy.geocoders import Nominatim
import pandas as pd


FILE_NAME = "direct-immo"


headers={
	"upgrade-insecure-requests": "1",
	"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36"

}


def get_page_response(url,postmethod,data):
	# making a request here to the webpageoko
	Flag=True
	while Flag:
		try:
			session=requests.session()
			if postmethod == "get":
					response=session.get(url, headers=headers)
			if postmethod == "post":
					response=session.post(url, headers=headers,data=data)
			if response.status_code == 200 or response.status_code == 404:
				Flag=False
		except Exception as e:
			print(e)
	return response


def get_geo_location(soup,address):
	# Function for extracting geo coordinates 
	
	our_text = soup.get_text().split("mymap.setView([")[1].split(",")
	lat = our_text[0].strip()
	lon = our_text[1].replace(']','').strip()
		
	print("Longitude:",lat,"Latitude:",lon)		
	return lat,lon


def get_data(my_property,scraped_data):
	# function for scraping all required data
	url = my_property
	print(url)
	
	response = get_page_response(url,'get',None)
	ps = fromstring(response.text) 
	soup = BeautifulSoup(response.text,'lxml')
	
	tables = soup.find('div',class_='span4 panel-left').findAll('div',class_='field')
	for t in tables:
		if 'Adresse' in t.find('div',class_='name').get_text():
			scraped_data["address"] = t.find('div',class_='value').get_text()
		if 'Prix' 	in t.find('div',class_='name').get_text():
			scraped_data["rent"] = t.find('div',class_='value').get_text()
			scraped_data["rent"] = int(scraped_data["rent"].replace(u'€','').replace('.',''))
		if 'Nombre de Chambre' 	in t.find('div',class_='name').get_text():
			scraped_data["room_count"] = int(t.find('div',class_='value').get_text())
		if 'Superficie totale' in t.find('div',class_='name').get_text():
			square_meters = t.find('div',class_='value').get_text()
			scraped_data["square_meters"] = int(square_meters.replace(u'm²','').replace('.',''))
		if 'Nombre de salle(s) de bain' in t.find('div',class_='name').get_text():	
			bathroom_count = t.find('div',class_='value').get_text()
			scraped_data["bathroom_count"] = int(bathroom_count))
	
	# calling functions to get latitute and longitute data
	try:
		scraped_data["latitude"],scraped_data["longitude"] = get_geo_location(soup,scraped_data["address"])
	except Exception as e:
		print(e)

	scraped_data["external_link"] = url
	scraped_data["external_source"] = 'direct-immo.be'

	scraped_data["title"] = ps.xpath("//h3[@class='pull-left leftside']/text()")[0].strip()
	
	try:
		scraped_data["city"] = scraped_data["address"].split()[-1].strip()
	except:
		pass
	try:
		scraped_data["zipcode"] = scraped_data["address"].split()[-2].strip()
	except:
		pass
	
	
	

	scraped_data["landlord_name"] = 'Direct-immo'
	scraped_data["landlord_email"] = 'info@direct-immo.be'
	scraped_data["landlord_phone"] = '02.347.10.01'

	
	if 'garage' in soup.get_text().lower() or 'parking' in soup.get_text().lower():
		scraped_data["parking"] = True
	if 'balcony' in soup.get_text().lower():	
		scraped_data["balcony"] = True	
	if 'CHAMBRES MEUBLÉ' in soup.get_text().lower() or 'meublé' in soup.get_text().lower():
		scraped_data["furnished"] = True	
	if ' terrace' in soup.get_text().lower():	
		scraped_data.update({'terrace':True})
	if ' elevator' in soup.get_text().lower() or 'lift' in soup.get_text().lower():
		scraped_data.update({'elevator':True})
	if 	' swim' in soup.get_text().lower():
		scraped_data.update({'swimming_pool':True})
	

	description = ps.xpath("//div[@class='group-container span12']//div[@class='row-fluid']//div[@class='field']//text()")
	description = [x.strip() for x in description if x.strip()]	
	description = '\n'.join(description)
		
	scraped_data["description"] = description
	try:
		charge = soup.findAll('div',class_='group span6')
		chg = []
		for c in [charge[-1]]:
			if 'Charges' in c.get_text():
				c_value = c.findAll('div',class_='value')
				for cv in c_value:
					try:
						req_price = cv.get_text()
					except:
						continue	
					chg.append(req_price)
		
	except Exception as e:
		print(e)
	utilities = 0
	for each in chg:
		each_price = int(each.replace(u'€','').replace('.',''))
		utilities += each_price
		scraped_data['utilities'] = utilities	
			

	images = ps.xpath("//ul[@class='thumbnails']//img/@src")
	scraped_data["images"] = images
	scraped_data["external_images_count"] = len(scraped_data["images"])

	if 'appartement' in soup.get_text().lower():
		scraped_data['property_type'] = 'apartment'	
	elif 'commercial'	 in soup.get_text().lower():
		return None
	elif 'commerce' in soup.get_text().lower():
		return None	
	elif 'flat' in soup.get_text().lower():
		scraped_data['property_type'] = 'apartment'	
	else:
		return None

	return scraped_data
	

def get_all_property_links():
	# scraping property links and addresses
	all_properties = []
	url = 'https://www.direct-immo.be/fr/a-louer?view=list&page=1'
	print('getting all property links...')
	response = get_page_response(url,'get',None)	                 
	ps = fromstring(response.text) 
	property_urls = ps.xpath("//div[@class='image']/a/@href")
	
	
	for index, p in enumerate(property_urls):
		p = 'https://www.direct-immo.be'+p
		all_properties.append(p)
	
	while True:
		next_url = ps.xpath("//a[@class='nav next']/@href")
	
		if next_url:
			next_url = 'https://www.direct-immo.be'+next_url[0]
			response = get_page_response(next_url,'get',None)	                 
			ps = fromstring(response.text) 
			property_urls = ps.xpath("//div[@class='image']/a/@href")
			for index, p in enumerate(property_urls):
				p = 'https://www.direct-immo.be/'+p
				all_properties.append(p)
		else:
			break		


	return all_properties		




def main():
	# required dictionary
	scraped_data_all = {
		"external_link": "",
		"external_source": "",
		"title": "",
		"description": "",
		"images": "",
		"landlord_name": "",
		"landlord_phone": "",
		"landlord_email": "",
		"external_images_count": None,
		"currency":"EUR"
		}
	global json_list	
	json_list = []

	# calling get_all_property_links function first to scrape all required property links
	all_properties = get_all_property_links()
	print('property links extraction completed...')

	print("Starting data extraction...")
	#calling get data function to scrape required data from each links
	
	print(len(all_properties))
	for ind, each_property in enumerate(all_properties[0:5]):
		scraped_data = scraped_data_all.copy()
		
		json_object = get_data(each_property,scraped_data)
		print(json_object)
		if not json_object:
			continue
		json_list.append(json_object)	
  
	json_object = json.dumps(json_list,indent=4, sort_keys=True, default=str)
	with open("direct-immo.json", "w") as outfile: 
		outfile.write(json_object) 

if __name__ == "__main__":
	main()
  
