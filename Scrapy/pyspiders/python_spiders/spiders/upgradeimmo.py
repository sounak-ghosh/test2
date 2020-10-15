import scrapy
import js2xml
from ..loaders import ListingLoader
from python_spiders.helper import remove_unicode_char, extract_rent_currency, format_date

def extract_city_zipcode(_address):
    zip_city = _address.split(", ")[1]
    zipcode, city = zip_city.split(" ")
    return zipcode, city


class UpgradeimmoSpider(scrapy.Spider):
    name = 'upgradeimmo'
    allowed_domains = ['upgradeimmo.be']
    start_urls = ['http://upgradeimmo.be/']
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'

    def start_requests(self):
        start_urls = [
            {'url': 'https://www.upgradeimmo.be/fr/a-louer/appartements',
                'property_type': 'apartment'}
        ]
        for url in start_urls:
            yield scrapy.Request(url=url.get('url'),
                                 callback=self.parse,
                                 meta={'property_type': url.get('property_type')})

    def parse(self, response, **kwargs):
        listings = response.xpath(
            ".//div[@class='property-list']/div[@class='property']")
        for property_item in listings:
            property_url = response.urljoin(property_item.xpath(
                ".//div[@class='meet_info button-link']/a/@href").extract_first())
            yield scrapy.Request(
                url=property_url,
                callback=self.get_property_details,
                meta={'property_type': response.meta.get('property_type')}
            )

        next_page_url = response.xpath(
            ".//div[@class='paging']//a[contains(@class, 'next')]/@href").extract_first()
        if next_page_url:
            yield scrapy.Request(
                url=response.urljoin(next_page_url),
                callback=self.parse,
                meta={'property_type': response.meta.get('property_type')}
                )

    def get_property_details(self, response):
        external_link = response.url
        property_type = response.meta.get('property_type')
        available_date = ''.join(response.xpath(".//div[contains(.//text(), 'Date de disponibilité')]/following-sibling::div[2]//text()").extract())
        furnished = ''.join(response.xpath(".//div[contains(.//text(), 'Meublé')]/following-sibling::div[2]//text()").extract())
        terrace = ''.join(response.xpath(".//div[contains(.//text(), 'Terrasse')]/following-sibling::div[2]//text()").extract())
        address = ''.join(response.xpath(".//div[@class='top-title']//div[@class='fleft']//text()").extract())
        zipcode, city = extract_city_zipcode(address)

        item_loader = ListingLoader(response=response)
        item_loader.add_value('external_source', "Upgradeimmo_PySpider_belgium_fr")
        item_loader.add_value('property_type', property_type)
        item_loader.add_value('external_link', external_link)
        item_loader.add_xpath('address', ".//div[@class='top-title']//div[@class='fleft']//text()")
        item_loader.add_xpath('rent_string', ".//div[@class='top-title']//div[@class='fright']//text()")
        item_loader.add_xpath('description', ".//div[contains(text(), 'Description')]/following-sibling::div[1]//text()")
        item_loader.add_xpath('square_meters', ".//div[contains(.//text(), 'Superficie totale')]/following-sibling::div[2]//text()")
        if available_date:
            item_loader.add_value('available_date', format_date(available_date))
        item_loader.add_xpath('floor', ".//div[contains(.//text(), 'Etage') and not(contains(.//dt//text(), 'Nombre d’etage'))]/following-sibling::div[2]//text()")
        item_loader.add_xpath('images', ".//div[@id='Photos']//li/a/@href")
        if furnished:
            item_loader.add_value('furnished', True)
        if terrace:
            item_loader.add_value('terrace', True)
        js_code = response.xpath("//script[contains(., 'mymap.setView')]/text()").extract_first()
        parsed_js = js2xml.parse(js_code)
        latitude = parsed_js.xpath("//var[@name='marker']//number[1]//@value")
        longitude = parsed_js.xpath("//var[@name='marker']//number[2]//@value")
        if latitude:
            item_loader.add_value('latitude', latitude[0])
        if longitude:
            item_loader.add_value('longitude', longitude[0])
        item_loader.add_xpath('room_count', ".//div[contains(.//text(), 'Nombre de Chambre(s)')]/following-sibling::div[2]//text()")
        item_loader.add_value('landlord_name', 'Upgrade IMMO')
        item_loader.add_value('landlord_email', 'info@upgradeimmo.be')
        item_loader.add_value('landlord_phone', '02 / 673.95.64')
        item_loader.add_value('zipcode', zipcode)
        item_loader.add_value('city', city)
        yield item_loader.load_item()
