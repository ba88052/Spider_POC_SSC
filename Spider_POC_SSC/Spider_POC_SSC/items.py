# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class SpiderPocSscCompanyInfoItem(scrapy.Item):
    COMPANY_NAME = scrapy.Field()
    COMPANY_MDN = scrapy.Field()
    COMPANY_GENERAL_INFO = scrapy.Field()
    COMPANY_NNB_NNQ_SHAREHOLDERS_DATA = scrapy.Field()

class SpiderPocSscFinanceInfoItem(scrapy.Item):
    COMPANY_NAME = scrapy.Field()
    COMPANY_MDN = scrapy.Field()
    REPORT_NAME = scrapy.Field()
    REPORT_BCDKT = scrapy.Field()
    REPORT_KQKD = scrapy.Field()
    REPORT_LCTT_TT = scrapy.Field()
    REPORT_LCTT_GT = scrapy.Field()


