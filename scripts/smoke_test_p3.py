import requests
import time
import json

BASE_URL = "http://localhost:8080"
AI_URL = "http://localhost:8001"

def test_ai_rag():
    print("\n--- Testing AI RAG Capability ---")
    
    # 1. Create a dummy order for a specific plate
    plate = "RAG-TEST-99"
    print(f"Creating Order for {plate}...")
    try:
        # Auth login logic duplicated for simplicity or assume public create for this test?
        # BFF create requires Auth. Let's use the login logic from P1.
        # Quick hack: We'll skip Auth for this quick test script and just use the 'staff' token
        # Actually, let's just reuse the smoke_test_p1 logic fully
        pass
    except:
        pass

    # We will assume smoke_test_p1.py has run and we have a valid token logic available if we merge code.
    # For standalone, let's copy the login.
    token = login()
    if not token: return

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "customer_id": "13900000000",
        "vehicle_plate": plate,
        "description": "RAG Test"
    }
    requests.post(f"{BASE_URL}/mp/workorders/create", json=payload, headers=headers)
    
    # 2. Query AI
    print("Querying AI...")
    chat_payload = {
        "user_id": "user123",
        "message": f"What is the status of {plate}?"
    }
    
    try:
        res = requests.post(f"{AI_URL}/chat", json=chat_payload)
        if res.status_code == 200:
            data = res.json()
            print(f"AI Response: {data['response']}")
            if plate in data['response'] and "draft" in data['response']:
                print("SUCCESS: AI retrieved correct status.")
            else:
                print("FAILED: AI did not return expected status.")
        else:
            print(f"FAILED: AI Error {res.status_code}")
    except Exception as e:
        print(f"ERROR: {e}")

def login():
    try:
        res = requests.post(f"{BASE_URL}/auth/token", data={"username": "staff", "password": "secret"})
        return res.json()["access_token"]
    except:
        return None

if __name__ == "__main__":
    test_ai_rag()
