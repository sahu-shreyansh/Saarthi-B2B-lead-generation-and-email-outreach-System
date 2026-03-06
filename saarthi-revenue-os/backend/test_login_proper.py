import traceback
from fastapi.testclient import TestClient
from app.main import app

def run():
    try:
        client = TestClient(app)
        response = client.post("/auth/login", json={"email": "sahushreyansh692@gmail.com", "password": "wrongpassword"})
        print("STATUS:", response.status_code)
        print("CONTENT:", response.text)
    except Exception as e:
        print("EXCEPTION CAUGHT:")
        traceback.print_exc()

if __name__ == "__main__":
    run()
