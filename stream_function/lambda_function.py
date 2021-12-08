import boto3
import datetime
import json
import os
import requests

class TwitterStream:
    
    def __init__(self, token, values, bucket):
        self._s3 = boto3.client('s3')
        self._api_url = 'https://api.twitter.com/2/tweets/search/stream'
        self._headers = {
            "Content-type": "application/json",
            "Authorization": f'Bearer {token}'
        }
        self._values = values
        self._bucket = bucket

    def _get_rules(self):
        return requests.get(
            headers=self._headers,
            url=self._api_url+'/rules'
        )

    def _post_rules(self, data):
        return requests.post(
            headers=self._headers,
            url=self._api_url+'/rules',
            data=json.dumps(data)
        )

    def _get_stream(self):
        return requests.get(
            headers=self._headers,
            url=self._api_url,
            stream=True
        )

    def _write(self, key, text):
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=str(text).encode()
        )

    def start(self):

        # RULES ================================================================

        rules_add = []
        rules_value = []
        rules_delete = []

        # get
        for rule in self._get_rules(self).json()['data']:
            if rule['value'] not in self._values:
                rules_delete.append(rule['id'])
            else:
                rules_value.append(rule['value'])

        # delete
        if len(rules_delete) > 0:
            resp = self._post_rules(self,{"delete":{"ids":rules_delete}})
            print(f'DELETE STREAM RULES: {resp.text}')
            
        # add
        for value in self._values:
            if value not in rules_value:
                rules_add.append({"value":value})
        if len(rules_add) > 0:
            resp = self._post_rules(self,{"add":rules_add})
            print(f'ADD STREAM RULES: {resp.text}')

        # write
        for rule in self._get_rules(self).json()['data']:
            self._write(self, 'rule/'+rule['id']+'.json', rule)

        # STREAM ===============================================================

        for line in self._get_stream(self).iter_lines():
            if not line:
                continue

            tweet = json.loads(line)

            for rule in tweet['matching_rules']:
                self._write(self,
                    'tweet/'+rule['id'] + \
                        datetime.datetime.utcnow().strftime('/%Y/%m/%d/%H/%M/%Y%m%d%H%M%S%f_') + \
                        tweet['data']['id']+'.json',
                    tweet['data']
                )

def lambda_handler(event, context):

    TwitterStream(
        token = event['token'],
        values = event['values'],
        bucket = os.environ['BUCKET']
    ).start()
