# Handles asynchronous calls to the agent API.
import json
import requests
from datetime import datetime
from pydantic import BaseModel
from objects import ModelResp, modelresps, PatientInput

agentUrl = "http://localhost:8082/diagnose"
agent_call_running = False  # Flag to track if agentCall is running
result = None

async def agentCall_async(transcribed_text):
    print("agentCall_async started")

    global agent_call_running
    if agent_call_running:
        print("agentCall already running. Skipping")   
        return

    agent_call_running = True
    try:
        # print("agentCall:")
        # print(transcribed_text)
        print("before patient input")
        payload = PatientInput(
            gender="Unknown",
            age=0,
            symptoms=transcribed_text,
            medical_history=transcribed_text)
        
        response = requests.post(agentUrl, json=payload.dict())
        result = response.json()
        if response.status_code == 200:
            print("Modelquery successful")
        else:
           print(f"Modelquery failed: {response.status_code}")
            
        # print("Result:", result)
    except Exception as e:
        print(f"Exception: {e}")
        result = (e).json()
    finally:
        agent_call_running = False
        modelresps.append(ModelResp(datetime.now(), result))
        print("after modelresps append: ", len(modelresps))
