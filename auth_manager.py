import json
import hashlib
import os
from datetime import datetime

class AuthManager:
    def __init__(self, users_file='users.json'):
        self.users_file = users_file
        self.ensure_users_file()
    
    def ensure_users_file(self):
        """Create users file if it doesn't exist"""
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w') as f:
                json.dump({}, f)
    
    def hash_password(self, password):
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def signup(self, username, password, email=""):
        """Register a new user"""
        if not username or not password:
            return False, "Username and password are required"
        
        # Load existing users
        with open(self.users_file, 'r') as f:
            users = json.load(f)
        
        # Check if user already exists
        if username in users:
            return False, "Username already exists"
        
        # Create new user
        users[username] = {
            'password': self.hash_password(password),
            'email': email,
            'created_at': datetime.now().isoformat(),
            'rag_pipelines': [],
            'chat_history': []
        }
        
        # Save users
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)
        
        return True, "Signup successful! Please login."
    
    def login(self, username, password):
        """Authenticate user"""
        if not username or not password:
            return False, "Username and password are required"
        
        # Load users
        with open(self.users_file, 'r') as f:
            users = json.load(f)
        
        # Check credentials
        if username not in users:
            return False, "Invalid username or password"
        
        if users[username]['password'] != self.hash_password(password):
            return False, "Invalid username or password"
        
        return True, "Login successful!"
    
    def get_user_data(self, username):
        """Get user data"""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
        
        return users.get(username, {})
    
    def update_user_data(self, username, data):
        """Update user data"""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
        
        if username in users:
            users[username].update(data)
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
            return True
        
        return False
    
    def add_rag_pipeline(self, username, pipeline_name):
        """Add a RAG pipeline for user"""
        user_data = self.get_user_data(username)
        if 'rag_pipelines' not in user_data:
            user_data['rag_pipelines'] = []
        
        pipeline_info = {
            'name': pipeline_name,
            'created_at': datetime.now().isoformat(),
            'documents': []
        }
        
        user_data['rag_pipelines'].append(pipeline_info)
        self.update_user_data(username, user_data)
        
        return pipeline_info
    
    def get_rag_pipelines(self, username):
        """Get all RAG pipelines for user"""
        user_data = self.get_user_data(username)
        return user_data.get('rag_pipelines', [])