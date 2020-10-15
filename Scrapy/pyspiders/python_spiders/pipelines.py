# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import copy
import requests
from scrapy.utils.project import get_project_settings
from scrapy.exceptions import NotSupported
from .helper import string_found, extract_rent_currency


def filter_null_objects(_item):
    _new_item = copy.deepcopy(_item)
    for key in _item:
        if not _item[key]:
            del _new_item[key]
    return _new_item


def call_reva_api(_json, _country, _locale, _extraction_type):
    settings = get_project_settings()
    headers = {'X-Report-Formats': 'summary+attributewise_error_summary+error_details+missing_values',
               'X-Country': _country,
               'X-Locale': _locale}
    if _extraction_type == 'production':
        base_url = "{}/api/spiders/process_data".format(settings.get('API_ENDPOINT'))
        response = requests.post(base_url, headers=headers, json=_json)
    else:
        base_url = "{}/api/spiders/validate".format(settings.get('API_ENDPOINT'))
        response = requests.post(base_url, headers=headers, json=_json)
        print(response.content.decode('utf-8'))
    return response


class PythonSpidersPipeline:
    all_items = []

    def open_spider(self, spider):
        self.all_items = []

    def close_spider(self, spider):
        print("Inside Closing spider")
        # api_response = call_reva_api(self.all_items, spider.country, spider.locale, spider.execution_type)
        if self.all_items:
            for idx in range(0, len(self.all_items), 50):
                api_response = call_reva_api(self.all_items[idx:idx + 50], spider.country, spider.locale, spider.execution_type)
                if api_response.status_code == 200:
                    spider.log('Response from validation API {}'.format(api_response.content.decode('utf-8')))
                else:
                    raise NotSupported("Error while calling API Response-code: {}, response-body: {}".format(
                        api_response.status_code, api_response.content.decode('utf-8')))
        else:
            spider.log('No items')

    def process_item(self, item, spider):
        images = item.get('images', None)
        description = item.get('description', None)
        rent_string = item.get('rent_string', None)
        if images:
            item['external_images_count'] = len(item['images'])
        if description:
            if string_found(['parking', 'parkeerplaats'], description):
                item['parking'] = True
            if string_found(['balcon'], description):
                item['balcony'] = True
            if string_found(['ascenseur'], description):
                item['elevator'] = True
            if string_found(['terrasse', 'terrace'], description):
                item['terrace'] = True
            if string_found(['dishwasher'], description):
                item['dishwasher'] = True
        if rent_string:
            rent, currency = extract_rent_currency(rent_string)
            item['rent'] = rent
            item['currency'] = currency
            del item['rent_string']
        new_item = filter_null_objects(item)
        self.all_items.append(dict(new_item))
        return item
