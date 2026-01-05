"""API utilities for communicating with the LLM service"""

import requests
import base64
import io
import json
import http.client

def fetch_available_models():
    """Fetch available LLM models from localhost:8000/models"""
    try:
        conn = http.client.HTTPConnection("localhost", 8000)
        conn.request("GET", "/models")
        res = conn.getresponse()
        data = res.read()
        conn.close()
        models_data = json.loads(data.decode("utf-8"))
        # Extract all_models from the response
        if isinstance(models_data, dict) and "all_models" in models_data:
            return models_data["all_models"]
        elif isinstance(models_data, list):
            return models_data
        else:
            return ["GPT-4"]  # Fallback
    except Exception as e:
        print(f"Error fetching models: {e}")
        return ["GPT-4"]  # Fallback model

def call_llm_api(model_name, temperature, prompt, query, image_context=None):
    """Call the /generate API endpoint"""
    try:
        url = "http://localhost:8000/generate"
        # Prepare form data
        data = {
            "model_name": model_name,
            "temperature": str(temperature),
            "prompt": prompt or "",
            "query": query,
            "text_context": ""  # Leave empty for now
        }
        files = None
        if image_context:
            # Decode base64 to binary and create file-like object
            image_bytes = base64.b64decode(image_context)
            image_file = io.BytesIO(image_bytes)
            files = {
                "image_context": ("image.png", image_file, "image/png")
            }
        # Make POST request
        response = requests.post(url, data=data, files=files)
        response_data = response.json()
        # Extract response field from API response
        if isinstance(response_data, dict) and "response" in response_data:
            return response_data["response"]
        return str(response_data)
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return f"Error: Unable to connect to LLM service. ({str(e)})"