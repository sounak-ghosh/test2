# -*- coding: utf-8 -*-
# Author: Mitesh Pandav/Sounak Ghosh
import scrapy
import js2xml
from ..helper import currency_parser, extract_number_only, remove_white_spaces, remove_unicode_char, format_date
from ..items import ListingItem


def check_if_available(input_string):
    if 'oui' in input_string.lower():
        return True
    else:
        return False

def extract_city_zip(_address):
    _address = remove_white_spaces(_address)
    if len(_address.split(" - ")) > 1:
        zip_city = _address.split(" - ")[1]
        zipcode = zip_city.split(" ")[0]
        city = ' '.join(zip_city.split(" ")[1:])
        return zipcode, city
    return None, None

class ImmobalcaenSpider(scrapy.Spider):
    """ website_name """
    name = 'Immobalcaen_PySpider_belgium_fr'
    allowed_domains = ['immobalcaen.com', 'immobalcaen.be']
    start_urls = ['https://www.immobalcaen.be/fr/List/PartialListEstate?EstatesList=System.Collections.Generic.List%601%5BWebulous.Immo.DD.WEntities.Estate%5D&EstateListForNavigation=System.Collections.Generic.List%601%5BWebulous.Immo.DD.WEntities.Estate%5D&SelectedType=System.Collections.Generic.List%601%5BSystem.String%5D&Categories=System.Collections.Generic.List%601%5BSystem.Web.Mvc.SelectListItem%5D&ListID=7&SearchType=ToRent&SearchTypeIntValue=0&Cities=System.Collections.Generic.List%601%5BSystem.Web.Mvc.SelectListItem%5D&SelectedRegion=0&Regions=System.Collections.Generic.List%601%5BSystem.Web.Mvc.SelectListItem%5D&SortParameter=Category&Furnished=False&InvestmentEstate=False&NewProjects=False&CurrentPage=0&MaxPage=0&EstateCount=2&SoldEstates=False&RemoveSoldRentedOptionEstates=False&List=Webulous.Immo.DD.CMSEntities.EstateListContentObject&Page=Webulous.Immo.DD.CMSEntities.Page&ContentZones=System.Collections.Generic.List%601%5BWebulous.Immo.DD.CMSEntities.ContentZone%5D&DisplayMap=False&MapMarkers=System.Collections.Generic.List%601%5BWebulous.Immo.DD.WEntities.MapMarker%5D&MapZipMarkers=System.Collections.Generic.List%601%5BWebulous.Immo.DD.WEntities.MapZipMarker%5D&EstateTotalCount=0&isMobileDevice=False&Countries=System.Collections.Generic.List%601%5BSystem.Web.Mvc.SelectListItem%5D&CountrySearch=Undefined']
    position = 0
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'

    def parse(self, response):
        listings = response.xpath(".//div[@class='estate-list__item']//a[@class='estate-card']/@href").extract()
        for property_url in listings:
            yield scrapy.Request(
                url=response.urljoin(property_url),
                callback=self.get_details,
                meta={'property_type': response.meta.get('property_type')}
            )

    def get_details(self, response):
        self.position += 1
        external_link = response.url
        title = ''.join(response.xpath(".//h1//text()").extract())
        room_count = ''.join(response.xpath(".//tr[contains(th//text(), 'Nombre de chambres')]//td//text()").extract())
        square_meters = ''.join(response.xpath(".//tr[contains(th//text(), 'Surface habitable')]//td//text()").extract())
        bathroom_count = ''.join(response.xpath("//th[contains(text(),'Nombre de salle de bain')]/following-sibling::td/text()").extract())
        available_date = ''.join(response.xpath(".//tr[contains(th//text(), 'Disponibilité')]//td//text()").extract())
        parking = ''.join(response.xpath(".//tr[contains(th//text(), 'Parking')]//td//text()").extract())
        terrace = ''.join(response.xpath(".//tr[contains(th//text(), 'Terrasse')]//td//text()").extract())
        furnished = ''.join(response.xpath(".//tr[contains(th//text(), 'Meublé')]//td//text()").extract())
        external_id = ''.join(response.xpath(".//tr[contains(th//text(), 'Référence')]//td//text()").extract())
        dishwasher = ''.join(response.xpath(".//tr[contains(th//text(), 'Lave-vaisselle')]//td//text()").extract())
        elevator = ''.join(response.xpath(".//tr[contains(th//text(), 'Ascenseur')]//td//text()").extract())
        landlord_phone = ''.join(response.xpath(".//div[contains(@class, 'box-affix__container')]//a[contains(@href, 'tel:')]//@href").extract())
        landlord_phone = landlord_phone.strip("tel:")
        property_type = response.meta.get('property_type')
        address = ''.join(response.xpath(".//h3[contains(.//text(), 'Adresse')]/following-sibling::p[1]//text()").extract())
        description = ''.join(response.xpath(".//h2[contains(.//text(), 'Description')]/following-sibling::p[1]//text()").extract())
        zipcode, city = extract_city_zip(address)
        rent = remove_white_spaces(title).split(' - ')[-1]
        js_code = response.xpath(".//script[contains(.//text(), 'myLatLng')]//text()").extract_first()
        parsed_js = js2xml.parse(js_code)
        latitude = parsed_js.xpath(".//var[@name='myLatLng']/following-sibling::assign[1]//number[1]/@value")[0]
        longitude = parsed_js.xpath(".//var[@name='myLatLng']/following-sibling::assign[1]//number[2]/@value")[0]
        landlord_name = 'Immo Balcaen'
        landlord_email = 'info@immobalcaen.be'
        images = response.xpath(".//div[contains(@class, 'estate-detail-carousel__body')]//a/@href").extract()
        utilities = ''.join(response.xpath("//th[contains(text(),'Charges (€) (montant)')]/following-sibling::td/text()").extract())


        item = ListingItem()
        item['external_source'] = "Immobalcaen_PySpider_belgium_fr"
        item['images'] = images
        item['external_link'] = external_link
        item['external_id'] = external_id
        item['title'] = remove_white_spaces(title)
        item['zipcode'] = title.split('-')[2].split(' ')[0]
        item['city'] = title.split('-')[2].replace(item['zipcode'],'').strip()
        if utilities:
            item['utilities'] = int(utilities)
        if bathroom_count:
            item['bathroom_count'] =   int(extract_number_only(bathroom_count))
        if room_count:
            item['room_count'] = extract_number_only(room_count)
        if square_meters:
            item['square_meters'] = extract_number_only(remove_unicode_char(square_meters))
        if available_date and available_date!='immédiatement':
            item['available_date'] = format_date(available_date, '%d/%m/%Y')
        if parking:
            item['parking'] = check_if_available(parking)
        if terrace:
            item['terrace'] = check_if_available(terrace)
        if furnished:
            item['furnished'] = check_if_available(furnished)
        if dishwasher:
            item['dishwasher'] = check_if_available(dishwasher)
        if elevator:
            item['elevator'] = check_if_available(elevator)
        item['landlord_phone'] = remove_white_spaces(landlord_phone)
        item['landlord_email'] = landlord_email
        item['landlord_name'] = landlord_name
        item['address'] = remove_white_spaces(address)
        item['description'] = remove_white_spaces(description)
        item['city'] = city
        item['zipcode'] = zipcode
        item['property_type'] = property_type
        item['position'] = self.position
        item['latitude'] = latitude
        item['longitude'] = longitude
        if rent:
            item['rent'] = extract_number_only(remove_unicode_char(rent))
            item['currency'] = currency_parser(rent)
        if item.get('rent', None):
            item['rent'] = int(item['rent']) if item['rent'].isdigit() else None
        if item.get('room_count', None):
            item['room_count'] = int(item['room_count']) if item['room_count'].isdigit() else None
        if item.get('square_meters', None):
            item['square_meters'] = int(item['square_meters']) if item['square_meters'].isdigit() else None
        if 'appartement' in title.lower():
            item['property_type'] = 'apartment'
            yield item
        elif 'maison' in title.lower() or 'Villa' in title.lower():
            item['property_type'] = 'house'
            yield item