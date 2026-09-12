from fastapi import APIRouter, UploadFile, File
import asyncio
import random
from typing import Dict, Any

router = APIRouter()

@router.post("/vision/detect", tags=["Vision"], summary="Run ML disease detection on uploaded image")
async def detect_disease(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Accepts an image upload and returns a simulated ML disease detection response.
    This replaces the 'Camera Not Connected' state with a working demo endpoint.
    """
    # Simulate ML processing delay
    await asyncio.sleep(1.5)
    
    # Read a few bytes just to ensure the upload worked
    content = await file.read(10)
    
    # A few possible stub responses for the hackathon demo
    scenarios = [
        {
            "status": "success",
            "prediction": "Healthy",
            "confidence": 0.98,
            "disease_detected": False,
            "recommendation": "Crop is healthy. Continue normal monitoring."
        },
        {
            "status": "success",
            "prediction": "Early Blight",
            "confidence": 0.87,
            "disease_detected": True,
            "recommendation": "Apply fungicide immediately. Ensure canopy airflow."
        },
        {
            "status": "success",
            "prediction": "Pest: Fall Armyworm",
            "confidence": 0.92,
            "disease_detected": True,
            "recommendation": "Inspect stems for larvae. Apply recommended pesticide if threshold exceeded."
        }
    ]
    
    # Pick a random scenario to make the demo feel dynamic
    result = random.choice(scenarios)
    result["filename"] = file.filename
    
    return result
