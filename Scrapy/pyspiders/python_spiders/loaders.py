import re
from scrapy.loader import ItemLoader
from itemloaders.processors import Join, MapCompose, TakeFirst, Identity
from .items import ListingItem
from .helper import square_meters_extract, extract_number_only

def filter_empty(_s):
    return _s or None

def get_int(value):
    # value = extract_number_only(value)
    return int(re.sub("\D", "", value))

class ListingLoader(ItemLoader):
    default_item_class = ListingItem
    # default_input_processor = MapCompose()
    default_output_processor = TakeFirst()

    description_in = MapCompose(str.strip, filter_empty)
    description_out = Join(' ')

    rent_in = MapCompose(get_int)
    room_count_in = MapCompose(get_int)
    square_meters_in = MapCompose(square_meters_extract, get_int)
    utilities_in = MapCompose(get_int)
    deposit_in = MapCompose(get_int)
    heating_cost_in = MapCompose(get_int)
    water_cost_in = MapCompose(get_int)
    prepaid_rent_in = MapCompose(get_int)

    furnished_in = Identity()
    floor_in = Identity()
    parking_in = Identity()
    elevator_in = Identity()
    terrace_in = Identity()
    swimming_pool_in = Identity()
    washing_machine_in = Identity()
    dishwasher_in = Identity()
    pets_allowed_in = Identity()
    property_type_in = Identity()

    images_out = Identity()
    floor_plan_images_out = Identity()
    external_link_out = TakeFirst()
    external_source_out = Join()
    address_out = Join()
    city_out = Join()
    zipcode_out = Join()
    rent_string_out = Join()

    def __init__(self, response):
        super(ListingLoader, self).__init__(response=response)
        self.images_in = MapCompose(response.urljoin)
