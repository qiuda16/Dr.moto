import requests
import json
import sys

try:
    # Health Check
    health = requests.get('http://localhost:8003/health')
    with open("verify_result.txt", "w", encoding="utf-8") as f:
        f.write(f"Health Status: {health.status_code}\n")
        f.write(json.dumps(health.json(), indent=2) + "\n")
        
        # KB Test
        print("\nTesting KB...", flush=True)
        # Note: We use 'real_manual_test' as collection because that's what we ingested into
        payload = {'question': '定期保养表', 'collection': 'real_manual_test'}
        kb_res = requests.post('http://localhost:8003/ai/kb/ask', json=payload)
        f.write(f"KB Status: {kb_res.status_code}\n")
        if kb_res.status_code == 200:
            f.write(json.dumps(kb_res.json(), indent=2, ensure_ascii=False) + "\n")
        else:
            f.write(kb_res.text + "\n")
    print("Result written to verify_result.txt")

except Exception as e:
    with open("verify_error.txt", "w", encoding="utf-8") as f:
        f.write(str(e))
    print(f"Error: {e}")
