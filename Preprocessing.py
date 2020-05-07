#-*- coding: utf-8 -*-
import pickle
import pickledb
import re
import os
import time
import logging

from filelock import Timeout, FileLock
from bs4 import BeautifulSoup
from tqdm import tqdm

class Preprocessing:
    def __init__(self):
        self.regex = re.compile('>#(.*)<')
        #self.db = pickledb.load('post.db', True)
        logging.basicConfig(filename='./Log/preprocessor.log', level=logging.INFO)

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
        if target == None:
            return None

        return str(target) + '.pickle'

    def hashtag_extract(self, key):
        soup = BeautifulSoup(self.raw_data[key]['content'], 'html.parser')
        tags = []
        for tag in soup.find_all('a'):
            tags += self.regex.findall(str(tag))
        tags = list(set(tags))
        return tags

    def remove_tag(self, key):
        content = self.raw_data[key]['content']
        return re.sub('<.+?>', '', content)

    '''
    def commit_db(self, key, value):
        self.db.set(key, value)
        return True
    '''

    def run(self):
        while True:
            self.work = self.work_aloc()
            if self.work == None:
                time.sleep(30)
                continue
            
            with open(self.work, 'rb') as f:
                self.raw_data = pickle.load(f)
            
            lock = FileLock("post.db.lock")
            with lock:
                db = pickledb.load('post.db', False)
                logging.info('f_name : ' + self.work + ' started...')
                for key, value in tqdm(self.raw_data.items()):
                    value['hashtags'] = self.hashtag_extract(key)
                    value['content'] = self.remove_tag(key)
                    value['date'] = str(value['date'])
                    db.set(key, value)
                os.remove(self.work)
                db.dump()
                logging.info('f_name : ' + self.work + ' finished...')

if __name__ == "__main__":
    preproc = Preprocessing()
    preproc.run()
