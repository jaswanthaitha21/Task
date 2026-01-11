"""API utilities for communicating with the LLM service"""

import requests
import base64
import io
import json
import http.client

def fetch_available_models():
    """Fetch available LLM models"""
    try:
        conn = http.client.HTTPConnection("localhost:8000")
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

def fetch_supported_configs():
    """Fetch supported configurations from the API"""
    try:
        conn = http.client.HTTPConnection("10.232.115.110:8000")
        conn.request("GET", "/supported-configs")
        res = conn.getresponse()
        data = res.read()
        config = json.loads(data.decode("utf-8"))
        conn.close()
        
        return config
        
    except Exception as e:
        print(f"Error fetching supported configs: {e}")
        # Return default fallback values
        return {
            "supported_file_types": ["pdf", "txt", "docx", "doc", "csv", "xlsx", "xls"],
            "supported_chunk_methods": ["recursive", "character", "token", "markdown", "python", "html", "markdown_with_headings"],
            "supported_embedding_models": ["azure_openai"],
            "supported_vector_stores": ["faiss"]
        }

def fetch_supported_search_methods():
    """Fetch supported search methods from the API"""
    try:
        conn = http.client.HTTPConnection("10.232.115.110:8000")
        conn.request("GET", "/supported-search-methods")
        res = conn.getresponse()
        data = res.read()
        config = json.loads(data.decode("utf-8"))
        conn.close()
        
        return config.get("supported_search_methods", ["similarity_search"])
        
    except Exception as e:
        print(f"Error fetching supported search methods: {e}")
        # Return default fallback
        return ["similarity_search", "as_retriever", "similarity_search_with_score", "max_marginal_relevance_search"]

def call_llm_api(model_name, temperature, prompt, query, image_context=None, text_context=""):
    """Call the /generate API endpoint"""
    try:
        url = "http://localhost:8000/generate"
        
        # Prepare form data
        data = {
            "model_name": model_name,
            "temperature": str(temperature),
            "prompt": prompt or "",
            "query": query,
            "text_context": text_context or ""
        }
        
        files = None
        
        # Use image_context if provided and no text_context
        if image_context and not text_context:
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

def create_vector_store_api(doc_source, files, s3_url, dms_id, chunk_method, chunk_size, chunk_overlap, embedding_model, vector_store, progress_callback=None):
    """Create vector store by calling the /vector-creation API"""
    
    try:
        # Convert to API format
        if progress_callback:
            progress_callback(0.1, "Preparing configuration...")
        
        api_chunk_method = chunk_method.lower().replace(" ", "_")
        api_embedding_model = embedding_model.lower().replace(" ", "_")
        api_vector_store = vector_store.lower()
        
        # Prepare form data
        if progress_callback:
            progress_callback(0.2, "Preparing document data...")
        
        data = {
            "split_method": api_chunk_method,
            "chunk_size": str(int(chunk_size)),
            "overlap": str(int(chunk_overlap)),
            "embedding_model_type": api_embedding_model,
            "vector_store_type": api_vector_store
        }
        
        files_dict = None
        
        if progress_callback:
            progress_callback(0.3, "Processing documents...")
        
        if doc_source == "File Upload":
            # Handle file uploads
            if isinstance(files, list):
                file_path = files[0].name if hasattr(files[0], 'name') else str(files[0])
                with open(file_path, 'rb') as f:
                    files_dict = {"file": f}
                    if progress_callback:
                        progress_callback(0.5, "Sending to server...")
                    response = requests.post("http://10.232.115.110:8000/vector-creation", data=data, files=files_dict)
            else:
                file_path = files.name if hasattr(files, 'name') else str(files)
                with open(file_path, 'rb') as f:
                    files_dict = {"file": f}
                    if progress_callback:
                        progress_callback(0.5, "Sending to server...")
                    response = requests.post("http://10.232.115.110:8000/vector-creation", data=data, files=files_dict)
        
        elif doc_source == "S3 Folder URL":
            data["s3_folder_url"] = s3_url
            if progress_callback:
                progress_callback(0.5, "Fetching from S3...")
            response = requests.post("http://10.232.115.110:8000/vector-creation", data=data)
        
        else:  # DMS File ID
            data["dms_file_id"] = dms_id
            if progress_callback:
                progress_callback(0.5, "Fetching from DMS...")
            response = requests.post("http://10.232.115.110:8000/vector-creation", data=data)
        
        if progress_callback:
            progress_callback(0.8, "Processing response...")
        
        result = response.json()
        
        if progress_callback:
            progress_callback(0.9, "Finalizing...")
        
        return result
        
    except Exception as e:
        raise Exception(f"Error creating vector store: {str(e)}")