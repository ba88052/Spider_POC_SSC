import scrapy
import time
import logging
import pandas as pd
import sys
from tqdm import tqdm
from Spider_POC_SSC.items import SpiderPocSscFinanceInfoItem
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent


class CompanyFinanceSpider(scrapy.Spider):
    name = "ssc_company_finance"

    #---------------設定Selenium----------------# 
    def __init__(self, first_page = 1, max_page = 0):
        self.first_page = first_page
        self.max_page = max_page
        options = Options()
        user_agent = UserAgent().google #目前fake agent很容易產生不支援的瀏覽器，還需調整
        options.add_argument(f"user-agent= Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36")
        options.add_argument("--disable-notifications")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--safebrowsing-disable-download-protection")
        options.add_argument('--headless')
        self.driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=options)
        self.wait = WebDriverWait(self.driver, 60)

    #---------------開啟Selenium----------------#
    def start_requests(self):
        self.driver.get("https://congbothongtin.ssc.gov.vn/faces/NewsSearch")
        if self.max_page < 1 :
            self.max_page = int(self.wait.until(EC.visibility_of_element_located((By.ID,"pt9:t1::nb_pg56265"))).text) #需修改，因id會變
        if self.first_page == 0:
            self.first_page = self.max_page
            print("max page:", self.max_page)
        yield scrapy.Request(url="https://www.google.com.tw", callback=self.get_company_finance_data)
        
    #---------------Selenium進入頁面後的調整----------------#
    def get_company_finance_data(self, response):
        self.SPIDER_POC_SSC_FINANCE_INFO_ITEM =  SpiderPocSscFinanceInfoItem()
        #用來儲存回傳資料
        for page in tqdm(range(self.first_page, self.max_page+1), position=1):
            for link in tqdm(range(15), position=0):
                self.wait_until_done()
                self.go_to_page(page)
                time.sleep(5)
                retry_count = 0
                max_retries = 5
                while retry_count < max_retries:
                    try:
                        self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'xgl')))
                        report_links = self.driver.find_elements(By.CLASS_NAME, 'xgl')
                        report_name = report_links[link].text
                        report_links[link].click()
                        break
                    except:
                        retry_count =+ 1
                        logging.warning(f"Error occurred: Search Wrong Retry Times#{retry_count}")
                        time.sleep(2)
                        continue      
                if retry_count == max_retries:
                    logging.error(f"Error occurred: Retry Enough Times")
                    self.driver.quit()
                    sys.exit()
                #儲存公司名稱                            
                company_name, company_MDN = self.get_company_name_MDN()
                #儲存年份與季度(如果季度不存在則為0，表示為半年或年報
                year, quarter = self.get_year_quarter()
                #抓取報表資料
                self.get_report_data(year=year, quarter=quarter, report_name = report_name, company_name=company_name, company_MDN=company_MDN)
                yield self.SPIDER_POC_SSC_FINANCE_INFO_ITEM
                self.driver.back()
        self.driver.quit()
        
    
    #---------------用來等待頁面載入完成----------------#
    def wait_until_done(self):
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    #---------------進入指定頁面----------------#
    def go_to_page(self, page):
        target_page_element = self.wait.until(EC.visibility_of_element_located((By.ID,"pt9:t1::nb_in_pg")))
        page_column = target_page_element.get_attribute("value")
        while page_column != f"{page}":
            target_page_element.clear()
            target_page_element.send_keys(page)
            target_page_element.send_keys(Keys.RETURN)
            time.sleep(2)
            target_page_element = self.wait.until(EC.visibility_of_element_located((By.ID,"pt9:t1::nb_in_pg")))
            page_column = target_page_element.get_attribute("value")
            
    #---------------拿到公司名稱和MDN----------------#
    def get_company_name_MDN(self):
        self.wait_until_done()
        self.wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="pt2:t2:0:c3"]/span/span')))
        company_name = self.driver.find_element(By.XPATH, '//*[@id="pt2:plam3"]/tbody/tr/td[2]').text
        company_MDN = self.driver.find_element(By.XPATH,'//*[@id="pt2:plam1"]/tbody/tr/td[2]').text
        self.SPIDER_POC_SSC_FINANCE_INFO_ITEM['COMPANY_NAME'] = company_name
        self.SPIDER_POC_SSC_FINANCE_INFO_ITEM['COMPANY_MDN'] = company_MDN
        return(company_name, company_MDN)

    #---------------拿到Year和Quarter----------------#
    def get_year_quarter(self):
        year_quarter = self.driver.find_elements(By.CLASS_NAME, "xer")
        year_quarter_li = []
        for num in year_quarter:
            if num.text:
                year_quarter_li.append(num.text)

        year = year_quarter_li[0]
        try:
            quarter = year_quarter_li[1]
        except:
            quarter = ""
        return(year, quarter)
    
    #---------------拿到所有report data----------------#
    def get_report_data(self, year, quarter, report_name, company_name, company_MDN):
        report_name = f"{year}_{quarter}_{report_name}"
        self.SPIDER_POC_SSC_FINANCE_INFO_ITEM['REPORT_NAME'] = report_name
        table_names = ["REPORT_BCDKT", "REPORT_KQKD", "REPORT_LCTT_TT", "REPORT_LCTT_GT"]
        for tab_num, table_name in zip(range(1, 5), table_names):
            table_link = self.wait.until(EC.element_to_be_clickable((By.ID, f'pt2:tab{tab_num}::disAcr')))
            time.sleep(2)
            table_link.click()
            economic_infor_report_data = self.wait.until(EC.visibility_of_element_located((By.ID, f'pt2:tab{tab_num}::body'))).get_attribute('innerHTML')
            economic_infor_report_headers = [header.get_attribute('innerHTML') for header in self.driver.find_elements(By.CLASS_NAME, ("x1h1"))]
            economic_infor_report_df = pd.read_html(economic_infor_report_data)[1]
            economic_infor_report_df.columns = economic_infor_report_headers
            self.SPIDER_POC_SSC_FINANCE_INFO_ITEM[table_name] = economic_infor_report_df.to_json()

