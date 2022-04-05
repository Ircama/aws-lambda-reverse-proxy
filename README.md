# aws-lambda-reverse-proxy
A simple Python Reverse Proxy using AWS Lambda

# AWS Lambda setup

AWS > Lambda > Functions > Create function
- select "Author from scratch"
- Function name: rproxy
- Runtime: Python 3.9
- Architecture: x86_64
- Permissions: Create a new role with basic Lambda permissions

Press Create Function

Press Add trigger

Select Api Gateway

Select "Create an API"
Select "HTTP API"
Security: Open

Press Add

Press "rproxy-API" in "API Gateway: rproxy-API"

Press "Routes"

Press Create

Route and method: `ANY` `/{proxy+}`

Notes on using the `ANY` `/{proxy+}` integration:
- https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
- https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-set-up-simple-proxy.html

Press Create

Select "ANY" in "`/rproxy`" (not `/{proxy+}`)

Press Delete (and confirm).

You shoud have 
```
$default
  /{proxy+}
    ANY
```

Press ANY

Press "Attach integration"

Select rproxy (your AWS Lambda function)

Press "Attach integration"

Notice:
Payload format version: 2.0
Timeout: 30000 msec

Press again "API Gateway" on the top.

Press "rproxy-API"

Select "default" (not $default)

Check that "default" is selected (not $default) and press "Delete". Confirm.

Press again "API Gateway" on the top.

Press "rproxy-API"

You shoud just have "$default"	https://.......amazonaws.com

Test the URL in another page; you should get "Hello from Lambda!"

Add /test to the URL: https://.......amazonaws.com/test

You should still get "Hello from Lambda!" (this means that the proxy gateway works with all paths).

Go back to AWS > Lambda > Functions >rproxy

Select "General configuration". Configure the memory (e.g., 512 MB) and the timeout (e.g., 30 secs). Press Save.

Press Triggers (and do a refresh on this page....)

You might have two API Gateway: rproxy-API
API endpoint: https://....amazonaws.com/{proxy+}
and another one with arn:aws:execute-api.../*/*/rproxy

Remove the second one (select and delete), so that only the `/{proxy+}` is configured.

Press "Environment variables".

Add `REMOTE_URL` and `FILTERED_PATH` (see below).

Press Code.

Paste the code from this repo (replacing the default code)

Press "Deploy".

Select "Runtime settings" and press Edit

Change the Handler: lambda_function.proxy_handler.

Press Save.

Test again the page.

Test https://....amazonaws.com/foobar; you should get a "Filtered URL." error (if using `FILTERED_PATH=/foobar`).

Test https://....amazonaws.com/cookies/set/:name/:value; you should get the cookie named `:name:` set to `:value`.

Test https://....amazonaws.com/headers; you should get the list of headers of your function, as obtained by https://httpbin.org/headers; included in the headers there should be `"Cookie": ":name=:value",`

Test https://....amazonaws.com/headers?trace_request=y; you should get the dump of the `event` and `context` variables of `proxy_handler()`.

Test https://....amazonaws.com/headers?trace_connection=y; you should read tracing information in the CloudWatch Logs (e.g., `/usr/local/bin/aws logs tail /aws/lambda/rproxy  --follow`).

In case of error, run `/usr/local/bin/aws logs tail /aws/lambda/rproxy  --follow` and see the logs.

## Installation of awscli

Installation of awscli on Unix (or WSL) to trace the AWS Lambda function:

```bash
# Install awscli:

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
/usr/local/bin/aws --version

# Configure awscli:
/usr/local/bin/aws configure
```

## Tracing

(After installing awscli:)

```bash
/usr/local/bin/aws logs tail /aws/lambda/<function name> --follow
```

## Needed variables

`REMOTE_URL`: http or https remote URL (example: https://httpbin.org)

`FILTERED_PATH`: path that needs to be filtered (example: /foobar)

## Special parameters

`&trace_connection=y`: trace log data via `aws logs tail /aws/lambda/<function name> --follow`
`&trace_request=y`: dump the request
