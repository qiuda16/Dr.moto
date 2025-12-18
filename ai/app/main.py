from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import logging
import os

# Config
class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    BFF_URL = os.getenv("BFF_URL", "http://bff:8080")

settings = Settings()

# App
app = FastAPI(title="DrMoto AI Service", version="0.1.0")
logger = logging.getLogger("ai")
logging.basicConfig(level=logging.INFO)

from .routers import kb
app.include_router(kb.router)

# Models
class ChatRequest(BaseModel):
    user_id: str
    message: str
    context: dict = {}

class ChatResponse(BaseModel):
    response: str
    suggested_actions: list = []

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai"}

import requests
import re

# ... (Config remains same)

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    logger.info(f"Chat request: {req.message}")
    try:
        msg = req.message.lower()
        response_text = ""
        actions = []
        
        # 1. Intent: Check Status with Plate Number
        plate_match = re.search(r'\b[A-Z0-9-]*\d+[A-Z0-9-]*\b', req.message.upper())
        
        if ("status" in msg or "check" in msg) and plate_match:
            plate = plate_match.group(0)
            logger.info(f"Detected plate: {plate}")
            try:
                # Use synchronous requests for stability in MVP (avoiding httpx crash)
                url = f"{settings.BFF_URL}/mp/workorders/search?plate={plate}"
                logger.info(f"Calling BFF: {url}")
                res = requests.get(url, timeout=5)
                logger.info(f"BFF Response: {res.status_code}")
                if res.status_code == 200:
                    orders = res.json()
                    if orders:
                        latest = orders[-1]
                        response_text = f"Found {len(orders)} order(s) for {plate}. The latest status is: **{latest['status']}** (ID: {latest['id']})."
                    else:
                        response_text = f"I couldn't find any work orders for vehicle {plate}."
                else:
                    response_text = "I'm having trouble connecting to the records system right now."
            except Exception as e:
                logger.error(f"RAG Error: {e}", exc_info=True)
                response_text = "Sorry, I encountered an internal error while checking records."
                
        # 2. Intent: Procedure/Guide Query
        # e.g., "How to change oil for Corolla?"
        if "how to" in msg or "guide" in msg or "procedure" in msg:
            # MVP: Extract vehicle and procedure name (Mock logic)
            # In real life, use LLM to extract {vehicle_key, procedure_name}
            vehicle_key = "TOYOTA|COROLLA|2019|1.8" # Default for MVP
            proc_name = "Oil Change"
            
            try:
                # Call BFF Structured Knowledge
                url = f"{settings.BFF_URL}/mp/knowledge/procedures?vehicle_key={vehicle_key}&name={proc_name}"
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    procs = res.json()
                    if procs:
                        p = procs[0]
                        steps_text = "\n".join([f"{s['step_order']}. {s['instruction']}" for s in p['steps']])
                        response_text = f"Here is the procedure for **{p['name']}**:\n\n{steps_text}"
                        actions = ["Start Procedure"]
                    else:
                        response_text = f"I couldn't find a structured procedure for '{proc_name}'."
                else:
                    response_text = "Knowledge Base unavailable."
            except Exception as e:
                logger.error(f"KB Error: {e}")
                response_text = "Sorry, I can't access the manual right now."

        elif "status" in msg or "order" in msg:
            response_text = "I can help you check your work order status. Please provide your Vehicle Plate number."
            actions = ["Check Status"]
        elif "price" in msg or "cost" in msg:
            response_text = "Our basic service starts at $50. For a detailed quote, please visit our shop."
            actions = ["View Pricing"]
        elif "hours" in msg or "open" in msg:
            response_text = "We are open Monday to Friday, 9 AM to 6 PM."
        else:
            response_text = f"I received your message: '{req.message}'. How can I help you with your vehicle today?"
            
        return {
            "response": response_text,
            "suggested_actions": actions
        }
    except Exception as e:
        logger.error(f"Critical Chat Error: {e}", exc_info=True)
        return {
            "response": "System Error",
            "suggested_actions": []
        }
