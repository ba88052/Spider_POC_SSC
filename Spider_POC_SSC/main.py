import subprocess
import threading
import argparse
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout

def generate_page_ranges(first_page, max_page, num_threads):
    page_range_size = (max_page - first_page + 1) // num_threads
    page_ranges = []
    for i in range(num_threads):
        start_page = first_page + i * page_range_size
        end_page = first_page + (i+1) * page_range_size - 1
        if i == num_threads-1:
            end_page = max_page
        page_ranges.append((start_page, end_page))
    return page_ranges

def set_selenium():
    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--safebrowsing-disable-download-protection")
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    return(driver)

def get_max_page_company_info():
    url = "https://congbothongtin.ssc.gov.vn/faces/CompanyProfilesSearch"
    driver = set_selenium()
    wait = WebDriverWait(driver, 30)
    driver.get(url)
    max_page = wait.until(EC.visibility_of_element_located((By.XPATH,'//*[@id="pt2:resId1::nb_cnt"]/tbody/tr/td[3]'))).text
    max_page = int(re.findall('\d+', max_page)[0])
    driver.quit()
    return max_page

def get_max_page_company_finance():
    url = "https://congbothongtin.ssc.gov.vn/faces/NewsSearch"
    driver = set_selenium()
    wait = WebDriverWait(driver, 30)
    driver.get(url)
    max_page = wait.until(EC.visibility_of_element_located((By.XPATH,'//*[@id="pt9:t1::nb_cnt"]/tbody/tr/td[3]'))).text
    max_page = int(re.findall('\d+', max_page)[0])
    driver.quit()
    return max_page

if __name__ == '__main__':
#---------------從指令設定start_year和end_year---------------#
    parser = argparse.ArgumentParser()
    parser.add_argument('--first_page', default="1", type=str, help='Setting searching first page.')
    parser.add_argument('--max_page', default="0", type=str, help='Setting searching max page.')
    parser.add_argument('--mode', type=str, help='company_info=0 or company_finance=1')
    args = parser.parse_args()
    first_page = int(args.first_page)
    max_page = int(args.max_page)
    mode = int(args.mode)
    commands = []
    threads = []
#---------------設計多執行緒下指令---------------#
    if mode == 0:
        if max_page == 0:
            max_page = get_max_page_company_info()
        for page_ranges in generate_page_ranges(first_page, max_page, 3):
            commands.append(['scrapy', 'crawl', 'ssc_company_info', '-a', f'first_page={page_ranges[0]}', '-a', f'max_page={page_ranges[1]}'])
    elif mode == 1:
        if max_page == 0:
            max_page = get_max_page_company_finance()
        for page_ranges in generate_page_ranges(first_page, max_page, 3):
            commands.append(['scrapy', 'crawl', 'ssc_company_finance', '-a', f'first_page={page_ranges[0]}', '-a', f'max_page={page_ranges[1]}'])
#---------------啟動多執行緒---------------#
    for command in commands:
        t = threading.Thread(target=run_command, args=(command,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()