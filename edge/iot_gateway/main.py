import time
import json
import uuid
from datetime import datetime
import random

def main():
    print("Starting IoT Gateway...")
    print("Connecting to Sensors...")
    
    while True:
        # Mock sensor loop
        time.sleep(2)
        
        # Simulate torque reading
        reading = {
            "device_id": "torque_gun_01",
            "timestamp": datetime.now().isoformat(),
            "type": "torque",
            "value": round(random.uniform(10.0, 15.0), 2),
            "unit": "Nm"
        }
        print(f"[IoT] Sensor Reading: {json.dumps(reading)}")

if __name__ == "__main__":
    main()
