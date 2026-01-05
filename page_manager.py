# page_manager.py
import gradio as gr

class PageManager:
    def __init__(self):
        self.pages = {}

    def register(self, name: str, container: gr.Column):
        self.pages[name] = container

    def switch(self, page_name: str):
        updates = []
        for name, container in self.pages.items():
            updates.append(gr.update(visible=(name == page_name)))
        return updates
