#-*- coding: utf-8 -*-
import datetime, time
import random
import re
import platform
import json
import pickle
import os
import csv

import dateutil.parser

from tqdm import tqdm
from urllib import parse 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
#https://www.selenium.dev/docs/site/en/

class Crawler:
	def __init__(self):
		if platform.system() == "Linux":
			self.driver_dir = './chromedriver' #for linux system
		else:
			self.driver_dir = 'chromedriver.exe' #for windows system

		self.urlbase = "https://www.instagram.com/explore/tags/"
		self.posturl = "https://www.instagram.com/p/"
		self.login_url = "https://www.instagram.com/accounts/login/"

		self.station_list = []
		with open('station.csv','r') as f:
			tmp = csv.reader(f)
			for name in tmp:
				self.station_list.append(name[0])

		self.suffix_list = ['역']
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
		prefs = {"profile.managed_default_content_settings.images": 2}
		options.add_experimental_option("prefs", prefs)

		self.driver = webdriver.Chrome(self.driver_dir, chrome_options=options)
		self.driver.implicitly_wait(5) #setting implicitly waiting time

		self.driver_post = webdriver.Chrome(self.driver_dir, chrome_options=options)
		self.driver_post.implicitly_wait(5)

	def link_loading(self, seed_url, batch_size = 100):
		print('Link loading with batch size : %d' %(batch_size))
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
			if self.single_crawling(key) == False:
				time_flag = False
		return time_flag
	
	def single_crawling(self, key):
		self.driver_post.get(self.posturl + key)

		waitcnt = 0
		while True:
			try:
				post_date = dateutil.parser.parse(self.driver_post.find_element_by_xpath(self.path['in_post_date']).get_attribute("datetime"))
				break
			except Exception as e:
				print(e)
				time.sleep(0.5)
				waitcnt += 1
				if waitcnt > 3:
					waitcnt = 0
					self.driver_post.refresh()

		post_date += datetime.timedelta(hours=9)

		if int((self.start_time.date() - post_date.date()).days) > self.day_range:
			return False
		
		waitcnt = 0
		while True:
			try:
				post_content = self.driver_post.find_element_by_xpath(self.path['in_post_content']).get_attribute("innerHTML")
				break
			except Exception as e:
				print(e)
				time.sleep(0.5)
				waitcnt += 1
				if waitcnt > 3:
					waitcnt = 0
					self.driver_post.refresh()

		self.contents_db[key] = {"date" : post_date, "content" : post_content}
		return True

	def run(self):
		self.login(self.driver)
		self.login(self.driver_post)

		print('start time: %s' % (self.start_time))
		for station in self.station_list:
			for suffix in self.suffix_list:
				self.contents_db.clear()
				hashtag = station + suffix
				seed_url = self.urlbase + parse.quote(hashtag)
				#self.tag_crawling(seed_url)
				try:
					self.driver.get(seed_url)
				except:
					#no page with hashtag, error occured
					continue
				self.driver.find_element_by_tag_name('body').send_keys("webdriver" + Keys.PAGE_DOWN)
				self.driver.find_element_by_tag_name('body').send_keys("webdriver" + Keys.PAGE_DOWN)
				while True:
					load_flag = self.link_loading(seed_url, batch_size=self.batch_size)
					print('Successfully load %d new links' % (len(self.link_collection)))
					batch_flag = self.batch_crawling()
					print('Successfully crawling %d new links' % (len(self.link_collection)))

					print('Now %d in db' % (len(self.contents_db)))
					if load_flag and batch_flag:
						continue
					break
				
				fname = str(int(datetime.datetime.now().timestamp())) + '.pickle'
				with open(fname, 'wb') as f:
					pickle.dump(self.contents_db, f)
				print('Crawling finished with no errors!')

				
if __name__ == "__main__":
	cw = Crawler()
	cw.run()