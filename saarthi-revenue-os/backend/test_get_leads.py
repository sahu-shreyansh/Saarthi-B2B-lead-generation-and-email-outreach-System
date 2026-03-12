import requests
import json

url = "http://localhost:8000/api/v1/leads?campaign_id=8da37bc1-10b9-4259-8f2e-2bef95a483ca"
headers = {"Authorization": "Bearer mock-token-for-local-dev"}
response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
try:
    print(json.dumps(response.json()[:2], indent=2))
except Exception as e:
    print(response.text)
