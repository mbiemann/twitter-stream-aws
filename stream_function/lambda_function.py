import boto3
import datetime
import json
import os
import requests

bucket = os.environ['BUCKET']

def rules(token, values):

    rules_add = []
    rules_value = []
    rules_delete = []

    # get
    resp = requests.get(
        url='https://api.twitter.com/2/tweets/search/stream/rules',
        headers={
            "Content-type": "application/json",
            "Authorization": f'Bearer {token}'
        }
    )
    for rule in resp.json()['data']:
        if rule['value'] not in values:
            rules_delete.append(rule['id'])
        else:
            rules_value.append(rule['value'])

    # delete
    if len(rules_delete) > 0:
        resp = requests.post(
            url='https://api.twitter.com/2/tweets/search/stream/rules',
            headers={
                "Content-type": "application/json",
                "Authorization": f'Bearer {token}'
            },
            data=json.dumps({"delete":{"ids":rules_delete}})
        )
        print(f'DELETE STREAM RULES: {resp.text}')
    
    # add
    for value in values:
        if value not in rules_value:
            rules_add.append({"value":value})
    if len(rules_add) > 0:
        resp = requests.post(
            url='https://api.twitter.com/2/tweets/search/stream/rules',
            headers={
                "Content-type": "application/json",
                "Authorization": f'Bearer {token}'
            },
            data=json.dumps({"add":rules_add})
        )
        print(f'ADD STREAM RULES: {resp.text}')
    
    # put s3
    resp = requests.get(
        url='https://api.twitter.com/2/tweets/search/stream/rules',
        headers={
            "Content-type": "application/json",
            "Authorization": f'Bearer {token}'
        }
    )
    for rule in resp.json()['data']:
        boto3.client('s3').put_object(
            Bucket=bucket,
            Key='rule/'+rule['id']+'.json',
            Body=str(rule).encode()
        )

def stream(token):

    # get stream
    resp = requests.get(
        url='https://api.twitter.com/2/tweets/search/stream',
        headers={
            "Content-type": "application/json",
            "Authorization": f'Bearer {token}'
        },
        stream=True
    )
    
    # iteration
    for line in resp.iter_lines():
        if not line:
            continue

        tweet = json.loads(line)
        
        # rule per folder
        for rule in tweet['matching_rules']:

            # Put object to S3 bucket
            boto3.client('s3').put_object(
                Bucket=bucket,
                Key='tweet/'+rule['id']+datetime.datetime.utcnow().strftime('/%Y/%m/%d/%H/%M/%Y%m%d%H%M%S%f_')+ \
                    tweet['data']['id']+'.json',
                Body=str(tweet['data']).encode()
            )

def main(token, values):

    # rules
    rules(token, values)

    # start
    stream(token)

def lambda_handler(event, context):

    main(
        twitter_token = event['token'],
        values = event['values'],
    )