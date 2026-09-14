from fastapi import APIRouter, UploadFile, File, Form
import os
from typing import Dict, Any

router = APIRouter()

@router.post("/vision/detect", tags=["Vision"], summary="Run ML disease detection on uploaded image")
async def detect_disease(file: UploadFile = File(...), crop_name: str = Form("green_gram")) -> Dict[str, Any]:
    """
    Accepts an image upload and returns ML disease detection response.
    Uses YOLO if the model is available.
    """
    # The backend is typically run from the SIH_AGRI/backend directory.
    # We placed the models in SIH_AGRI/backend/ml_models/
    full_path = os.path.join("ml_models", f"{crop_name}.pt")
    
    if not os.path.exists(full_path):
        return {
            "status": "training",
            "prediction": "Model Under Training",
            "confidence": 0.0,
            "disease_detected": False,
            "recommendation": f"The ML model for {crop_name.replace('_', ' ').title()} is currently under training and will be available soon.",
            "filename": file.filename
        }
        
    # Read the file
    contents = await file.read()
    
    # Import here to avoid overhead if not used
    import cv2
    import numpy as np
    from ultralytics import YOLO
    
    try:
        model = YOLO(full_path)
        
        # Convert bytes to numpy array
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        results = model(img)
        result = results[0]
        
        if len(result.boxes) == 0:
            return {
                "status": "success",
                "prediction": "Healthy",
                "confidence": 0.95,
                "disease_detected": False,
                "recommendation": f"No diseases or pests detected for {crop_name.replace('_', ' ').title()}. Continue normal monitoring.",
                "filename": file.filename
            }
        
        # Get highest confidence detection
        best_box = max(result.boxes, key=lambda box: float(box.conf[0]))
                
        conf = float(best_box.conf[0])
        class_id = int(best_box.cls[0])
        prediction = result.names[class_id]
        
        # Simple heuristic: if the class name contains 'healthy', it's healthy
        is_disease = "healthy" not in prediction.lower()
        
        return {
            "status": "success",
            "prediction": prediction.replace('_', ' ').title(),
            "confidence": conf,
            "disease_detected": is_disease,
            "recommendation": f"Detected {prediction}. Consult local agricultural guidelines for treatment." if is_disease else "Crop appears healthy.",
            "filename": file.filename
        }
    except Exception as e:
        return {
            "status": "error",
            "prediction": "Analysis Failed",
            "confidence": 0.0,
            "disease_detected": False,
            "recommendation": f"An error occurred during inference: {str(e)}",
            "filename": file.filename
        }
