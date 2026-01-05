"""Custom CSS styles for the RAG application - Multipage Compatible"""

CUSTOM_CSS = """
/* ========================================
   GLOBAL STYLES
   ======================================== */
.gradio-container {
    max-width: 100% !important;
    padding: 0 !important;
}

main, .contain {
    max-width: 100% !important;
}

/* Remove min-height constraints that cause scrolling */
.gradio-container, main {
    min-height: auto !important;
}

/* ========================================
   LOGIN PAGE STYLES
   ======================================== */
#login-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 40px 20px;
}

#login-container .column {
    background: white;
    border-radius: 16px;
    padding: 40px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    max-width: 500px;
    width: 100%;
}

#welcome-title h1 {
    text-align: center;
    color: #2d3748 !important;
    font-size: 32px !important;
    font-weight: 700 !important;
    margin-bottom: 10px !important;
}

/* Input fields */
input, textarea {
    font-size: 15px !important;
    padding: 12px !important;
    border: 2px solid #e2e8f0 !important;
    border-radius: 8px !important;
}

input:focus, textarea:focus {
    border-color: #667eea !important;
    outline: none !important;
}

/* Login/Signup Buttons */
#login-button,
#signup-button {
    width: 100% !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 14px !important;
    border-radius: 8px !important;
    font-size: 16px !important;
    margin-top: 10px !important;
}

/* ========================================
   MAIN APP STYLES
   ======================================== */
#main-container {
    background: #f8f9fa;
}

/* Top bar */
#top-bar {
    padding: 16px 24px;
    background: white;
    border-bottom: 1px solid #e0e0e0;
    align-items: center;
    gap: 20px;
}

/* Centered title */
#common-rag-title {
    text-align: center;
    flex: 1;
}

#common-rag-title h2 {
    margin: 0;
    font-size: 28px;
    font-weight: 700;
    color: #4a5568;
}

/* Right-side controls */
#top-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
}

#user-display {
    font-size: 14px;
    font-weight: 600;
    color: #2d3748;
    background: transparent !important;
    border: none !important;
    padding: 4px 8px !important;
    text-align: right;
}

#clear-btn, #logout-btn {
    height: 32px !important;
    min-width: 100px !important;
    font-size: 13px !important;
    border-radius: 6px !important;
}

/* ========================================
   SIDEBAR STYLES
   ======================================== */

/* New Chat Button */
#sidebar-new-chat-btn {
    width: 100% !important;
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 12px !important;
    border-radius: 8px !important;
    font-size: 16px !important;
    box-shadow: 0 2px 6px rgba(79, 70, 229, 0.3);
    margin-bottom: 16px !important;
}

/* Scrollable sections */
.scrollable-kb,
.scrollable-chats {
    max-height: 300px;
    overflow-y: auto;
    padding: 8px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #f8fafc;
}

.scrollable-kb::-webkit-scrollbar,
.scrollable-chats::-webkit-scrollbar {
    width: 6px;
}

.scrollable-kb::-webkit-scrollbar-track,
.scrollable-chats::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 3px;
}

.scrollable-kb::-webkit-scrollbar-thumb,
.scrollable-chats::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 3px;
}

/* ========================================
   CHAT INTERFACE STYLES
   ======================================== */

/* Upload status */
#upload-status {
    background: #f0fdf4;
    border: 1px solid #86efac;
    border-radius: 8px;
    padding: 12px;
    color: #166534;
    margin-bottom: 12px;
}

/* Input area */
.input-group {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 24px;
    padding: 8px 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-top: 12px;
}

#input-bar {
    gap: 12px;
    align-items: center;
}

#upload-btn {
    background: #f3f4f6 !important;
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    font-size: 18px !important;
}

#msg-input input,
#msg-input textarea {
    font-size: 15px !important;
    border: none !important;
    background: transparent !important;
}

/* ========================================
   SETTINGS MODAL STYLES
   ======================================== */
#settings-modal {
    position: fixed !important;
    right: 20px;
    top: 120px;
    width: 360px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.15);
    padding: 24px;
    z-index: 1000;
    border: 1px solid #e2e8f0;
}

#minimize-settings-btn,
#maximize-settings-btn,
#close-settings-btn {
    width: 32px !important;
    height: 32px !important;
    padding: 0 !important;
    font-size: 18px !important;
    border-radius: 6px !important;
}

/* ========================================
   KB CONFIG PAGE STYLES
   ======================================== */
#kb-config-container {
    background: white;
}

#kb-config-page {
    padding: 24px;
    background: white;
}

#kb-config-header {
    align-items: center;
    margin-bottom: 24px;
}

#kb-config-title {
    text-align: center;
    flex: 1;
}

#kb-config-form {
    max-width: 800px;
    margin: 0 auto;
    background: #f8fafc;
    padding: 32px;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
}
"""