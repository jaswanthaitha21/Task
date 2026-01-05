"""Improved Main chat application UI with better state management"""

import gradio as gr
import os
import base64
from typing import Dict, List, Tuple
from api_utils import call_llm_api

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
        status_msg = "✗ No files uploaded successfully"
    
    return status_msg, current_files

def chat_response(
    message: str, 
    history: List, 
    selected_model: str,
    selected_kb: str,
    uploaded_files: Dict,
    temperature: float = 0.7,
    system_prompt: str = ""
) -> Tuple[List, Dict]:
    """Handle chat messages with proper error handling and KB context"""
    if not message or not message.strip():
        return history, uploaded_files

    try:
        # Prepare context from selected knowledge base (if implemented)
        kb_context = f"\n[Using Knowledge Base: {selected_kb}]" if selected_kb else ""
        enhanced_prompt = f"{system_prompt}{kb_context}"
        
        # Handle image context - use first image if available
        image_context = None
        if uploaded_files:
            first_file = list(uploaded_files.values())[0]
            if first_file['type'].startswith('image/'):
                image_context = first_file['data']
        
        # Call LLM API
        bot_response = call_llm_api(
            model_name=selected_model,
            temperature=temperature,
            prompt=enhanced_prompt,
            query=message,
            image_context=image_context
        )
        
        # Clear uploaded files after use (optional - keep for context)
        # uploaded_files.clear()
        
    except Exception as e:
        print(f"Error in chat_response: {e}")
        bot_response = f"I apologize, but I encountered an error: {str(e)}"
    
    # Append to history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": bot_response})
    
    return history, uploaded_files

def create_main_app(available_models: List[str], kb_list: List[Dict]):
    """Create main application interface with improved state management"""
    
    # Session state
    uploaded_files = gr.State({})
    current_kb = gr.State(kb_list[0]['name'] if kb_list else None)

    with gr.Column() as main_app:
        # Top bar
        with gr.Row(elem_id="top-bar"):
            with gr.Column(elem_id="top-mid", scale=1):
                gr.HTML("<div id='common-rag-title'><h2>Common RAG</h2></div>")
            with gr.Column(elem_id="top-right", scale=1):
                user_display = gr.Textbox(
                    value="", label="", interactive=False, container=False,
                    elem_id="user-display", placeholder="User"
                )
                clear_btn = gr.Button("Clear Chat", size="sm", variant="secondary", elem_id="clear-btn")
                logout_btn = gr.Button("Logout", size="sm", variant="secondary", elem_id="logout-btn")
        
        gr.Markdown("---")

        # Main content area
        with gr.Row(equal_height=True):
            # Left sidebar
            with gr.Column(scale=1, min_width=250):
                new_chat_btn = gr.Button("+ New Chat", size="lg", variant="primary", elem_id="sidebar-new-chat-btn")
                gr.Markdown("---")

                # Knowledge Bases section
                with gr.Group():
                    gr.Markdown("### Knowledge Bases")
                    with gr.Column(elem_classes="scrollable-kb"):
                        kb_radio = gr.Radio(
                            choices=[kb['name'] for kb in kb_list],
                            value=kb_list[0]['name'] if kb_list else None,
                            label="Select Knowledge Base",
                            interactive=True
                        )
                
                gr.Markdown("---")

                # Previous Chats section
                with gr.Group():
                    gr.Markdown("### Previous Chats")
                    with gr.Column(elem_classes="scrollable-chats"):
                        chat_list = gr.Radio(
                            choices=[
                                "Project Q&A (2026-01-03)",
                                "Research Summary (2026-01-02)",
                                "Code Help (2025-12-30)"
                            ],
                            label="Recent conversations",
                            interactive=True
                        )

            # Right side: Chat interface
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(label="", height=450, show_label=False)
                
                # File upload status
                upload_status = gr.Textbox(
                    label="", 
                    interactive=False, 
                    visible=False,
                    elem_id="upload-status"
                )

                # Main input container
                with gr.Group(elem_classes="input-group"):
                    with gr.Row(elem_id="input-bar"):
                        upload_btn = gr.UploadButton(
                            "📎", 
                            file_count="multiple", 
                            size="sm", 
                            elem_id="upload-btn",
                            file_types=["image", ".pdf", ".txt", ".docx", ".md"]
                        )
                        msg_input = gr.Textbox(
                            placeholder="Ask a question about your documents...",
                            show_label=False, 
                            container=False, 
                            elem_id="msg-input", 
                            scale=4, 
                            lines=1
                        )
                        model_dropdown = gr.Dropdown(
                            choices=available_models,
                            value=available_models[0] if available_models else None,
                            show_label=False, 
                            container=False, 
                            scale=1, 
                            elem_id="model-dropdown"
                        )

                # Settings Panel
                with gr.Column(visible=False, elem_id="settings-modal") as settings_modal:
                    with gr.Row():
                        gr.Markdown("### Model Settings")
                        with gr.Row():
                            minimize_settings_btn = gr.Button("−", size="sm", elem_id="minimize-settings-btn")
                            maximize_settings_btn = gr.Button("□", size="sm", elem_id="maximize-settings-btn", visible=False)
                            close_settings_btn = gr.Button("✕", size="sm", elem_id="close-settings-btn")
                    
                    with gr.Column() as settings_content:
                        temperature_slider = gr.Slider(
                            minimum=0, maximum=2, value=0.7, step=0.1,
                            label="Temperature", 
                            info="Controls randomness (0=focused, 2=creative)"
                        )
                        max_tokens_slider = gr.Slider(
                            minimum=100, maximum=4000, value=1000, step=100,
                            label="Max Tokens",
                            info="Maximum response length"
                        )
                        system_prompt = gr.Textbox(
                            label="System Prompt",
                            placeholder="You are a helpful AI assistant...",
                            lines=4,
                            value="You are a helpful AI assistant that answers questions based on the provided documents and knowledge base."
                        )

        # Event handlers
        def show_upload_status(files, current_files):
            status, updated_files = handle_file_upload(files, current_files)
            return gr.update(value=status, visible=True), gr.update(value=None), updated_files

        def send_message(message, history, model, kb, files, temp, sys_prompt):
            if not message or not message.strip():
                return history, "", files
            new_history, updated_files = chat_response(
                message, history, model, kb, files, temp, sys_prompt
            )
            return new_history, "", updated_files

        def clear_chat():
            return [], {}  # Clear chat and uploaded files

        def update_kb(kb_name):
            return kb_name
        
        def show_settings():
            return gr.update(visible=True)

        def hide_settings():
            return (
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False)
            )

        def minimize_settings():
            return gr.update(visible=False), gr.update(visible=True)

        def maximize_settings():
            return gr.update(visible=True), gr.update(visible=False)

        # Wire up events
        upload_btn.upload(
            show_upload_status, 
            inputs=[upload_btn, uploaded_files], 
            outputs=[upload_status, upload_btn, uploaded_files]
        )
        
        msg_input.submit(
            send_message,
            inputs=[msg_input, chatbot, model_dropdown, current_kb, uploaded_files, temperature_slider, system_prompt],
            outputs=[chatbot, msg_input, uploaded_files]
        )
        
        clear_btn.click(
            clear_chat, 
            outputs=[chatbot, uploaded_files]
        )
        
        kb_radio.change(
            update_kb,
            inputs=[kb_radio],
            outputs=[current_kb]
        )
        
        model_dropdown.change(show_settings, outputs=[settings_modal])
        
        close_settings_btn.click(
            hide_settings,
            outputs=[settings_modal, settings_content, maximize_settings_btn]
        )
        
        minimize_settings_btn.click(
            minimize_settings,
            outputs=[settings_content, maximize_settings_btn]
        )
        
        maximize_settings_btn.click(
            maximize_settings,
            outputs=[settings_content, maximize_settings_btn]
        )

        # Return everything including state objects
        return (
            main_app,
            logout_btn,
            user_display,
            chatbot,
            new_chat_btn,
            current_kb,
            uploaded_files
        )