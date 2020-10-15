import scrapy


class RevaBaseSpider(scrapy.Spider):
    name = 'reva_base_spider'
    allowed_domains = ['abc.com']
    start_urls = ['http://abc.com/']
    execution_type = 'testing'
    country = 'belgium'
    locale ='fr'

    def parse(self, response):
        pass
