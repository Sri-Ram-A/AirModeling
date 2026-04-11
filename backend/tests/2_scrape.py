import requests
import json
import urllib3

urllib3.disable_warnings()

session = requests.Session()

url = "https://airquality.cpcb.gov.in/caaqms/fetch_table_data"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://airquality.cpcb.gov.in/ccr/",
    "Origin": "https://airquality.cpcb.gov.in",
    "Accept": "application/json",
    "Content-Type": "text/plain"
}

payload = {
    "draw": 1,
    "start": 0,
    "length": 10,
    "city": "Bengaluru",
    "criteria": "24 Hours",
    "fromDate": "10-04-2026 T00:00:00Z",
    "parameterNames": ["PM2.5"]
}

# Step 1: establish session
session.get("https://airquality.cpcb.gov.in/ccr/", headers=headers, verify=False)

# Step 2: send request
response = session.post(
    url,
    headers=headers,
    data=json.dumps(payload),
    verify=False
)

print(response.text)