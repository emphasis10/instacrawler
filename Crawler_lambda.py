# -*- coding: utf-8 -*-
import datetime
import time
import random
import re
import platform
import json
import os
import csv
import json
import boto3

import dateutil.parser

from urllib import parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup


class Crawler:
    def __init__(self):
        self.driver_dir = '/opt/python/chromedriver'
        self.urlbase = "https://www.instagram.com/explore/tags/"
        self.posturl = "https://www.instagram.com/p/"
        self.login_url = "https://www.instagram.com/accounts/login/"

        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('InstaTourSeedTag')

        all_key = []
        for tag in self.table.scan()['Items']:
            all_key.append(tag['tag'])
        self.station_list = random.sample(all_key, 5)
        # select random 10 tags

        self.table = self.dynamodb.Table('InstaTourRawData')

        self.suffix_list = ['']
        self.driver_setting()
        self.start_time = datetime.datetime.now()
        self.contents_db = dict()
        self.link_collection = set()
        self.batch_size = 72
        self.id_pool = set()

        self.regex = re.compile('>#(.*)<')

        # 이 부분 dynamoDB 연동 부분으로 변경해야 함.
        # 생략 가능
        '''db = pickledb.load('post.db', False)
        self.id_pool = set(db.getall())'''

        with open('/opt/python/path.json') as f:
            data = json.load(f)
            self.path = data['path']
            self.day_range = int(data['range'])

    def __del__(self):
        self.driver.close()
        self.driver_post.close()

    def driver_setting(self):
        options = webdriver.ChromeOptions()
        options.binary_location = '/opt/python/headless-chromium'
        options.add_argument('headless')
        options.add_argument('window-size=1920x1080')
        options.add_argument('disable-gpu')
        options.add_argument('no-sandbox')
        options.add_argument('--single-process')
        options.add_argument('--disable-dev-shm-usage')

        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(self.driver_dir, chrome_options=options)
        self.driver.implicitly_wait(5)  # setting implicitly waiting time

        self.driver_post = webdriver.Chrome(
            self.driver_dir, chrome_options=options)
        self.driver_post.implicitly_wait(5)

    def link_loading(self, seed_url, batch_size=100):
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
                    cur_url = self.driver.find_element_by_xpath(
                        tmp_url + '/div[' + str(i + 1) + ']/a').get_attribute('href')
                    cur_id = cur_url.split('/')[-2]
                    if cur_id in self.id_pool:
                        continue
                    if cur_id not in self.link_collection and cur_id not in self.contents_db:
                        new_post = True
                        self.link_collection.add(cur_id)
                        #print('Find %dth new link : %s' % (linkcnt, cur_id))
                        linkcnt += 1
            if new_post == False:
                return False
            self.driver.find_element_by_tag_name(
                'body').send_keys("webdriver" + Keys.PAGE_DOWN)
            self.driver.find_element_by_tag_name(
                'body').send_keys("webdriver" + Keys.PAGE_DOWN)
            self.driver.find_element_by_tag_name(
                'body').send_keys("webdriver" + Keys.PAGE_DOWN)
            time.sleep(3)
        return True

    def hashtag_extract(self, key):
        soup = BeautifulSoup(self.contents_db[key]['content'], 'html.parser')
        tags = []
        for tag in soup.find_all('a'):
            tags += self.regex.findall(str(tag))
        tags = list(set(tags))
        return tags

    def remove_tag(self, key):
        content = self.contents_db[key]['content']
        return re.sub('<.+?>', '', content)

    def commit_db(self, key, value):
        self.table.put_item(
            Item={
                'key': key,
                'username': value['username'],
                'date': value['date'],
                'content': value['content'],
                'likes': value['likes'],
                'img_url': value['img_url'],
                'hashtags': value['hashtags'],
            }
        )
        return True

    def batch_crawling(self):
        time_flag = True
        for key in self.link_collection:
            time_flag &= self.single_crawling_bs4(key)
        time.sleep(5)
        return time_flag

    def reloader(self):
        time.sleep(2)
        self.driver_post.refresh()
        time.sleep(5)
        pageString = self.driver_post.page_source
        self.bsObj = BeautifulSoup(pageString, "lxml")

        if self.bsObj.find('title').text[0] == '\n':
            return False
        else:
            return True

    def single_crawling_bs4(self, key):
        self.driver_post.get(self.posturl + key)

        data = dict()
        pageString = self.driver_post.page_source
        self.bsObj = BeautifulSoup(pageString, "lxml")

        if self.bsObj.find('title').text[0] == '\n':
            return False

        counter = 0
        while True:
            counter += 1
            try:
                data['date'] = dateutil.parser.parse(
                    self.bsObj.find('a', class_='c-Yi7').time['datetime'])
                data['date'] += datetime.timedelta(hours=9)

                if int((self.start_time.date() - data['date'].date()).days) > self.day_range:
                    return False

                # get content
                data['content'] = str(
                    self.bsObj.find('div', class_='C4VMK').span)

                # get username
                data['username'] = str(self.bsObj.find(
                    'div', class_='e1e1d').a.text)

                # get likes
                data['likes'] = 0  # default likes -> 0
                try:
                    data['likes'] = int(self.bsObj.find(
                        'div', class_='Nm9Fw').button.span.text)
                except:
                    pass

                # get first img_url

                try:
                    data['img_url'] = str(self.bsObj.find(
                        'img', class_='FFVAD')['src'])  # for image
                except:
                    try:
                        data['img_url'] = str(self.bsObj.find('video', class_='tWeCl')[
                                              'poster'])  # for video poster
                    except:
                        return False
                break
            except:
                if self.reloader() == False:
                    return False

        self.contents_db[key] = data
        return True

    def run(self):
        for station in self.station_list:
            for suffix in self.suffix_list:
                self.contents_db.clear()
                hashtag = station + suffix
                seed_url = self.urlbase + parse.quote(hashtag)
                try:
                    self.driver.get(seed_url)
                except:
                    # no page with hashtag, error occured
                    continue

                self.driver.find_element_by_tag_name(
                    'body').send_keys("webdriver" + Keys.PAGE_DOWN)
                self.driver.find_element_by_tag_name(
                    'body').send_keys("webdriver" + Keys.PAGE_DOWN)

                while True:
                    load_flag = self.link_loading(
                        seed_url, batch_size=self.batch_size)

                    batch_flag = self.batch_crawling()

                    if load_flag and batch_flag:
                        continue
                    break

                for key, value in self.contents_db.items():
                    value['hashtags'] = self.hashtag_extract(key)
                    value['content'] = self.remove_tag(key)
                    value['date'] = str(value['date'])
                    self.commit_db(key, self.contents_db[key])


if __name__ == "__main__":
    cw = Crawler()
    cw.run()
