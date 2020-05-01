#-*- coding: utf-8 -*-
import pickle
import re
import os
import time

from bs4 import BeautifulSoup

class Preprocessing:
    def __init__(self):
        self.regex = re.compile('>#(.*)<')

    def work_aloc(self):
        f_list = os.listdir()
        target = None
        for i in f_list:
            if re.search('.pickle$', i):
                if target == None:
                    target = int(i.split('.')[0])
                else:
                    ts = int(i.split('.')[0])
                    target = min(target, ts)
        return str(target) + '.pickle'

    def hashtag_extract(self, key):
        soup = BeautifulSoup(self.raw_data[key]['content'], 'html.parser')
        tags = []
        for tag in soup.find_all('a'):
            tags.append(self.regex.findall(str(tag)))
        return tags

    def remove_tag(self, key):
        content = self.raw_data[key]['content']
        return re.sub('<.+?>', '', content)

    def commit_db(self, key, value):
        return True

    def run(self):
        while True:
            self.work = self.work_aloc()
            if self.work == None:
                time.sleep(30)
                continue
            
            with open(self.work, 'rb') as f:
                self.raw_data = pickle.load(f)
            
            for key in self.raw_data:
                hash_tags = self.hashtag_extract(key)
                date = self.raw_data[key]['date']
                content = self.remove_tag(key)
                #img_url = self.raw_data[key]['img']
                img_url = None
                self.commit_db(key, {'hash_tags':hash_tags, 'date':date, 'content':content, 'img_url':img_url})
            os.remove(self.work)

if __name__ == "__main__":
    preproc = Preprocessing()
    reproc.run()
