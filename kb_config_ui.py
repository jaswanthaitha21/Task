"""Knowledge Base configuration page"""

import gradio as gr

def create_kb_config_page():
    """Create knowledge base configuration page"""
    with gr.Column(elem_id="kb-config-page") as kb_config_page:
        # Header with back button
        with gr.Row(elem_id="kb-config-header"):
            back_btn = gr.Button("← Back to Chat", size="sm", variant="secondary")
            gr.Markdown("# Create New Knowledge Base", elem_id="kb-config-title")
        gr.Markdown("---")

        # Configuration form
        with gr.Column(elem_id="kb-config-form"):
            # Knowledge Base Name
            kb_name_input = gr.Textbox(
                label="Knowledge Base Name",
                placeholder="Enter a name for your knowledge base"
            )

            # File Upload
            kb_files_upload = gr.File(
                label="Upload Documents",
                file_count="multiple",
                file_types=[".pdf", ".txt", ".docx", ".md"]
            )

            # Split Method Selection
            split_method = gr.Dropdown(
                label="Text Splitting Method",
                choices=[
                    "RecursiveCharacterTextSplitter",
                    "CharacterTextSplitter",
                    "TokenTextSplitter",
                    "MarkdownTextSplitter",
                    "PythonCodeTextSplitter",
                    "LatexTextSplitter"
                ],
                value="RecursiveCharacterTextSplitter",
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
                choices=[
                    "text-embedding-ada-002 (OpenAI)",
                    "text-embedding-3-small (OpenAI)",
                    "text-embedding-3-large (OpenAI)",
                    "sentence-transformers/all-MiniLM-L6-v2",
                    "sentence-transformers/all-mpnet-base-v2",
                    "BAAI/bge-small-en-v1.5",
                    "BAAI/bge-base-en-v1.5",
                    "BAAI/bge-large-en-v1.5"
                ],
                value="text-embedding-ada-002 (OpenAI)",
                info="Model used to create embeddings"
            )

            # Vector Store Selection
            vector_store = gr.Dropdown(
                label="Vector Store",
                choices=[
                    "FAISS",
                    "Chroma",
                    "Pinecone",
                    "Weaviate",
                    "Qdrant",
                    "Milvus"
                ],
                value="FAISS",
                info="Database to store vector embeddings"
            )

            # Status message
            kb_create_status = gr.Textbox(
                label="Status",
                interactive=False,
                visible=False
            )

            # Create Vector button
            create_vector_btn = gr.Button("Create Vector Store", variant="primary", size="lg")

    return (
        kb_config_page,
        back_btn,
        kb_name_input,
        kb_files_upload,
        split_method,
        chunk_size,
        chunk_overlap,
        embedding_model,
        vector_store,
        create_vector_btn,
        kb_create_status
    )

def create_vector_store(kb_name, files, split_method, chunk_size, chunk_overlap, embedding_model, vector_store):
    """Create vector store with dummy data for now"""
    if not kb_name or not kb_name.strip():
        return gr.update(value="❌ Please enter a knowledge base name", visible=True)
    
    if not files:
        return gr.update(value="❌ Please upload at least one document", visible=True)

    # Dummy success message
    try:
        file_count = len(files) if isinstance(files, list) else 1
        status_msg = f"""✅ Vector store created successfully!

📊 Configuration Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Knowledge Base: {kb_name}
• Documents: {file_count} file(s) uploaded
• Split Method: {split_method}
• Chunk Size: {chunk_size} characters
• Overlap: {chunk_overlap} characters
• Embedding Model: {embedding_model}
• Vector Store: {vector_store}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ You can now return to chat and select this knowledge base!"""
        
        return gr.update(value=status_msg, visible=True)
    
    except Exception as e:
        return gr.update(value=f"❌ Error creating vector store: {str(e)}", visible=True)