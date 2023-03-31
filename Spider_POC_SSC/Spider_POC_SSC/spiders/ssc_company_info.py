import os
import re
import sys
import json
import time
import scrapy
import random
import logging
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from Spider_POC_SSC.items import SpiderPocSscCompanyInfoItem
from selenium.webdriver.support import expected_conditions as EC


today = datetime.today().date()
today = today.strftime("%m%d")

class CompanyInfoSpider(scrapy.Spider):
    name = "ssc_company_info"
    bq_table_name = f'company_info_{today}'
    #---------------設定Selenium----------------#
    def __init__(self, first_page = 1, max_page = 0, *args, **kwargs):
        #設定參數
        super(CompanyInfoSpider, self).__init__(*args, **kwargs)
        self.first_page = int(first_page)
        self.max_page = int(max_page)
        #調整預設下載處
        self.current_dir = os.path.dirname(os.path.abspath('__file__'))
        download_directory = self.current_dir+'/SSC_Company_Data'
        if not os.path.exists(download_directory):
            os.makedirs(download_directory)
        self.download_directory = download_directory
        logging.info(f"File will be download to:{download_directory}")
        #設定selenium
        prefs = {'download.prompt_for_download': False,
                'download.directory_upgrade': True,
                'safebrowsing.enabled': True}
        options = Options()
        options.add_argument(f"user-agent= {self.generate_user_agent()}")
        options.add_argument("--disable-notifications")
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--headless')
        options.add_argument("--start-maximized")
        options.add_experimental_option('prefs', prefs)       
        self.driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=options)
        self.wait = WebDriverWait(self.driver, 30)

    #---------------設定User_Agent----------------# 
    def generate_user_agent(self):
        with open('user_agents.json', 'r') as f:
            user_agents = json.load(f) 

        return random.choice(user_agents)
        
    #---------------開啟Selenium----------------#
    def start_requests(self):
        self.driver.get("https://congbothongtin.ssc.gov.vn/faces/CompanyProfilesSearch")
        if self.max_page < 1 :
            self.max_page = self.wait.until(EC.visibility_of_element_located((By.XPATH,'//*[@id="pt2:resId1::nb_cnt"]/tbody/tr/td[3]'))).text
            self.max_page = int(re.findall('\d+', self.max_page)[0])
        if self.first_page == 0:
            self.first_page = self.max_page
        logging.info(f"First page:{self.first_page}, Max page:{self.max_page}")
        yield scrapy.Request(url="https://www.google.com.tw", callback=self.parse)

    #---------------Selenium進入頁面後的調整----------------#
    def parse(self, response):
        if self.first_page == 0:
            self.first_page = self.max_page
        SPIDE_RPOC_SSC_COMPANY_INFO_ITEM =  SpiderPocSscCompanyInfoItem()
        for page in tqdm(range(self.first_page, self.max_page+1), position = 1):
            for link in tqdm(range(20), position = 0):
                self.wait_until_done()
                self.go_to_page(page)
                self.wait_until_done()
                time.sleep(10)
                retry_count = 0
                max_retries = 5
                while retry_count < max_retries:
                    company_links = self.driver.find_elements(By.CLASS_NAME, 'xgl')
                    try:
                        company_name = company_links[link].text
                        company_links[link].click()
                        logging.info(f"Click Link page:{page}, link: {link}")
                        company_MDN = self.wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="plam2"]/td[2]/span'))).text
                        break
                    except:
                        retry_count += 1
                        logging.warning(f"Error occurred: Search Wrong Retry Times#{retry_count}")
                        continue
                    
                if retry_count == max_retries:
                    logging.error(f"Error occurred: Retry Enough Times")
                    self.driver.quit()
                    sys.exit()
                    # print(company_MDN, company_name)
                SPIDE_RPOC_SSC_COMPANY_INFO_ITEM["COMPANY_MDN"] = str(company_MDN)
                SPIDE_RPOC_SSC_COMPANY_INFO_ITEM["COMPANY_NAME"] = str(company_name)
                
                # 下載第一頁資料
                logging.info(f"Get First Data page:{page}, link: {link}")
                SPIDE_RPOC_SSC_COMPANY_INFO_ITEM["COMPANY_GENERAL_INFO"] = str(self.get_first_data(company_name))
                # SPIDE_RPOC_SSC_COMPANY_INFO_ITEM["COMPANY_GENERAL_INFO"] = str(1)

                # print("First page")
                
                # 下載第二頁資料
                logging.info(f"Get Second Data page:{page}, link: {link}")
                SPIDE_RPOC_SSC_COMPANY_INFO_ITEM["COMPANY_NNB_NNQ_SHAREHOLDERS_DATA"] = str(self.get_second_data())
                # SPIDE_RPOC_SSC_COMPANY_INFO_ITEM["COMPANY_NNB_NNQ_SHAREHOLDERS_DATA"] = str(2)
                # print("Second page")
                self.driver.back()

                yield SPIDE_RPOC_SSC_COMPANY_INFO_ITEM
        self.driver.quit()

    #---------------用來等待頁面載入完成----------------#
    def wait_until_done(self):
        self.wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        self.wait.until(lambda browser: browser.execute_script('return document.readyState') == 'complete')
    
    #---------------進入指定頁面----------------#
    def go_to_page(self, page):
        target_page_element = self.wait.until(EC.visibility_of_element_located((By.ID,"pt2:resId1::nb_in_pg")))
        page_column = target_page_element.get_attribute("value")
        while page_column != f"{page}":
            target_page_element.clear()
            target_page_element.send_keys(page)
            target_page_element.send_keys(Keys.RETURN)
            self.driver.implicitly_wait(2)
            target_page_element = self.wait.until(EC.visibility_of_element_located((By.ID,"pt2:resId1::nb_in_pg")))
            page_column = target_page_element.get_attribute("value")
        
    #---------------下載第一頁資料----------------#
    def get_first_data(self, company_name):
        self.wait_until_done()
        download_button =  self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="r1:0:b4"]/a')))
        download_button.click()
        t = 0
        # print(self.download_directory)
        while not os.path.isfile(f"{self.current_dir}/ThongTinHoSo.xls") or t>120:
            self.driver.implicitly_wait(2)
            t += 1
        if os.path.isfile(f"{self.current_dir}/ThongTinHoSo.xls"):
            os.rename(f"{self.current_dir}/ThongTinHoSo.xls", f"{self.download_directory}/{company_name}_general_info.xls")
            COMPANY_GENERAL_INFO_DF = pd.read_excel(f"{self.download_directory}/{company_name}_general_info.xls")
            COMPANY_GENERAL_INFO_DF = COMPANY_GENERAL_INFO_DF.to_json(orient="records")
            return COMPANY_GENERAL_INFO_DF
        else:
            raise ValueError("%s isn't a file!" % self.download_directory)
            
    #---------------下載第二頁資料----------------#
    def get_second_data(self):
        self.wait_until_done()
        second_page = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="tab4::disAcr"]')))
        second_page.click()
        NNB_NNQ_SHAREHOLDERS_DATA = {}
        table_names = ["insiders", "people_involved", "founding_shareholders", "major_shareholders"]
        for pd_num, table_name in zip(range(1,5), table_names):
            NNB_NNQ_SHAREHOLDERS = self.wait.until(EC.visibility_of_element_located((By.ID, f'pb{pd_num}'))).get_attribute('innerHTML')
            NNB_NNQ_SHAREHOLDERS_DF = pd.read_html(NNB_NNQ_SHAREHOLDERS)
            try:
                NNB_NNQ_SHAREHOLDERS_DATA[table_name] = NNB_NNQ_SHAREHOLDERS_DF[2].to_json(orient="records")
            except:
                NNB_NNQ_SHAREHOLDERS_DATA[table_name] = None
        return json.dumps(NNB_NNQ_SHAREHOLDERS_DATA)