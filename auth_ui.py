"""Authentication UI components: Login and Signup pages"""

import gradio as gr

def create_login_page():
    """Create login/signup page with proper layout"""
    with gr.Column(elem_id="login-page") as login_page:
        # Title
        gr.Markdown(
            "# Welcome to Common RAG",
            elem_id="welcome-title"
        )
        
        gr.Markdown("---")
        
        # Centered container for login/signup
        with gr.Row():
            gr.Column(scale=1)  # Left spacer
            
            with gr.Column(scale=2, min_width=400):
                with gr.Tabs() as tabs:
                    # Login Tab
                    with gr.Tab("Login"):
                        with gr.Column():
                            gr.Markdown("### Sign in to your account")
                            
                            login_username = gr.Textbox(
                                label="Username",
                                placeholder="Enter your username"
                            )
                            
                            login_password = gr.Textbox(
                                label="Password",
                                type="password",
                                placeholder="Enter your password"
                            )
                            
                            login_msg = gr.Textbox(
                                label="",
                                interactive=False,
                                visible=False,
                                elem_id="login-message"
                            )
                            
                            login_btn = gr.Button(
                                "Login",
                                variant="primary",
                                size="lg",
                                elem_id="login-button"
                            )
                            
                            gr.Markdown("---")
                            gr.Markdown("*Don't have an account? Switch to Sign Up tab*", elem_id="login-note")
                    
                    # Sign Up Tab
                    with gr.Tab("Sign Up"):
                        with gr.Column():
                            gr.Markdown("### Create a new account")
                            
                            signup_username = gr.Textbox(
                                label="Username",
                                placeholder="Choose a username",
                                elem_id="signup-username"
                            )
                            
                            signup_email = gr.Textbox(
                                label="Email (optional)",
                                placeholder="Enter your email address",
                                elem_id="signup-email"
                            )
                            
                            signup_password = gr.Textbox(
                                label="Password",
                                type="password",
                                placeholder="Choose a strong password",
                                elem_id="signup-password"
                            )
                            
                            signup_btn = gr.Button(
                                "Sign Up",
                                variant="primary",
                                size="lg",
                                elem_id="signup-button"
                            )
                            
                            gr.Markdown("---")
                            gr.Markdown("*Already have an account? Switch to Login tab*")
            
            gr.Column(scale=1)  # Right spacer
    
    return (
        login_page,
        login_username,
        login_password,
        login_btn,
        login_msg,
        signup_username,
        signup_email,
        signup_password,
        signup_btn
    )