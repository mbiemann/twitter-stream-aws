import boto3
import datetime
import json
import os
import requests

class TwitterStream:

    def __init__(self, token, values, report, bucket, context):
        self._s3 = boto3.client('s3')
        self._api_url = 'https://api.twitter.com/2/tweets/search/stream'
        self._headers = {
            "Content-type": "application/json",
            "Authorization": f'Bearer {token}'
        }
        self._values = values
        self._bucket = bucket
        self._context = context
        self._report = report

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
        for rule in self._get_rules().json()['data']:
            if rule['value'] not in self._values:
                rules_delete.append(rule['id'])
            else:
                rules_value.append(rule['value'])

        # delete
        if len(rules_delete) > 0:
            resp = self._post_rules({"delete":{"ids":rules_delete}})
            print(f'DELETE STREAM RULES: {resp.text}')

        # add
        for value in self._values:
            if value not in rules_value:
                rules_add.append({"value":value})
        if len(rules_add) > 0:
            resp = self._post_rules({"add":rules_add})
            print(f'ADD STREAM RULES: {resp.text}')

        # write
        for rule in self._get_rules().json()['data']:
            self._write(
                'stream/rule/'+rule['id']+'.json',
                json.dumps({
                    "id": rule['id'],
                    "value": rule['value']
                })
            )
            if rule['id'] not in self._report:
                self._report[rule['id']] = {"value":rule['value'],"count":0}

        # STREAM ===============================================================

        time_max = 0
        for line in self._get_stream().iter_lines():
            if not line:
                continue

            time_start = self._context.get_remaining_time_in_millis()

            tweet = json.loads(line)
            for rule in tweet['matching_rules']:
                dt = datetime.datetime.utcnow()
                self._write(
                    'stream/tweet/'+rule['id'] + \
                        dt.strftime('/%Y/%m/%d/%H/%M/%Y%m%d%H%M%S%f_') + \
                        tweet['data']['id']+'.json',
                    json.dumps({
                        "id": tweet['data']['id'],
                        "text": tweet['data']['text'],
                        "rule_id": rule['id'],
                        "datetime": dt.isoformat()
                    })
                )
                self._report[rule['id']]['count'] += 1

            time_end = self._context.get_remaining_time_in_millis()
            if time_end <= (time_max * 3):
                break
            time_spent = time_start - time_end
            if time_spent > time_max:
                time_max = time_spent

        return self._report

def lambda_handler(event, context):
    return TwitterStream(
        token = event['token'],
        values = event['values'],
        report = event['stream'] if 'stream' in event else {},
        bucket = os.environ['BUCKET'],
        context = context
    ).start()