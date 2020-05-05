#-*- coding: utf-8 -*-
import datetime, time
import random
import re
import platform
import json
import pickle
import os
import csv
import logging

import dateutil.parser

from tqdm import tqdm
from urllib import parse 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

class Crawler:
    def __init__(self):
        if platform.system() == "Linux":
            self.driver_dir = './chromedriver' #for linux system
        else:
            self.driver_dir = 'chromedriver.exe' #for windows system

        logging.basicConfig(filename='./Log/crawler.log', level=logging.INFO)
        #Set log file path and logging level

        self.urlbase = "https://www.instagram.com/explore/tags/"
        self.posturl = "https://www.instagram.com/p/"
        self.login_url = "https://www.instagram.com/accounts/login/"

        self.station_list = []
        with open('station.csv','r', encoding='utf-8') as f:
            tmp = csv.reader(f)
            for name in tmp:
                self.station_list.append(name[0])

        self.suffix_list = ['']
        self.driver_setting()
        self.start_time = datetime.datetime.now()
        self.contents_db = dict()
        self.link_collection = set()
        self.batch_size = 100

        with open('path.json') as f:
            data = json.load(f)
            self.path = data['path']
            self.day_range = int(data['range'])

    def __del__(self):
        self.driver.close()
        self.driver_post.close()
    
    def login(self, driver):
        with open('account.json') as f:
            acc = json.load(f)
            my_id = acc['id']
            my_password = acc['password']

        driver.get(self.login_url)
        time.sleep(3)
        driver.find_element_by_xpath("//*[@id=\"react-root\"]/section/main/div/article/div/div[1]/div/form/div[2]/div/label/input").send_keys(my_id)
        driver.find_element_by_xpath("//*[@id=\"react-root\"]/section/main/div/article/div/div[1]/div/form/div[3]/div/label/input").send_keys(my_password)
        driver.find_element_by_xpath("//*[@id=\"react-root\"]/section/main/div/article/div/div[1]/div/form/div[4]/button").click()
        time.sleep(5)

    def driver_setting(self):   
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('window-size=1920x1080')
        options.add_argument('disable-gpu')
        options.add_argument('no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(self.driver_dir, chrome_options=options)
        self.driver.implicitly_wait(5) #setting implicitly waiting time

        self.driver_post = webdriver.Chrome(self.driver_dir, chrome_options=options)
        self.driver_post.implicitly_wait(5)
        logging.debug("Completed Chrome driver loading.")

    def link_loading(self, seed_url, batch_size = 100):
        logging.info('Link loading with batch size : %d' %(batch_size))
        self.link_collection = set()

        root_path = self.path['recent_post']
        linkcnt = 1

        while len(self.link_collection) < batch_size:
            new_post = False
            cnt = 0
            while True:
                cnt += 1
                tmp_url = root_path + '/div[' + str(cnt) + ']'
                try:
                    self.driver.find_element_by_xpath(tmp_url)
                except:
                    break
                for i in range(3):
                    cur_url = self.driver.find_element_by_xpath(tmp_url + '/div[' + str(i + 1) + ']/a').get_attribute('href')
                    cur_id = cur_url.split('/')[-2]
                    if cur_id not in self.link_collection and cur_id not in self.contents_db:
                        new_post = True
                        self.link_collection.add(cur_id)
                        #print('Find %dth new link : %s' % (linkcnt, cur_id))
                        linkcnt += 1
            if new_post == False:
                return False
            self.driver.find_element_by_tag_name('body').send_keys("webdriver" + Keys.PAGE_DOWN)
            self.driver.find_element_by_tag_name('body').send_keys("webdriver" + Keys.PAGE_DOWN)
            self.driver.find_element_by_tag_name('body').send_keys("webdriver" + Keys.PAGE_DOWN)
            time.sleep(3)
        return True
    
    def batch_crawling(self):
        time_flag = True
        for key in tqdm(self.link_collection):
            if self.single_crawling_bs4(key) == False:
                time_flag = False
        return time_flag
    
    def safe_post_data(self, path_name, attr = 'innerHTML'):
        waitcnt = 0
        while True:
            waitcnt += 1
            try:
                inner = self.driver_post.find_element_by_xpath(self.path[path_name]).get_attribute(attr)
                return inner
            except Exception as e:
                logging.error(e)
                time.sleep(0.5)
                if waitcnt > 10:
                    waitcnt = 0
                    self.driver_post.refresh()
                    time.sleep(5)

    def get_img_url(self):
        '''
        3 cases in image
            1. Single image - "in_post_single_img"
            2. Mutli image - "in_post_multi_img"
            3. Video thumbnail - "in_post_video_img"
        '''
        self.safe_post_data('in_post_content') #for element loading

        source = self.driver_post.find_element_by_xpath(self.path['in_post_common_img']).get_attribute('innerHTML')
        soup = BeautifulSoup(source, 'html.parser')
        
        if soup.find('video'):
            return None
        return soup.find('img')['src']
    
    def single_crawling(self, key):
        self.driver_post.get(self.posturl + key)

        data = dict()

        #get postdate
        data['date'] = dateutil.parser.parse(self.safe_post_data('in_post_date', 'datetime'))
        data['date'] += datetime.timedelta(hours=9)

        if int((self.start_time.date() - data['date'].date()).days) > self.day_range:
            return False
        
        #get content
        data['content'] = self.safe_post_data('in_post_content')
        
        #get username
        data['username'] = self.safe_post_data('in_post_username')

        #get likes
        #data['likes'] = self.safe_post_data('in_post_likes')

        #get first img_url
        data['img_url'] = self.get_img_url()
        if not data['img_url']:
            return True
        
        self.contents_db[key] = data
        return True

    def single_crawling_bs4(self, key):
        self.driver_post.get(self.posturl + key)
        
        pageString = self.driver.page_source
        bsObj = BeautifulSoup(pageString, "lxml")

        data = dict()

        data['date'] = dateutil.parser.parse(bsObj.find('a', class_='c-Yi7').time['datetime'])
        data['date'] += datetime.timedelta(hours=9)

        if int((self.start_time.date() - data['date'].date()).days) > self.day_range:
            return False

        #get content
        data['content'] = bsObj.find('div', class_='C4VMK').span
        
        #get username
        data['username'] = bsObj.find('div', class_='C4VMK').h2.div.a.text

        #get likes
        data['likes'] = 0 #default likes -> 0
        try:
            data['likes'] = int(bsObj.find('div', class_='Nm9Fw').button.span.text)
        except: pass
        
        #get first img_url

        try:
            data['img_url'] = bsObj.find('img', class_='FFVAD')['src'] #for image
        except:
            data['img_url'] = bsObj.find('video', class_='tWeCl')['poster'] #for video poster
        
        '''
        if not data['img_url']:
            return True
        '''
        self.contents_db[key] = data
        return True

    def run(self):
        self.login(self.driver)
        self.login(self.driver_post)

        logging.info('start time: %s' % (self.start_time))
        for station in self.station_list:
            for suffix in self.suffix_list:
                self.contents_db.clear()
                hashtag = station + suffix
                seed_url = self.urlbase + parse.quote(hashtag)
                try:
                    self.driver.get(seed_url)
                except:
                    logging.info('No page with tag : %s' % (hashtag))
                    #no page with hashtag, error occured
                    continue

                self.driver.find_element_by_tag_name('body').send_keys("webdriver" + Keys.PAGE_DOWN)
                self.driver.find_element_by_tag_name('body').send_keys("webdriver" + Keys.PAGE_DOWN)

                logging.info('Crawling start with tag : %s' % (hashtag))
                while True:
                    load_flag = self.link_loading(seed_url, batch_size=self.batch_size)
                    logging.info('Successfully load %d new links' % (len(self.link_collection)))
                    batch_flag = self.batch_crawling()
                    logging.info('Successfully crawling %d new links' % (len(self.link_collection)))

                    logging.info('Now %d in db' % (len(self.contents_db)))
                    if load_flag and batch_flag:
                        continue
                    break
                
                fname = str(int(datetime.datetime.now().timestamp())) + '.pickle'
                with open(fname, 'wb') as f:
                    pickle.dump(self.contents_db, f)
                logging.info('Crawling finished with tag : %s' % (hashtag))

                
if __name__ == "__main__":
    cw = Crawler()
    cw.run()
