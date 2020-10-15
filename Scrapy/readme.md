# Code Guidelines

## Loaders

### Import
```
from ..loaders import ListingLoader
```

### Create  Object
```
item_loader = ListingLoader(response=response)
```

### Add Xpath
```
item_loader.add_xpath('address', ".//div[@class='top-title']//div[@class='fleft']//text()")
```
- there is no need to write `extract()` or `extract first()`

### Add value
```
item_loader.add_value('property_type', property_type)
```
- Use in case when you have to extract value, process, and then add to item

### Yield
```
yield item_loader.load_item()
```
- At the end of the code yield Object

## Start Requests

```
def start_requests(self):
    start_urls = [
        {'url': 'http://www.vastgoeddevos.be/te-huur?category=12&priceRange=&office=1&status=te+huur',
         'property_type': 'apartment'},
        {'url': 'http://www.vastgoeddevos.be/te-huur?category=12&priceRange=&office=2&status=te+huur',
         'property_type': 'apartment'},
        {'url': 'http://www.vastgoeddevos.be/te-huur?category=3&priceRange=&office=1&status=te+huur',
         'property_type': 'house'},
        {'url': 'http://www.vastgoeddevos.be/te-huur?category=3&priceRange=&office=2&status=te+huur',
         'property_type': 'house'},
    ]
    for url in start_urls:
        yield scrapy.Request(url=url.get('url'),
                             callback=self.parse,
                             meta={'property_type': url.get('property_type')})
def parse(self, response, **kwargs):
	property_type = response.meta.get('property_type')

```
- Use this code when you have differet url for Different Listing type, for accurate listing without parsing

## Rent extraction
- Simple add item object ['rent_string'] with rent and rent Symbol (make sure there is no extra data)
- From this string, rent and currency will be parsed automatically
```
item_loader.add_xpath('rent_string', ".//div[@class='top-title']//div[@class='fright']//text()")
```

## Date format
```
from python_spiders.helper import format_date
if available_date:
    item_loader.add_value('available_date', format_date(available_date, '%d/%m/%Y'))
```

### Note - you can refer to spider `upgradeimmo` for ideas

# Code practices

## Xpath

### Max 2 levels

- BAD

```
//div[contains(@class,'property-list')]//div[contains(@class,'span12 property')]/div[contains(@class,'pic')]//a/@href
```

- GOOD

```
//div[contains(@class,'property-list')]//div[contains(@class,'pic')]//a/@href
```

### Match single unique class
- BAD
```
//div[contains(@class,'span12 property')]
```
- GOOD
```
//div[contains(@class,'property')]
```

## Code
### Use helpers when possible

e.g. Cleanup inputs like trimming strings

- BAD
```
int(response.xpath('//span[@id="bdrms"]/text()').extract_first().strip().replace(' ','').replace('\n', ''))
```
- GOOD

Define a utility funciton to be reused

```
remove_white_spaces(response.xpath('//span[@id="bdrms"]/text()').extract_first())
```
- `remove_white_spaces` function is available as helper function

### Avoid using `try..catch`
- BAD
```
try:
  a = b.split(' ')[1]
except:
  pass
```
- GOOD

Validate/Check values before further operations

```
if len(b.split(' '))>1:
  a = b.split(' ')[1]
```

### Avoid clutters in spider file
- Add headers, user_agents etc in middlewares
- Create helpers for common utilities like string formating etc as helper functions

### Property mapping 
- A dictionary `property_type_lookup` added in helpers, you can add new mapping as required if not found. Must be reviewed by Mitesh/Mehmet/Amit
- Lookup will be done automatically at loaders py.

### Avoid using additional libraries.
List of approved libraries below

- Selenium
- js2xml

# Execution Instructions

## Setting up server

- `apt install python3-virtualenv libpython3.8-dev`
- `apt-get install build-essential`
- `export API_ENDPOINT="up-to-date-api-url"`

## Setting up virtual environment

- `virtualenv venv -p python3`
- `source venv/bin/activate`
- `pip install -r requirements.txt`

## check installation
- `scrapy list`

## spider execution
- `scrapy crawl [spider_name] --logfile=[spider_name] -o [spider_name].json`

## spider execution for production
- `scrapy crawl [spider_name] --logfile=[spider_name] -o [spider_name].json -a extraction_type=production`
