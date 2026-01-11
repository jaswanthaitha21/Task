"""Knowledge Base configuration page"""

import gradio as gr
from api_utils import fetch_supported_configs, create_vector_store_api

def create_kb_config_page():
    """Create knowledge base configuration page"""
    
    # Fetch supported configurations from API
    supported_configs = fetch_supported_configs()
    
    # Prepare file types for Gradio (add dots)
    file_types = [f".{ft}" for ft in supported_configs.get("supported_file_types", ["pdf", "txt", "docx"])]
    
    # Prepare chunk methods (capitalize first letter for display)
    chunk_methods = [method.replace("_", " ").title() for method in supported_configs.get("supported_chunk_methods", ["recursive"])]
    
    # Prepare embedding models (capitalize for display)
    embedding_models = [model.replace("_", " ").title() for model in supported_configs.get("supported_embedding_models", ["azure_openai"])]
    
    # Prepare vector stores (uppercase for display)
    vector_stores = [vs.upper() for vs in supported_configs.get("supported_vector_stores", ["faiss"])]
    
    with gr.Column(elem_id="kb-config-page") as kb_config_page:
        
        # Header with back button
        with gr.Row(elem_id="kb-config-header"):
            with gr.Column(scale=6):
                gr.Markdown("# Create New Knowledge Base", elem_id="kb-config-title")
            with gr.Column(scale=1):
                back_btn = gr.Button("← Back to Chat", size="sm", variant="secondary")
        
        gr.Markdown("---")
        
        # Configuration form
        with gr.Column(elem_id="kb-config-form"):
            
            # Document Source Selection
            gr.Markdown("### Document Source")
            doc_source = gr.Radio(
                choices=["File Upload", "S3 Folder URL", "DMS File ID"],
                value="File Upload",
                label="How would you like to provide documents?",
                info="Choose only one source for your documents"
            )
            
            # File Upload (visible by default)
            kb_files_upload = gr.File(
                label="Upload Documents",
                file_count="multiple",
                file_types=file_types,
                visible=True
            )
            
            # S3 URL Input (hidden by default)
            s3_url_input = gr.Textbox(
                label="S3 Folder URL",
                placeholder="s3://bucket-name/folder/path",
                visible=False
            )
            
            # DMS File ID Input (hidden by default)
            dms_id_input = gr.Textbox(
                label="DMS File ID",
                placeholder="Enter DMS File ID",
                visible=False
            )
            
            gr.Markdown("---")
            
            # Chunk Method Selection
            chunk_method = gr.Dropdown(
                label="Chunking Method",
                choices=chunk_methods,
                value=chunk_methods[0] if chunk_methods else "Recursive",
                info="Choose how to split your documents into chunks"
            )
            
            # Chunk Size and Overlap
            with gr.Row():
                chunk_size = gr.Slider(
                    label="Chunk Size",
                    minimum=100,
                    maximum=4000,
                    value=1000,
                    step=100,
                    info="Size of each text chunk in characters"
                )
                
                chunk_overlap = gr.Slider(
                    label="Chunk Overlap",
                    minimum=0,
                    maximum=500,
                    value=200,
                    step=50,
                    info="Overlap between consecutive chunks"
                )
            
            # Embedding Model Selection
            embedding_model = gr.Dropdown(
                label="Embedding Model",
                choices=embedding_models,
                value=embedding_models[0] if embedding_models else "Azure Openai",
                info="Model used to create embeddings"
            )
            
            # Vector Store Selection
            vector_store = gr.Dropdown(
                label="Vector Store",
                choices=vector_stores,
                value=vector_stores[0] if vector_stores else "FAISS",
                info="Database to store vector embeddings"
            )
            
            # Status message
            kb_create_status = gr.Textbox(
                label="Status",
                interactive=False,
                visible=False
            )
            
            # Progress bar
            kb_progress = gr.Progress()
            
            # Create Vector button
            create_vector_btn = gr.Button("Create Vector Store", variant="primary", size="lg")
        
        # Event handlers for document source toggle
        def toggle_doc_source(choice):
            """Show/hide inputs based on document source selection"""
            if choice == "File Upload":
                return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
            elif choice == "S3 Folder URL":
                return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
            else:  # DMS File ID
                return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
        
        doc_source.change(
            toggle_doc_source,
            inputs=[doc_source],
            outputs=[kb_files_upload, s3_url_input, dms_id_input]
        )
    
    return (
        kb_config_page,
        back_btn,
        doc_source,
        kb_files_upload,
        s3_url_input,
        dms_id_input,
        chunk_method,
        chunk_size,
        chunk_overlap,
        embedding_model,
        vector_store,
        create_vector_btn,
        kb_create_status,
        toggle_doc_source,
        kb_progress
    )

def create_vector_store(doc_source, files, s3_url, dms_id, chunk_method, chunk_size, chunk_overlap, embedding_model, vector_store, progress=gr.Progress()):
    """Create vector store wrapper with UI feedback"""
    
    # Validate document source
    if doc_source == "File Upload" and not files:
        return gr.update(value="❌ Please upload at least one document", visible=True)
    elif doc_source == "S3 Folder URL" and (not s3_url or not s3_url.strip()):
        return gr.update(value="❌ Please enter a valid S3 folder URL", visible=True)
    elif doc_source == "DMS File ID" and (not dms_id or not dms_id.strip()):
        return gr.update(value="❌ Please enter a valid DMS File ID", visible=True)
    
    try:
        # Show initial progress
        progress(0, desc="Starting vector creation...")
        yield gr.update(value="🔄 Initializing...", visible=True)
        
        # Progress callback function
        def progress_callback(value, desc):
            progress(value, desc=desc)
        
        # Show upload status
        yield gr.update(value="📤 Uploading documents...", visible=True)
        
        # Call API function
        result = create_vector_store_api(
            doc_source, files, s3_url, dms_id, 
            chunk_method, chunk_size, chunk_overlap, 
            embedding_model, vector_store, 
            progress_callback
        )
        
        # Show processing status
        yield gr.update(value="⚙️ Creating embeddings and vector store...", visible=True)
        
        # Check response
        if result.get("success"):
            progress(1.0, desc="Completed!")
            status_msg = f"""✅ Vector store created successfully!

Configuration Summary:
- Document Count: {result.get('document_count', 'N/A')}
- Batch Count: {result.get('batch_count', 'N/A')}
- Vector Store Type: {result.get('store_type', vector_store).upper()}
- Chunk Method: {chunk_method}
- Chunk Size: {int(chunk_size)} characters
- Overlap: {int(chunk_overlap)} characters
- Embedding Model: {embedding_model}
- Saved Path: {result.get('saved_path', 'N/A')}

{result.get('message', 'You can now return to chat and select this knowledge base!')}"""
        else:
            status_msg = f"❌ Error: {result.get('message', 'Unknown error occurred')}"
        
        yield gr.update(value=status_msg, visible=True)
        
    except Exception as e:
        progress(0, desc="Error occurred")
        error_msg = f"❌ Error creating vector store: {str(e)}"
        yield gr.update(value=error_msg, visible=True)