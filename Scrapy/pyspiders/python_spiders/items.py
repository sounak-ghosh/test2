# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class ListingItem(scrapy.Item):
    external_source = scrapy.Field() # required
    external_link = scrapy.Field() # required
    external_id = scrapy.Field()
    address = scrapy.Field() # required
    title = scrapy.Field()
    description = scrapy.Field()
    property_type = scrapy.Field() # required
    square_meters = scrapy.Field() # required
    room_count = scrapy.Field()
    rent_string = scrapy.Field()
    rent = scrapy.Field()
    available_date = scrapy.Field()
    deposit = scrapy.Field()
    prepaid_rent = scrapy.Field()
    currency = scrapy.Field()
    images = scrapy.Field()
    floor_plan_images = scrapy.Field()
    external_images_count = scrapy.Field()

    city = scrapy.Field()
    zipcode = scrapy.Field()
    latitude = scrapy.Field()
    longitude = scrapy.Field()

    water_cost = scrapy.Field()
    heating_cost = scrapy.Field()
    energy_label = scrapy.Field()

    floor = scrapy.Field()
    utilities = scrapy.Field()
    pets_allowed = scrapy.Field()
    parking = scrapy.Field()
    balcony = scrapy.Field()
    furnished = scrapy.Field()
    elevator = scrapy.Field()
    terrace = scrapy.Field()
    swimming_pool = scrapy.Field()

    landlord_name = scrapy.Field()
    landlord_phone = scrapy.Field()
    landlord_email = scrapy.Field()
    position = scrapy.Field()
    dishwasher = scrapy.Field()
    washing_machine = scrapy.Field()

    bathroom_count = scrapy.Field()