import scrapy
from scrapy.crawler import CrawlerProcess

class ExampleSpider(scrapy.Spider):
    name = "example"
    start_urls = ['https://example.com']

    def parse(self, response):
        yield {
            'title': response.css('title::text').get(),
            'url': response.url,
        }

def run_scrapy_spider():
    process = CrawlerProcess(settings={
        "FEEDS": {
            "output.json": {"format": "json"},
        },
    })
    process.crawl(ExampleSpider)
    process.start()
    with open('output.json') as f:
        return f.read()
