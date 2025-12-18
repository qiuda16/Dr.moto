import requests
import json
import time

BASE_URL = "http://localhost:8080"
AI_URL = "http://localhost:8001"

def test_knowledge_base():
    print("\n--- Testing Knowledge Base (Structured) ---")
    
    # 1. Seed Data
    print("Seeding DB...")
    res = requests.post(f"{BASE_URL}/mp/knowledge/seed")
    if res.status_code != 200:
        print(f"Seed Failed: {res.text}")
        return

    # 2. Query BFF Directly
    print("Querying BFF Procedures...")
    res = requests.get(f"{BASE_URL}/mp/knowledge/procedures?vehicle_key=TOYOTA|COROLLA|2019|1.8&name=Oil")
    if res.status_code == 200:
        data = res.json()
        if len(data) > 0 and "Oil Change" in data[0]['name']:
            print(f"SUCCESS: Found procedure with {len(data[0]['steps'])} steps.")
        else:
            print("FAILED: Procedure content mismatch.")
    else:
        print(f"FAILED: BFF Error {res.status_code}")

    # 3. Query via AI (RAG)
    print("Querying AI for Procedure...")
    chat_payload = {
        "user_id": "user123",
        "message": "How to change oil for Corolla?"
    }
    try:
        res = requests.post(f"{AI_URL}/chat", json=chat_payload)
        if res.status_code == 200:
            data = res.json()
            print(f"AI Response:\n{data['response']}")
            if "1. Lift vehicle" in data['response']:
                print("SUCCESS: AI returned structured steps.")
            else:
                print("FAILED: AI did not return steps.")
        else:
            print(f"FAILED: AI Error {res.status_code}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_knowledge_base()
