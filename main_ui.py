"""Improved Main chat application UI with better state management"""

import gradio as gr
import os
import base64
from typing import Dict, List, Tuple
from api_utils import call_llm_api, fetch_supported_search_methods

def handle_file_upload(files, current_files: Dict) -> Tuple[str, Dict]:
    """Handle document upload and convert to base64 - thread-safe"""
    if not files:
        return "No files selected", current_files
    
    current_files.clear()
    successful_uploads = []
    
    for file in files:
        try:
            file_path = file.name if hasattr(file, 'name') else str(file)
            file_name = os.path.basename(file_path)
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Basic file type validation
            file_ext = os.path.splitext(file_name)[1].lower()
            
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                media_type = f"image/{file_ext[1:]}"
            elif file_ext == '.pdf':
                media_type = "application/pdf"
            else:
                media_type = "application/octet-stream"
            
            file_base64 = base64.b64encode(file_content).decode('utf-8')
            
            current_files[file_name] = {
                'data': file_base64,
                'type': media_type,
                'size': len(file_content)
            }
            
            successful_uploads.append(file_name)
            
        except Exception as e:
            print(f"Error reading file {file_name}: {e}")
    
    if successful_uploads:
        status_msg = f"✓ Uploaded {len(successful_uploads)} file(s): {', '.join(successful_uploads)}"
    else:
        status_msg = "❌ No files uploaded successfully"
    
    return status_msg, current_files

def chat_response(
    message: str,
    history: List,
    selected_model: str,
    selected_kb: str,
    uploaded_files: Dict,
    temperature: float = 0.7,
    system_prompt: str = "",
    text_context: str = ""
) -> Tuple[List, Dict]:
    """Handle chat messages with proper error handling and KB context"""
    
    if not message or not message.strip():
        return history, uploaded_files
    
    try:
        # Handle image context vs text context
        image_context = None
        final_text_context = ""
        
        # Priority: if text context is provided, use it; otherwise check for images
        if text_context and text_context.strip():
            final_text_context = text_context.strip()
        elif uploaded_files:
            # Use first image if available
            first_file = list(uploaded_files.values())[0]
            if first_file['type'].startswith('image/'):
                image_context = first_file['data']
        
        # Call LLM API
        bot_response = call_llm_api(
            model_name=selected_model,
            temperature=temperature,
            prompt=system_prompt,
            query=message,
            image_context=image_context,
            text_context=final_text_context
        )
        
        # Clear uploaded files after use (optional - keep for context)
        uploaded_files.clear()
        
    except Exception as e:
        print(f"Error in chat_response: {e}")
        bot_response = f"I apologize, but I encountered an error: {str(e)}"
    
    # Append to history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": bot_response})
    
    return history, uploaded_files

def create_main_app(available_models: List[str], kb_list: List[Dict]):
    """Create main application interface with improved state management"""
    
    # Fetch supported search methods
    supported_search_methods = fetch_supported_search_methods()
    
    # Format search methods for display (replace underscores with spaces and title case)
    search_method_choices = [method.replace("_", " ").title() for method in supported_search_methods]
    
    # Session state
    uploaded_files = gr.State({})
    current_kb = gr.State(kb_list[0]['name'] if kb_list else None)
    
    with gr.Column() as main_app:
        
        # Top bar
        with gr.Row(elem_id="top-bar"):
            with gr.Column(elem_id="top-mid", scale=3):
                gr.HTML("<div id='common-rag-title'><h2>Common RAG</h2></div>")
            
            with gr.Column(elem_id="top-right", scale=1):
                with gr.Row(scale=1):
                    user_display = gr.Textbox(
                        value="",
                        label="",
                        interactive=False,
                        container=False,
                        elem_id="user-display",
                        placeholder="User"
                    )
                
                with gr.Row(scale=1):
                    clear_btn = gr.Button("Clear Chat", size="sm", variant="secondary", elem_id="clear-btn")
                    logout_btn = gr.Button("Logout", size="sm", variant="secondary", elem_id="logout-btn")
        
        gr.Markdown("---")
        
        # Main content area
        with gr.Row(equal_height=True):
            
            # Left sidebar
            with gr.Column(scale=1, min_width=250, elem_id="sidebar"):
                new_chat_btn = gr.Button("+ Create New Knowledge Base", size="lg", variant="primary", elem_id="sidebar-new-chat-btn")
                
                gr.Markdown("---")
                
                # Knowledge Bases section
                with gr.Group():
                    gr.Markdown("### Knowledge Bases", elem_id="section-title")
                    
                    with gr.Column(elem_id="kb_scroll"):
                        # Create card-style buttons for each KB
                        kb_buttons = []
                        for kb in kb_list:
                            with gr.Row(elem_classes="kb-card"):
                                kb_btn = gr.Button(
                                    f"📚 {kb['name']}\n📅 {kb['created']}",
                                    elem_classes="kb-card-btn",
                                    size="sm"
                                )
                                kb_buttons.append(kb_btn)
                
                gr.Markdown("---")
                
                # Previous Chats section
                with gr.Group():
                    gr.Markdown("### Previous Chats", elem_id="section-title")
                    
                    with gr.Column(elem_id="chats_scroll"):
                        # Create card-style buttons for chats
                        chat_buttons = []
                        chats = [
                            {"title": "Project Q&A", "date": "2026-01-03"},
                            {"title": "Research Summary", "date": "2026-01-02"},
                            {"title": "Code Help", "date": "2025-12-30"},
                            {"title": "Technical Review", "date": "2025-12-29"},
                            {"title": "Documentation", "date": "2025-12-28"},
                        ]
                        for chat in chats:
                            with gr.Row(elem_classes="chat-card"):
                                chat_btn = gr.Button(
                                    f"💬 {chat['title']}\n📅 {chat['date']}",
                                    elem_classes="chat-card-btn",
                                    size="sm"
                                )
                                chat_buttons.append(chat_btn)
            
            # Right side: Chat interface
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="", height=450, show_label=False)
                
                # Upload status
                upload_status = gr.Textbox(
                    label="",
                    interactive=False,
                    visible=False,
                    elem_id="upload-status"
                )
                
                # Main input row
                with gr.Row(elem_id="input-bar", elem_classes="input-group"):
                    upload_btn = gr.UploadButton(
                        "📎",
                        file_count="multiple",
                        size="sm",
                        elem_id="upload-btn",
                        scale=0
                    )
                    
                    msg_input = gr.Textbox(
                        placeholder="Enter your query here...",
                        show_label=False,
                        container=False,
                        elem_id="msg-input",
                        scale=4,
                        lines=1,
                        max_lines=1,
                        submit_btn=True
                    )
                    
                    model_dropdown = gr.Dropdown(
                        choices=available_models,
                        value=available_models[0] if available_models else None,
                        show_label=False,
                        container=False,
                        elem_id="model-dropdown"
                    )
                
                # Model Settings Modal
                with gr.Column(visible=False, elem_id="settings-modal") as settings_modal:
                    with gr.Row(elem_id="settings-modal-header"):
                        gr.Markdown("### Model Settings", elem_id="settings-modal-title")
                        minimize_settings_btn = gr.Button("−", size="sm", elem_id="minimize-settings-btn")
                        maximize_settings_btn = gr.Button("□", size="sm", elem_id="maximize-settings-btn", visible=False)
                        close_settings_btn = gr.Button("✕", size="sm", elem_id="close-settings-btn")
                    
                    with gr.Column(elem_id="settings-content") as settings_content:
                        temperature_slider = gr.Slider(
                            minimum=0,
                            maximum=2,
                            value=0.7,
                            step=0.1,
                            label="Temperature",
                            info="Controls randomness (0=focused, 2=creative)"
                        )
                        
                        system_prompt = gr.Textbox(
                            label="System Prompt",
                            placeholder="You are a helpful AI assistant...",
                            lines=3,
                            value="You are a helpful AI assistant that answers questions based on the provided documents and knowledge base."
                        )
                        
                        text_context = gr.Textbox(
                            label="Text Context",
                            placeholder="Provide additional text context here (optional)...",
                            lines=6,
                            info="Note: Use either uploaded images OR text context, not both"
                        )
                
                # Retriever Settings Panel
                with gr.Column(visible=False, elem_id="kb-settings-modal") as kb_settings_modal:
                    with gr.Row(elem_id="kb-settings-modal-header"):
                        gr.Markdown("### Retriever Settings", elem_id="kb-settings-modal-title")
                        minimize_kb_settings_btn = gr.Button("−", size="sm", elem_id="minimize-kb-settings-btn")
                        maximize_kb_settings_btn = gr.Button("□", size="sm", elem_id="maximize-kb-settings-btn", visible=False)
                        close_kb_settings_btn = gr.Button("✕", size="sm", elem_id="close-kb-settings-btn")
                    
                    with gr.Column(elem_id="kb-settings-content") as kb_settings_content:
                        search_method_dropdown = gr.Dropdown(
                            label="Search Method",
                            choices=search_method_choices,
                            value=search_method_choices[0] if search_method_choices else "Similarity Search",
                            info="Method used to search the knowledge base"
                        )
                        
                        num_documents_slider = gr.Slider(
                            minimum=1,
                            maximum=20,
                            value=5,
                            step=1,
                            label="Number of Documents",
                            info="Number of relevant documents to retrieve"
                        )
                        
                        retriever_query = gr.Textbox(
                            label="Query",
                            placeholder="Enter your retrieval query...",
                            lines=2
                        )
                        
                        retrieve_btn = gr.Button("Retrieve", variant="primary", size="lg")
        
        # Event handlers
        def show_upload_status(files, current_files, txt_context):
            status, updated_files = handle_file_upload(files, current_files)
            if updated_files:
                # Disable text context if files uploaded
                return gr.update(value=status, visible=True), gr.update(value=None), updated_files, gr.update(interactive=False, value="")
            return gr.update(value=status, visible=True), gr.update(value=None), updated_files, gr.update(interactive=True)
        
        def on_text_context_change(txt_context, files):
            # Disable upload button if text context has content
            if txt_context and txt_context.strip():
                return gr.update(interactive=False), {}
            return gr.update(interactive=True), files
        
        def clear_all():
            # Clear everything and re-enable both
            return [], gr.update(interactive=True), gr.update(interactive=True, value="")
        
        def send_message(message, history, model, kb, files, temp, sys_prompt, txt_context):
            if not message or not message.strip():
                return history, "", files
            
            new_history, updated_files = chat_response(
                message, history, model, kb, files, temp, sys_prompt, txt_context
            )
            
            return new_history, "", updated_files
        
        def clear_chat():
            # Clear and re-enable both
            return [], {}, gr.update(interactive=True), gr.update(interactive=True, value="")
        
        def update_kb(kb_name):
            return kb_name
        
        def show_settings():
            return gr.update(visible=True), gr.update(visible=True), gr.update(visible=False)
        
        def show_kb_settings():
            return gr.update(visible=True), gr.update(visible=True), gr.update(visible=False)
        
        def hide_settings():
            return gr.update(visible=False)
        
        def hide_kb_settings():
            return gr.update(visible=False)
        
        def minimize_settings():
            return gr.update(visible=False), gr.update(visible=True)
        
        def maximize_settings():
            return gr.update(visible=True), gr.update(visible=False)
        
        def minimize_kb_settings():
            return gr.update(visible=False), gr.update(visible=True)
        
        def maximize_kb_settings():
            return gr.update(visible=True), gr.update(visible=False)
        
        def handle_retrieve(query, search_method, num_docs):
            """Handle document retrieval"""
            if not query or not query.strip():
                gr.Warning("Please enter a query")
                return
            
            gr.Info(f"Retrieving {num_docs} documents using {search_method}...")
            # TODO: Implement actual retrieval logic
            return
        
        # Wire up events
        upload_btn.upload(
            show_upload_status,
            inputs=[upload_btn, uploaded_files, text_context],
            outputs=[upload_status, upload_btn, uploaded_files, text_context]
        )
        
        text_context.change(
            on_text_context_change,
            inputs=[text_context, uploaded_files],
            outputs=[upload_btn, uploaded_files]
        )
        
        msg_input.submit(
            send_message,
            inputs=[msg_input, chatbot, model_dropdown, current_kb, uploaded_files, temperature_slider, system_prompt, text_context],
            outputs=[chatbot, msg_input, uploaded_files]
        )
        
        clear_btn.click(
            clear_chat,
            outputs=[chatbot, uploaded_files, upload_btn, text_context]
        )
        
        # Wire up KB card buttons
        for i, kb_btn in enumerate(kb_buttons):
            kb_name = kb_list[i]['name']
            kb_btn.click(
                lambda name=kb_name: name,
                outputs=[current_kb]
            ).then(
                show_kb_settings,
                outputs=[kb_settings_modal, kb_settings_content, maximize_kb_settings_btn]
            )
        
        # Wire up chat card buttons (placeholder functionality)
        for chat_btn in chat_buttons:
            chat_btn.click(
                lambda: gr.Info("Loading chat history..."),
                outputs=[]
            )
        
        model_dropdown.change(
            show_settings,
            outputs=[settings_modal, settings_content, maximize_settings_btn]
        )
        
        # Settings modal events
        close_settings_btn.click(
            hide_settings,
            outputs=[settings_modal]
        )
        
        minimize_settings_btn.click(
            minimize_settings,
            outputs=[settings_content, maximize_settings_btn]
        )
        
        maximize_settings_btn.click(
            maximize_settings,
            outputs=[settings_content, maximize_settings_btn]
        )
        
        # KB Settings modal events
        close_kb_settings_btn.click(
            hide_kb_settings,
            outputs=[kb_settings_modal]
        )
        
        minimize_kb_settings_btn.click(
            minimize_kb_settings,
            outputs=[kb_settings_content, maximize_kb_settings_btn]
        )
        
        maximize_kb_settings_btn.click(
            maximize_kb_settings,
            outputs=[kb_settings_content, maximize_kb_settings_btn]
        )
        
        # Retrieve button
        retrieve_btn.click(
            handle_retrieve,
            inputs=[retriever_query, search_method_dropdown, num_documents_slider],
            outputs=[]
        )
    
    # Return everything including state objects
    return (
        main_app,
        logout_btn,
        user_display,
        chatbot,
        new_chat_btn,
        current_kb,
        uploaded_files,
        kb_buttons,
        chat_buttons
    )