import cv2
import time
import json
import uuid
import os
import requests
import numpy as np
from datetime import datetime

# Configuration
BFF_URL = os.getenv("BFF_URL", "http://localhost:8080")
CAMERA_ID = int(os.getenv("CAMERA_ID", 0))
USE_MOCK_CAMERA = os.getenv("USE_MOCK_CAMERA", "true").lower() == "true"

def get_camera_frame(cap):
    if USE_MOCK_CAMERA or not cap.isOpened():
        # Generate a dummy frame (gray noise) with text
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, f"MOCK CAMERA - {datetime.now()}", (50, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        # Draw a fake tool (red rectangle)
        cv2.rectangle(frame, (100, 100), (200, 300), (0, 0, 255), -1)
        return True, frame
    else:
        return cap.read()

def main():
    print(f"Starting CV Module (Mock: {USE_MOCK_CAMERA})...")
    
    # Init Camera
    cap = None
    if not USE_MOCK_CAMERA:
        cap = cv2.VideoCapture(CAMERA_ID)
    
    # Load MediaPipe (Lazy load to avoid crash if not installed)
    try:
        import mediapipe as mp
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        print("MediaPipe Hands Initialized.")
    except ImportError:
        print("MediaPipe not installed. Running in simulation mode.")
        hands = None

    last_event_time = 0
    
    while True:
        success, image = get_camera_frame(cap)
        if not success:
            print("Ignoring empty camera frame.")
            continue

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 1. Hand Detection
        results = None
        if hands:
            results = hands.process(image_rgb)
        
        # 2. Tool Detection (Mock Logic for now, real YOLO would go here)
        # Assume if we see red pixels in the box (100,100) to (200,300), a tool is present
        roi = image[100:300, 100:200]
        # Check for red color
        avg_color_per_row = np.average(roi, axis=0)
        avg_color = np.average(avg_color_per_row, axis=0)
        # avg_color is [B, G, R]
        tool_present = avg_color[2] > 100 and avg_color[0] < 50
        
        # 3. Logic: Send event if tool detected (throttle to every 10s)
        if tool_present and (time.time() - last_event_time > 10):
            event_payload = {
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "event_type": "tool_detected",
                "source": "cv_camera_01",
                "payload": {
                    "tool_id": "screwdriver_ph_2",
                    "confidence": 0.98,
                    "location": {"x": 150, "y": 200, "zone": "Zone A"}
                }
            }
            print(f"[CV] Tool Detected: {json.dumps(event_payload)}")
            
            try:
                requests.post(f"{BFF_URL}/events/ingest", json=event_payload, timeout=2)
            except Exception as e:
                print(f"[CV] Failed to send: {e}")
                
            last_event_time = time.time()

        # Visualization (Optional, for local debugging)
        # cv2.imshow('MediaPipe Hands', image)
        # if cv2.waitKey(5) & 0xFF == 27:
        #   break
        
        # Sleep to reduce CPU usage in mock mode
        time.sleep(0.1)

    if cap:
        cap.release()

if __name__ == "__main__":
    main()
