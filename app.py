"""Common RAG Application - Multipage with Proper Auth & No Navbar
Fixed: Authentication blocking + Navbar completely hidden
"""

import gradio as gr
from auth_manager import AuthManager
from styles import CUSTOM_CSS
from api_utils import fetch_available_models
from auth_ui import create_login_page
from main_ui import create_main_app
from kb_config_ui import create_kb_config_page

# Initialize
auth_manager = AuthManager()
AVAILABLE_MODELS = fetch_available_models()
DUMMY_KNOWLEDGE_BASES = [
    {"name": "Project Documentation", "created": "2024-12-10"},
    {"name": "Research Papers", "created": "2024-12-15"},
    {"name": "Code Repository", "created": "2024-12-18"},
]

# Global state for current user
current_user = {"username": None, "selected_kb": None}

# ============================================================================
# AUTHENTICATION HANDLERS
# ============================================================================

def perform_signup(username, password, email):
    """Handle user signup"""
    if not username or not password:
        gr.Warning("Username and password are required")
        return
    if email and "@" not in email:
        gr.Warning("Please enter a valid email address")
        return
    success, message = auth_manager.signup(username, password, email)
    if success:
        gr.Info(message)
    else:
        gr.Warning(message)

def perform_logout():
    """Handle user logout"""
    current_user["username"] = None
    gr.Info("Logged out successfully")
    return []

# ============================================================================
# CREATE MAIN APP WITH ROUTING
# ============================================================================

# CSS to completely hide navbar
HIDE_NAVBAR_CSS = CUSTOM_CSS + """
/* Completely hide the navbar */
.gradio-page header,
nav,
.navbar,
[role="navigation"],
.tabs-wrapper > .tab-container {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
}

/* Remove top padding/margin where navbar was */
.gradio-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

main > .contain {
    padding-top: 0 !important;
}
"""

with gr.Blocks(
    title="Common RAG",
    css=HIDE_NAVBAR_CSS,
    head="""
    <script>
        // Hide navbar elements on load
        document.addEventListener('DOMContentLoaded', function() {
            const styles = document.createElement('style');
            styles.innerHTML = `
                nav, .navbar, header[role="banner"], [role="navigation"] {
                    display: none !important;
                }
            `;
            document.head.appendChild(styles);
        });
    </script>
    """
) as demo:
    
    # ========================================================================
    # LOGIN PAGE (Main/Home Page)
    # ========================================================================
    (
        login_page,
        login_username,
        login_password,
        login_btn,
        login_msg,
        signup_username,
        signup_email,
        signup_password,
        signup_btn
    ) = create_login_page()
    
    # Add hidden textbox to receive login result
    login_success = gr.Textbox(visible=False, elem_id="login-success-flag")
    
    # Wire up login with conditional navigation
    def login_handler(username, password):
        success, message = auth_manager.login(username, password)
        if success:
            current_user["username"] = username
            gr.Info(f"Welcome back, {username}!")
            return "SUCCESS"
        else:
            gr.Warning(message)
            return "FAILED"
    
    login_btn.click(
        login_handler,
        inputs=[login_username, login_password],
        outputs=[login_success]
    ).then(
        None,
        inputs=[login_success],
        outputs=None,
        js="""
        (status) => {
            if (status === "SUCCESS") {
                window.location.href = '/chat';
            }
        }
        """
    )
    
    signup_btn.click(
        perform_signup,
        inputs=[signup_username, signup_password, signup_email],
        outputs=[]
    )

# ============================================================================
# CHAT PAGE (Separate Route) - PROTECTED
# ============================================================================
with demo.route("Chat", "/chat"):
    
    # Auth check component
    auth_status = gr.HTML(visible=False, elem_id="auth-status")
    
    (
        main_app,
        logout_btn,
        user_display,
        chatbot,
        new_chat_btn,
        current_kb_state,
        uploaded_files_state
    ) = create_main_app(AVAILABLE_MODELS, DUMMY_KNOWLEDGE_BASES)
    
    # Authentication check on page load - BLOCKING
    def check_chat_auth():
        if not current_user['username']:
            # Return HTML that will trigger redirect
            return '<div data-redirect="true"></div>'
        return f'<div data-redirect="false">{current_user["username"]}</div>'
    
    demo.load(
        check_chat_auth,
        outputs=[auth_status]
    ).then(
        None,
        inputs=[auth_status],
        outputs=None,
        js="""
        (html) => {
            const div = document.createElement('div');
            div.innerHTML = html;
            const redirect = div.querySelector('[data-redirect="true"]');
            if (redirect) {
                alert('⚠️ Please login first to access this page');
                window.location.href = '/';
            } else {
                // Update user display
                const username = div.textContent;
                const userDisplay = document.querySelector('#user-display input, #user-display textarea');
                if (userDisplay && username) {
                    userDisplay.value = '👤 ' + username;
                }
            }
        }
        """
    )
    
    # Wire up New Chat button navigation
    new_chat_btn.click(
        None,
        None,
        None,
        js="() => { window.location.href = '/kb-config'; }"
    )
    
    # Wire up logout with navigation
    logout_btn.click(
        perform_logout,
        outputs=[chatbot]
    ).then(
        None,
        None,
        None,
        js="() => { window.location.href = '/'; }"
    )

# ============================================================================
# KB CONFIG PAGE (Separate Route) - PROTECTED
# ============================================================================
with demo.route("Create Knowledge Base", "/kb-config"):
    
    # Auth check component
    kb_auth_status = gr.HTML(visible=False, elem_id="kb-auth-status")
    
    import kb_config_ui
    
    (
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
    ) = create_kb_config_page()
    
    # Authentication check on page load - BLOCKING
    def check_kb_auth():
        if not current_user['username']:
            return '<div data-redirect="true"></div>'
        return '<div data-redirect="false"></div>'
    
    demo.load(
        check_kb_auth,
        outputs=[kb_auth_status]
    ).then(
        None,
        inputs=[kb_auth_status],
        outputs=None,
        js="""
        (html) => {
            const div = document.createElement('div');
            div.innerHTML = html;
            const redirect = div.querySelector('[data-redirect="true"]');
            if (redirect) {
                alert('⚠️ Please login first to access this page');
                window.location.href = '/';
            }
        }
        """
    )
    
    # Wire up back button navigation
    back_btn.click(
        None,
        None,
        None,
        js="() => { window.location.href = '/chat'; }"
    )
    
    # Wire up KB creation
    create_vector_btn.click(
        kb_config_ui.create_vector_store,
        inputs=[
            kb_name_input,
            kb_files_upload,
            split_method,
            chunk_size,
            chunk_overlap,
            embedding_model,
            vector_store
        ],
        outputs=[kb_create_status]
    )

if __name__ == "__main__":
    demo.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7867
    )