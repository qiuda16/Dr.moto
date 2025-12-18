import time
import random
import logging

# Simulate Edge Device (e.g. Camera or IoT Sensor)
# In reality, this would run on a Raspberry Pi or similar

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("edge-node")

def simulate_sensor_reading():
    """Simulate reading from hardware"""
    return {
        "temperature": 20 + random.random() * 5,
        "vibration": random.random() * 0.1,
        "status": "active"
    }

def main():
    logger.info("Starting Edge Node...")
    while True:
        data = simulate_sensor_reading()
        logger.info(f"Sensor Data: {data}")
        
        # In real world, send to MQTT or BFF
        # requests.post("http://bff:8080/edge/telemetry", json=data)
        
        time.sleep(5)

if __name__ == "__main__":
    main()
