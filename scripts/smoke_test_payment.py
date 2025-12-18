import requests
import json
import time
import uuid

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

def test_payment_flow():
    print("\n--- Testing Payment Flow & Idempotency ---")
    
    # 1. Create Work Order (Prerequisite)
    wo_id = f"wo-{uuid.uuid4()}"
    # We cheat and use the UUID directly in the intent if the backend allows, 
    # OR we need to create a real WO first. 
    # The BFF create_payment_intent checks `db.query(WorkOrder).filter(WorkOrder.uuid == intent.work_order_id)`
    # So we MUST create a WO first.
    
    headers = {"Authorization": f"Bearer {TOKEN}"}
    create_payload = {
        "customer_id": "13888888888",
        "vehicle_plate": "PAY-TEST-01",
        "description": "Payment Test"
    }
    res = requests.post(f"{BASE_URL}/mp/workorders/create", json=create_payload, headers=headers)
    if res.status_code != 200:
        print(f"FAILED: Could not create WO. {res.text}")
        return
    wo_data = res.json()
    wo_uuid = wo_data['id']
    print(f"Created WO: {wo_uuid}")
    
    # 2. Create Payment Intent
    print("Creating Payment Intent...")
    pay_payload = {
        "work_order_id": wo_uuid,
        "amount": 100.0,
        "provider": "mock"
    }
    res = requests.post(f"{BASE_URL}/mp/payments/create_intent", json=pay_payload, headers=headers)
    if res.status_code != 200:
        print(f"FAILED: Could not create intent. {res.text}")
        return
    pay_data = res.json()
    trans_id = pay_data['payment_id']
    print(f"Created Intent: {trans_id}")
    
    # 3. Confirm Payment (1st time)
    print("Confirming Payment (1st)...")
    res = requests.post(f"{BASE_URL}/mp/payments/mock_confirm", json={"transaction_id": trans_id})
    if res.status_code == 200:
        print("SUCCESS: Payment Confirmed")
    else:
        print(f"FAILED: {res.text}")
        
    # 4. Confirm Payment (2nd time - Idempotency Check)
    print("Confirming Payment (2nd - Idempotency)...")
    res = requests.post(f"{BASE_URL}/mp/payments/mock_confirm", json={"transaction_id": trans_id})
    data = res.json()
    if res.status_code == 200 and data.get("message") == "Already paid":
        print("SUCCESS: Idempotency Verified (Already paid)")
    else:
        print(f"FAILED: Expected 'Already paid', got {res.text}")

if __name__ == "__main__":
    if login():
        test_payment_flow()
