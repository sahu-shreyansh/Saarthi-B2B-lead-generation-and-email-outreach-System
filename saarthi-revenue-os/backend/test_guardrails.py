import requests

login_resp = requests.post("http://127.0.0.1:8000/auth/login", json={
    "email": "test@example.com",
    "password": "password123"
})

if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.text}")
    print(login_resp.status_code)
    # let's write to try OAuth2PasswordRequestForm since JSON failed first
    login_resp2 = requests.post("http://127.0.0.1:8000/auth/login", data={
        "username": "test@example.com",
        "password": "password123"
    })
    if login_resp2.status_code != 200:
        print(f"Form Login failed: {login_resp2.text}")
        exit(1)
    else:
        login_resp = login_resp2

token = login_resp.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

camps_resp = requests.get("http://127.0.0.1:8000/campaigns", headers=headers)
campaigns = camps_resp.json()

if not campaigns:
    camp_resp = requests.post("http://127.0.0.1:8000/campaigns", headers=headers, json={"name": "Test Billing"})
    camp_id = camp_resp.json().get("id")
else:
    camp_id = campaigns[0].get("id")

print(f"Testing with Campaign ID: {camp_id}")

resp1 = requests.post("http://127.0.0.1:8000/leadgen/start", headers=headers, json={
    "campaign_id": camp_id,
    "industry": "cafe",
    "location": "sf",
    "max_leads": 10
})
print(f"Normal Test (10 leads): {resp1.status_code} - {resp1.text}")

resp2 = requests.post("http://127.0.0.1:8000/leadgen/start", headers=headers, json={
    "campaign_id": camp_id,
    "industry": "cafe",
    "location": "sf",
    "max_leads": 99999
})
print(f"Billionaire Test (99999 leads): {resp2.status_code} - {resp2.text}")
