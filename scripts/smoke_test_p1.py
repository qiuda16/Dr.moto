import requests
import json
import time

BASE_URL = "http://localhost:8080"
TOKEN = None

def login():
    global TOKEN
    print("--- Logging in ---")
    try:
        res = requests.post(f"{BASE_URL}/auth/token", data={
            "username": "staff",
            "password": "secret"
        })
        if res.status_code == 200:
            TOKEN = res.json()["access_token"]
            print("SUCCESS: Logged in")
            return True
        else:
            print(f"FAILED Login: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        print(f"ERROR Login: {e}")
        return False

def test_create_order():
    print("\n--- Testing Work Order Creation ---")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = {
        "customer_id": "13800000000",
        "vehicle_plate": "TEST-001",
        "description": "Smoke Test Order"
    }
    try:
        res = requests.post(f"{BASE_URL}/mp/workorders/create", json=payload, headers=headers)
        if res.status_code == 200:
            data = res.json()
            print(f"SUCCESS: Created Order {data['id']}")
            return data['id']
        else:
            print(f"FAILED Create: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        print(f"ERROR Create: {e}")
        return None

def test_upload_media(order_id):
    print(f"\n--- Testing Media Upload for {order_id} ---")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    files = {'file': ('test_image.jpg', b'fake_image_content', 'image/jpeg')}
    try:
        res = requests.post(f"{BASE_URL}/mp/workorders/{order_id}/upload", files=files, headers=headers)
        if res.status_code == 200:
            print(f"SUCCESS: Uploaded {res.json()['url']}")
        else:
            print(f"FAILED Upload: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"ERROR Upload: {e}")

def test_event_ingestion():
    print("\n--- Testing Event Ingestion ---")
    payload = {
        "event_id": "evt-test-002",
        "timestamp": "2024-01-01T12:00:00",
        "event_type": "rule_violation",
        "source": "smoke_test",
        "payload": {"description": "Test Violation 2"}
    }
    try:
        res = requests.post(f"{BASE_URL}/events/ingest", json=payload)
        if res.status_code == 200:
            print("SUCCESS: Event Ingested")
        else:
            print(f"FAILED Ingest: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"ERROR Ingest: {e}")

if __name__ == "__main__":
    # Ensure BFF is up (simple retry)
    for i in range(5):
        try:
            requests.get(f"{BASE_URL}/health")
            break
        except:
            print("Waiting for BFF...")
            time.sleep(2)
            
    if login():
        order_id = test_create_order()
        if order_id:
            test_upload_media(order_id)
        test_event_ingestion()
