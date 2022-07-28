#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Ircama"
__copyright__ = "Copyright 2021-2022, Ircama"
__license__ = "CC BY-NC-SA 4.0"
__version__ = "1.0.1"
__maintainer__ = "Ircama"

import base64
import pprint
import os
import urllib3

# Disable the "Not Secure" warning when using HTTPS:
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GENERAL_ERROR = os.environ.get('GENERAL_ERROR') or "AWS Lambda Error"

PAYLOAD_QUOTA = int(os.environ.get('PAYLOAD_QUOTA') or 5000000)
# https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html

def proxy_handler(event, context):
    if os.environ.get('REMOTE_URL') is None:
        return {
            "statusCode": 500,
            "body": GenerateErrorPage("Missing REMOTE_URL environment variable",
                    GENERAL_ERROR + ": missing REMOTE_URL environment variable",
                    'AWS Lambda function not correctly configured'),
            "headers": {
                'Content-Type': 'text/html',
            }
        }
    url = os.environ['REMOTE_URL']
    if "rawPath" in event and event["rawPath"]:
        url += event["rawPath"]
    if "rawQueryString" in event and event["rawQueryString"].strip():
        url += "?" + event["rawQueryString"]

    http_method = event['requestContext']['http']['method']

    if (os.environ.get('FILTERED_PATH') is not None and
            "rawPath" in event and
            event["rawPath"] in os.environ['FILTERED_PATH'].split("|")):
        return {
            "statusCode": 500,
            "body": GenerateErrorPage(url,
                    GENERAL_ERROR,
                    os.environ.get('FILTERED_URL_MSG') or 'Filtered URL.'),
            "headers": {
                'Content-Type': 'text/html',
            }
        }

    # &trace_connection=y to print log data
    trace_connection = False
    if (event.get('queryStringParameters') and
            event['queryStringParameters'].get("trace_connection")):
        trace_connection = True
    # &dump_request=y to dump the request
    dump_request = False
    if (event.get('queryStringParameters') and
            event['queryStringParameters'].get("dump_request")):
        dump_request = True

    cookies = []
    if event.get('cookies'):
        cookies = event['cookies']

    headers = {}
    if event.get('headers'):
        headers = event['headers']

    body = ''
    if event.get('body'):
        body = event['body']

    if event.get('isBase64Encoded'):
        if event['isBase64Encoded']:
            body = base64.b64decode(body)
    
    if cookies:
        headers['Cookie'] = '; '.join(cookies)

    if trace_connection:
        print("remote url =", url)
        print("local http_method =", http_method)
        print("headers =", headers)
        print("cookies =", cookies)
        print("body =", body)

    retries = urllib3.util.Retry(connect=0, read=0, redirect=0)
    http = urllib3.PoolManager(
        cert_reqs='CERT_NONE',
        timeout=float(os.environ.get('REQUEST_TIMEOUT') or 11.0),
        retries=retries)
    try:
        resp = http.request(method=http_method, url=url, headers=headers,
                            body=body, redirect=False)
        resp_cookies = resp.headers.getlist('Set-Cookie')
        if trace_connection:
            print("statusCode returned from remote =", resp.status)
            print("resp_cookies =", resp_cookies)
            print("resp.headers =", resp.headers)
            print("size of received data =", len(resp.data))
            print("size of encoded data =", len(base64.b64encode(resp.data)))
        # https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html
        if len(resp.data) > PAYLOAD_QUOTA:
            return {
                "statusCode": 413,
                "body": GenerateErrorPage(url,
                        GENERAL_ERROR + ' (Payload Too Large)',
                        'Too much data to return'
                        ' from the remote web site over AWS Lambda'),
                "headers": {
                    'Content-Type': 'text/html',
                }
            }
        response = {
            "cookies": resp_cookies,
            "isBase64Encoded": True,
            "statusCode": resp.status,
            "body": base64.b64encode(resp.data),
            "headers": { i:resp.headers[i] for i in resp.headers }
        }
    except urllib3.exceptions.MaxRetryError:
        if trace_connection:
            print('Remote server down.')
        response = {
            "statusCode": 500,
            "body": GenerateErrorPage(url,
                    GENERAL_ERROR,
                    'Remote server down.'),
            "headers": {
                'Content-Type': 'text/html',
            }
        }
    except urllib3.exceptions.NewConnectionError:
        if trace_connection:
            print('Connection failed.')
        response = {
            "statusCode": 500,
            "body": GenerateErrorPage(url,
                    GENERAL_ERROR,
                    'Connection failed'),
            "headers": {
                'Content-Type': 'text/html',
            }
        }
    except Exception as e:
        if trace_connection:
            print('Connection error:', repr(e))
        response = {
            "statusCode": 500,
            "body": GenerateErrorPage(url,
                    GENERAL_ERROR,
                    'Connection error: ' + repr(e)),
            "headers": {
                'Content-Type': 'text/html',
            }
        }

    #print("response=", json.dumps(response, indent=4))

    if not dump_request:
        return response

    return {
        'statusCode': 200,
        'body': (
            ""
            """<!DOCTYPE html><html><head><title>Request dump</title></head>
<style>
pre {
    border: 2px solid grey;
    border-left: 6px solid #8f9090;
    border-radius: 8px;
    padding-left: 14px;
    padding-bottom: 14px;
    padding-right: 14px;
    width: -moz-fit-content;
    width: fit-content;
    margin: auto;
    line-height: 15px;
    background-image: linear-gradient(180deg, #f5f5f5 50%, #fff 50%);
    background-size: 100% 30px;
    background-position: 0 14px;
    box-shadow: 5px 5px 10px rgb(0 0 0 / 30%);
    -webkit-box-shadow: 5px 5px 10px rgba(0,0,0,0.3);
}
</style><body><hr /><div><pre>""" +
            #json.dumps(event, indent=4) + "\n<hr />" +
            pprint.pformat(event, indent=4) + "\n<hr />" +
            "Lambda function name: " +
                repr(context.function_name) + "\n" +
            "Lambda function version: " +
                repr(context.function_version) + "\n" +
            "Lambda function ARN: " +
                repr(context.invoked_function_arn) + "\n" +
            "CloudWatch log stream name: " +
                repr(context.log_stream_name) + "\n" +
            "CloudWatch log group name: " +
                repr(context.log_group_name) + "\n" +
            "Lambda Request ID: " +
                repr(context.aws_request_id) + "\n" +
            "Lambda function memory limits in MB: " +
                repr(context.memory_limit_in_mb) + "\n" +
            "Lambda time remaining in MS: " +
                repr(context.get_remaining_time_in_millis()) + "\n" +
            "\n<hr />" +
            "</pre></body></html>"
            ),
        "headers": {
            'Content-Type': 'text/html',
        }
    }
    # https://docs.aws.amazon.com/lambda/latest/dg/python-context.html


def GenerateErrorPage(url, error, description):
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css">
    <title>""" + (
        os.environ.get('GENERAL_ERROR') or "AWS Lambda Error"
        ) + """</title>
    </head>
    <body>
        <div class="jumbotron">
            <h1 class="display-4">""" + (
            os.environ.get('APP_NAME') or "Sample Application") + """</h1>
            <p class="lead"><h4><pre><b>""" + error  + """</b></pre></p></h4>
        </div>
        <div class="container-fluid">
        <h3><a style="color:red">""" + description + """</a></h3>
        </div>
        <br />
        <br />
        <div class="container-fluid">
        <h3><a href='""" + url + """'>Click here to access the same funtion on the target system</a></h3>
        </div>
    </body>
</html> 
"""
