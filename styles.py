"""Custom CSS styles for the RAG application UI."""

CUSTOM_CSS = """
.nav-holder {
    display: none !important;
}

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

/* GLOBAL STYLES */
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

/* LOGIN PAGE STYLES */
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

#login-note {
    text-align: center;
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
    border: 2px solid #e1e8f0 !important;
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

/* MAIN APP STYLES */
#main-container {
    background: #fafafa;
}

/* Top bar */
#top-bar {
    background: white;
    border-bottom: 1px solid #eee;
    align-items: center;
    gap: 20px;
    padding-top: 16px;
    padding-bottom: 16px;
}

/* Centered title */
#common-rag-title {
    text-align: center;
    flex: 1;
}

#common-rag-title h2 {
    margin: 0;
    font-size: 36px;
    font-weight: 700;
    color: #485568;
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

/* SIDEBAR STYLES */
#sidebar {
    background: #f8f9fa;
    padding: 16px;
    border-radius: 8px;
}

/* New Chat Button */
#sidebar-new-chat-btn {
    width: 100% !important;
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    font-size: 16px !important;
    box-shadow: 0 2px 6px rgba(79, 70, 229, 0.3);
}

/* Scroll containers */
#kb_scroll,
#chats_scroll {
    height: 180px;
    overflow-y: auto;
    padding: 4px;
}

/* Card Style for KB and Chats */
.kb-card,
.chat-card {
    margin-bottom: 8px !important;
    padding: 0 !important;
}

.kb-card-btn,
.chat-card-btn {
    width: 100% !important;
    background: white !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 12px !important;
    text-align: left !important;
    font-size: 13px !important;
    line-height: 1.5 !important;
    color: #374151 !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    white-space: pre-line !important;
}

.kb-card-btn:hover,
.chat-card-btn:hover {
    background: #f8f9fa !important;
    border-color: #667eea !important;
    box-shadow: 0 2px 6px rgba(102, 126, 234, 0.15) !important;
    transform: translateY(-1px) !important;
}

.kb-card-btn:active,
.chat-card-btn:active {
    transform: translateY(0) !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1) !important;
}

/* Optional: nice scrollbar styling (WebKit-based browsers) */
#kb_scroll::-webkit-scrollbar,
#chats_scroll::-webkit-scrollbar {
    width: 6px;
}

#kb_scroll::-webkit-scrollbar-track,
#chats_scroll::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 3px;
}

#kb_scroll::-webkit-scrollbar-thumb,
#chats_scroll::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 3px;
}

#section-title {
    text-align: center;
    margin: 8px;
}

/* CHAT INTERFACE STYLES */
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
    border: 1px solid #e1e8f0;
    border-radius: 24px;
    padding: 8px 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    margin-top: 12px;
    position: relative;
    z-index: 10;
}

#input-bar {
    background-color: #fff;
    border: 2px solid #e8e8e8;
    border-radius: 24px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 12px;
    padding: 6px 12px;
    min-height: 44px;
    box-sizing: border-box;
}

#input-bar:focus-within {
    border-color: #7a82f7;
    box-shadow: 0 0 8px rgba(122, 130, 247, 0.2);
}

/* Hide the parent gr-group and styler containers that show behind */
.gr-group.svelte-1p92624 {
    background: transparent !important;
}

.styler.svelte-1p92624 {
    background: transparent !important;
}

/* Make sure input bar row has white background */
.row.svelte-7xavid {
    background: transparent !important;
}

#upload-btn {
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    min-height: 36px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 20px !important;
    line-height: 1 !important;
    background: #f3f3f3 !important;
    border: 1px solid #e5e5e5 !important;
}

#upload-btn:hover {
    background: #e9e9e9 !important;
}

#msg-input input,
#msg-input textarea {
    font-size: 15px !important;
    border: none !important;
    background: transparent !important;
    resize: none !important;
    overflow: hidden !important;
}

#msg-input textarea {
    min-height: 20px !important;
    max-height: 20px !important;
}

#model-dropdown {
    min-width: 180px !important;
    max-width: 220px !important;
    height: auto !important;
    min-height: 36px !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 18px !important;
    background: #f9fafb !important;
    padding: 8px 16px !important;
    display: flex !important;
    align-items: center !important;
    font-size: 14px !important;
    color: #374151 !important;
}

#model-dropdown:hover {
    background: #f3f4f6 !important;
    border-color: #d1d5db !important;
}

#model-dropdown select,
#model-dropdown .wrap,
#model-dropdown .wrap-inner {
    width: 100% !important;
    height: auto !important;
    min-height: 20px !important;
}

#model-dropdown label {
    display: none !important;
}

#model-dropdown input,
#model-dropdown textarea {
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
    line-height: 1.4 !important;
}

/* SETTINGS MODAL STYLES */
#settings-modal {
    position: fixed !important;
    right: 20px;
    top: 120px;
    width: 380px;
    max-height: calc(100vh - 140px);
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.15);
    z-index: 1000;
    border: 1px solid #e2e8f0;
    display: flex;
    flex-direction: column;
}

#settings-modal-header {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 16px 20px !important;
    border-bottom: 1px solid #e2e8f0;
    gap: 8px !important;
    flex-shrink: 0;
}

#settings-modal-title {
    flex: 1;
    margin: 0 !important;
    font-size: 18px !important;
    font-weight: 600 !important;
}

#settings-modal-title h3 {
    margin: 0 !important;
    font-size: 18px !important;
}

#settings-content {
    padding: 20px;
    overflow-y: auto;
    flex: 1;
}

#settings-content::-webkit-scrollbar {
    width: 6px;
}

#settings-content::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 3px;
}

#settings-content::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 3px;
}

#minimize-settings-btn,
#maximize-settings-btn,
#close-settings-btn {
    width: 24px !important;
    height: 24px !important;
    min-width: 24px !important;
    padding: 0 !important;
    font-size: 14px !important;
    border-radius: 4px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: #f3f4f6 !important;
    border: 1px solid #e5e7eb !important;
    cursor: pointer !important;
}

#minimize-settings-btn:hover,
#maximize-settings-btn:hover,
#close-settings-btn:hover {
    background: #e5e7eb !important;
}

/* KB Settings Modal */
#kb-settings-modal {
    position: fixed !important;
    left: 20px;
    top: 120px;
    width: 380px;
    max-height: calc(100vh - 140px);
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.15);
    z-index: 1000;
    border: 1px solid #e2e8f0;
    display: flex;
    flex-direction: column;
}

#kb-settings-modal-header {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding: 16px 20px !important;
    border-bottom: 1px solid #e2e8f0;
    gap: 8px !important;
    flex-shrink: 0;
}

#kb-settings-modal-title {
    flex: 1;
    margin: 0 !important;
    font-size: 18px !important;
    font-weight: 600 !important;
}

#kb-settings-modal-title h3 {
    margin: 0 !important;
    font-size: 18px !important;
}

#kb-settings-content {
    padding: 20px;
    overflow-y: auto;
    flex: 1;
}

#kb-settings-content::-webkit-scrollbar {
    width: 6px;
}

#kb-settings-content::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 3px;
}

#kb-settings-content::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 3px;
}

#minimize-kb-settings-btn,
#maximize-kb-settings-btn,
#close-kb-settings-btn {
    width: 24px !important;
    height: 24px !important;
    min-width: 24px !important;
    padding: 0 !important;
    font-size: 14px !important;
    border-radius: 4px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: #f3f4f6 !important;
    border: 1px solid #e5e7eb !important;
    cursor: pointer !important;
}

#minimize-kb-settings-btn:hover,
#maximize-kb-settings-btn:hover,
#close-kb-settings-btn:hover {
    background: #e5e7eb !important;
}

/* When content is hidden during minimize */
#settings-content.hidden,
#kb-settings-content.hidden {
    display: none !important;
}

/* Hide entire modal column when children are all hidden */
#settings-modal:has(> .hide),
#kb-settings-modal:has(> .hide) {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
}

/* Direct approach - hide modal when it contains hidden header */
.column#settings-modal > .hide,
.column#kb-settings-modal > .hide {
    display: none !important;
}

.column#settings-modal:has(.hide) ~ *,
.column#kb-settings-modal:has(.hide) ~ * {
    display: none !important;
}

/* KB CONFIG PAGE STYLES */
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
    background: #fafafc;
    padding: 32px;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
}
"""