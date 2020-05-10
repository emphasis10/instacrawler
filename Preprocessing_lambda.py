# -*- coding: utf-8 -*-
import pickle
import re
import os
import time
import logging
import boto3
import json

from bs4 import BeautifulSoup


class Preprocessing:
    def __init__(self):
        self.regex = re.compile('>#(.*)<')
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table('InstaTourRawData')

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

    def commit_db(self, key, value):
        self.table.put_item(
            Item={
                'key': key,
                'username': value['username'],
                'date': value['date'],
                'content': value['content'],
                'likes': value['likes'],
                'img_url': value['img_url'],
                'hashtags': value['hashtag'],
            }
        )
        return True

    def run(self):
        while True:
            self.work = self.work_aloc()
            if self.work == None:
                break

            with open(self.work, 'rb') as f:
                self.raw_data = pickle.load(f)

            for key, value in self.raw_data.items():
                value['hashtags'] = self.hashtag_extract(key)
                value['content'] = self.remove_tag(key)
                value['date'] = str(value['date'])
                self.commit_db(key, value)
            os.remove(self.work)


if __name__ == "__main__":
    preproc = Preprocessing()
    preproc.run()
