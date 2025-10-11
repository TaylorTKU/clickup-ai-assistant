# app.py - ClickUp Construction Assistant with Fixed MMS/Photo Support
# Complete version with working photo attachments

import os
import re
import json
import base64
from io import BytesIO
from datetime import datetime, timedelta
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse
import openai

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# File-based storage for settings (persists across restarts)
SETTINGS_FILE = 'settings.json'

def load_settings():
    """Load settings from file or create defaults"""
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except:
        # Default settings if file doesn't exist
        return {
            'team_members': {
                'mike': {'name': 'Mike', 'role': 'Plumbing'},
                'tom': {'name': 'Tom', 'role': 'Grading'},
                'sarah': {'name': 'Sarah', 'role': 'Electrical'},
                'john': {'name': 'John', 'role': 'General'}
            },
            'job_types': {
                'plumbing': {'name': 'Plumbing', 'keywords': ['plumb', 'pipe', 'water', 'leak', 'faucet', 'valve']},
                'electrical': {'name': 'Electrical', 'keywords': ['electric', 'wire', 'power', 'outlet', 'breaker', 'panel']},
                'grading': {'name': 'Grading', 'keywords': ['grade', 'level', 'excavat', 'dirt', 'soil', 'slope']},
                'concrete': {'name': 'Concrete', 'keywords': ['concrete', 'pour', 'slab', 'foundation', 'cement']},
                'framing': {'name': 'Framing', 'keywords': ['frame', 'wall', 'roof', 'truss', 'stud']},
                'safety': {'name': 'Safety', 'keywords': ['safety', 'danger', 'hazard', 'violation', 'osha']},
                'inspection': {'name': 'Inspection', 'keywords': ['inspect', 'review', 'check', 'permit']}
            },
            'projects': {}  # Will store created projects
        }

def save_settings(settings):
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

# Load initial settings
SETTINGS = load_settings()

def sync_clickup_lists_on_startup():
    """Sync ClickUp lists with local settings on startup"""
    if not CLICKUP_KEY or not WORKSPACE_ID:
        print("⚠️  ClickUp not configured - skipping sync")
        return
    
    headers = {
        'Authorization': CLICKUP_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        print("🔄 Syncing with ClickUp lists...")
        
        # Get all spaces first
        space_response = requests.get(
            f'{BASE_URL}/team/{WORKSPACE_ID}/space',
            headers=headers,
            params={'archived': 'false'},
            timeout=10
        )
        
        if space_response.status_code != 200:
            print(f"⚠️  Could not fetch spaces: {space_response.status_code}")
            return
        
        spaces = space_response.json().get('spaces', [])
        
        # Get lists from each space
        synced_count = 0
        for space in spaces:
            space_id = space['id']
            space_name = space['name']
            
            # Get lists in this space
            list_response = requests.get(
                f'{BASE_URL}/space/{space_id}/list',
                headers=headers,
                params={'archived': 'false'},
                timeout=10
            )
            
            if list_response.status_code == 200:
                lists = list_response.json().get('lists', [])
                
                for lst in lists:
                    # Create simple key from first word of list name
                    list_name = lst['name']
                    simple_key = list_name.lower().split()[0] if list_name else 'unnamed'
                    
                    # Handle duplicates by adding number
                    original_key = simple_key
                    counter = 1
                    while simple_key in SETTINGS['projects']:
                        # Check if it's the same list ID (already synced)
                        if SETTINGS['projects'][simple_key].get('list_id') == lst['id']:
                            break
                        simple_key = f"{original_key}{counter}"
                        counter += 1
                    
                    # Add or update project
                    if simple_key not in SETTINGS['projects'] or SETTINGS['projects'][simple_key].get('list_id') != lst['id']:
                        SETTINGS['projects'][simple_key] = {
                            'list_id': lst['id'],
                            'name': list_name,
                            'space': space_name,
                            'created': lst.get('date_created', ''),
                            'synced': datetime.now().isoformat()
                        }
                        synced_count += 1
                        print(f"  ✅ Synced: {list_name} (use '{simple_key}:' for tasks)")
        
        # Save the synced settings
        save_settings(SETTINGS)
        
        print(f"✅ Sync complete! {synced_count} lists added/updated")
        print(f"📊 Total projects available: {len(SETTINGS['projects'])}")
        
    except Exception as e:
        print(f"⚠️  Error syncing with ClickUp: {e}")
        print("   Continuing with existing settings...")

# Configuration from environment variables
CLICKUP_KEY = os.getenv('CLICKUP_API_KEY', '')
WORKSPACE_ID = os.getenv('WORKSPACE_ID', '')
BASE_URL = 'https://api.clickup.com/api/v2'

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

# OpenAI configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# Startup message
print("=" * 60)
print("🏗️  ClickUp Construction Assistant")
print("=" * 60)
print(f"📌 ClickUp: {'Connected' if CLICKUP_KEY else 'Not configured'}")
print(f"🏢 Workspace: {WORKSPACE_ID if WORKSPACE_ID else 'Not configured'}")
print(f"📱 SMS: {'Enabled' if TWILIO_ACCOUNT_SID else 'Not configured'}")
print(f"🤖 OpenAI: {'Connected' if OPENAI_API_KEY else 'Not configured'}")
print(f"📁 Settings: {SETTINGS_FILE}")
print("=" * 60)

# Sync ClickUp lists on startup (AFTER configuration is loaded)
sync_clickup_lists_on_startup()

# Main interface HTML with project creation support
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>ClickUp Construction Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <style>
        * { 
            margin: 0; 
            padding: 0; 
            box-sizing: border-box; 
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            text-align: center;
            position: relative;
        }
        
        .settings-btn {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.2);
            border: 2px solid white;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            text-decoration: none;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .settings-btn:hover {
            background: white;
            color: #667eea;
        }
        
        .header h1 {
            font-size: 24px;
            margin-bottom: 10px;
        }
        
        .status-bar {
            background: rgba(255,255,255,0.2);
            padding: 8px 15px;
            border-radius: 20px;
            margin-top: 15px;
            font-size: 12px;
            display: inline-block;
        }
        
        .sms-status {
            background: rgba(255,255,255,0.2);
            padding: 5px 10px;
            border-radius: 10px;
            margin-left: 10px;
            font-size: 11px;
        }
        
        .messages {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 12px 18px;
            border-radius: 18px;
            max-width: 85%;
            animation: fadeIn 0.3s ease;
            line-height: 1.6;
        }
        
        @keyframes fadeIn {
            from { 
                opacity: 0; 
                transform: translateY(10px); 
            }
            to { 
                opacity: 1; 
                transform: translateY(0); 
            }
        }
        
        .message.user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
            text-align: right;
        }
        
        .message.ai {
            background: white;
            border: 1px solid #e9ecef;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        
        .message.success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        
        .input-section {
            padding: 20px;
            background: white;
            border-top: 1px solid #e9ecef;
        }
        
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .input-field {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e9ecef;
            border-radius: 25px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        .input-field:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }
        
        .send-btn {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        .send-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102,126,234,0.3);
        }
        
        .select-group {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .select-field {
            flex: 1;
            padding: 10px 15px;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            font-size: 14px;
            background: white;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .select-field:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .quick-actions {
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
        }
        
        .quick-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
        }
        
        .quick-btn {
            padding: 10px;
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
        }
        
        .quick-btn:hover {
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102,126,234,0.2);
        }
        
        .quick-icon {
            font-size: 20px;
            margin-bottom: 4px;
        }
        
        .quick-label {
            font-size: 11px;
            color: #6c757d;
            font-weight: 500;
        }
        
        .task-example {
            background: #f0f8ff;
            border-left: 4px solid #667eea;
            padding: 12px;
            margin: 15px 20px;
            font-size: 13px;
            color: #333;
        }
        
        .task-example strong {
            color: #667eea;
        }
        
        @media (max-width: 600px) {
            .container {
                border-radius: 0;
                height: 100vh;
            }
            .messages {
                height: 350px;
            }
            body {
                padding: 0;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/settings" class="settings-btn">⚙️ Settings</a>
            <h1>🏗️ ClickUp Construction Assistant</h1>
            <p>Create projects and tasks with automatic tracking</p>
            <div class="status-bar" id="status">✅ Connected to ClickUp</div>
            <span class="sms-status" id="smsStatus">📱 SMS Ready</span>
        </div>
        
        <div class="messages" id="messages">
            <div class="message ai">
                👋 Welcome! I can help you create projects and manage tasks.<br><br>
                <strong>Create Projects:</strong><br>
                🏗️ "Create project Oak Street"<br>
                🏗️ "New project Busbee with water and sewer"<br><br>
                <strong>Add Tasks to Projects:</strong><br>
                📝 "oak: Mike needs to fix water leak"<br>
                📝 "Add task for Sarah: Install outlets tomorrow"<br><br>
                <strong>Send Photos via SMS:</strong><br>
                📸 Text a photo with description to create visual task records<br><br>
                Tasks show as <strong>[Name] Task description</strong> in ClickUp!
            </div>
        </div>
        
        <div class="task-example">
            <strong>Examples:</strong><br>
            Create project: "create project Downtown"<br>
            Add to project: "downtown: fix leak" or select project below<br>
            📱 SMS works too! Text commands or photos to your Twilio number
        </div>
        
        <div class="input-section">
            <div class="select-group">
                <select class="select-field" id="projectSelect">
                    <option value="">Auto-detect project</option>
                </select>
                <select class="select-field" id="defaultAssignee">
                    <option value="">No default assignee</option>
                </select>
            </div>
            
            <div class="input-group">
                <input type="text" 
                       class="input-field" 
                       id="userInput" 
                       placeholder="Create project or add task..." 
                       autocomplete="off"
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="send-btn" onclick="sendMessage()">Send</button>
            </div>
        </div>
        
        <div class="quick-actions">
            <div class="quick-grid" id="quickActions">
                <!-- Will be populated dynamically -->
            </div>
        </div>
    </div>
    
    <script>
        // Load settings and projects
        async function loadSettings() {
            try {
                const response = await fetch('/api/settings');
                const settings = await response.json();
                
                // Update project select
                const projectSelect = document.getElementById('projectSelect');
                projectSelect.innerHTML = '<option value="">Auto-detect project</option>';
                
                if (settings.projects) {
                    for (const [key, project] of Object.entries(settings.projects)) {
                        const option = document.createElement('option');
                        option.value = project.list_id;
                        option.textContent = project.name;
                        projectSelect.appendChild(option);
                    }
                }
                
                // Update assignee select
                const select = document.getElementById('defaultAssignee');
                select.innerHTML = '<option value="">No default assignee</option>';
                
                for (const [key, member] of Object.entries(settings.team_members)) {
                    const option = document.createElement('option');
                    option.value = member.name;
                    option.textContent = `${member.name} - ${member.role}`;
                    select.appendChild(option);
                }
                
                // Update quick actions
                updateQuickActions(settings);
                
            } catch (e) {
                console.error('Error loading settings:', e);
            }
        }
        
        function updateQuickActions(settings) {
            const quickActions = document.getElementById('quickActions');
            quickActions.innerHTML = '';
            
            const actions = [
                {icon: '🏗️', label: 'New Project', command: 'create project '},
                {icon: '🚨', label: 'Urgent', command: 'urgent'},
                {icon: '📅', label: 'Tomorrow', command: 'tomorrow'}
            ];
            
            // Add team member actions
            for (const [key, member] of Object.entries(settings.team_members)) {
                if (actions.length < 9) {
                    actions.push({
                        icon: '👤',
                        label: member.name,
                        command: `for ${member.name}: `
                    });
                }
            }
            
            // Create buttons
            actions.forEach(action => {
                const btn = document.createElement('div');
                btn.className = 'quick-btn';
                btn.onclick = () => quickCommand(action.command);
                btn.innerHTML = `
                    <div class="quick-icon">${action.icon}</div>
                    <div class="quick-label">${action.label}</div>
                `;
                quickActions.appendChild(btn);
            });
        }
        
        function quickCommand(command) {
            const input = document.getElementById('userInput');
            
            if (command === 'urgent') {
                input.value = 'Add urgent task: ';
            } else if (command === 'tomorrow') {
                input.value = 'Create task due tomorrow: ';
            } else {
                input.value = command;
            }
            
            input.focus();
        }
        
        function addMessage(text, isUser, isSuccess) {
            const div = document.createElement('div');
            if (isUser) {
                div.className = 'message user';
            } else if (isSuccess === true) {
                div.className = 'message success';
            } else {
                div.className = 'message ai';
            }
            div.innerHTML = text;
            document.getElementById('messages').appendChild(div);
            document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
        }
        
        async function sendMessage() {
            const input = document.getElementById('userInput');
            const msg = input.value.trim();
            if (!msg) return;
            
            const projectSelect = document.getElementById('projectSelect').value;
            const defaultAssignee = document.getElementById('defaultAssignee').value;
            
            addMessage(msg, true);
            input.value = '';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: msg,
                        default_assignee: defaultAssignee,
                        project_list_id: projectSelect
                    })
                });
                
                const data = await response.json();
                addMessage(data.response, false, data.success);
                
                // Reload projects if a new one was created
                if (data.project_created) {
                    loadSettings();
                }
                
                // Update status
                if (data.success) {
                    document.getElementById('status').innerHTML = data.project_created ? 
                        '✅ Project created!' : '✅ Task created!';
                    setTimeout(() => {
                        document.getElementById('status').innerHTML = '✅ Connected to ClickUp';
                    }, 3000);
                }
                
            } catch (error) {
                addMessage('⚠️ Connection error. Please try again.', false, false);
                console.error('Error:', error);
            }
        }
        
        // Check SMS status
        async function checkSmsStatus() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                const smsStatus = document.getElementById('smsStatus');
                if (data.twilio_configured) {
                    smsStatus.innerHTML = '📱 SMS Active';
                    smsStatus.style.background = 'rgba(40, 167, 69, 0.2)';
                } else {
                    smsStatus.innerHTML = '📱 SMS Not Configured';
                    smsStatus.style.background = 'rgba(255, 193, 7, 0.2)';
                }
            } catch (e) {
                console.error('Error checking SMS status:', e);
            }
        }
        
        // Load on page load
        window.onload = function() {
            loadSettings();
            checkSmsStatus();
            document.getElementById('userInput').focus();
        };
        
        // Refresh projects periodically
        setInterval(loadSettings, 30000);
    </script>
</body>
</html>
"""

# Settings page HTML
SETTINGS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Settings - ClickUp Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            text-align: center;
            position: relative;
        }
        
        .back-btn {
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(255,255,255,0.2);
            border: 2px solid white;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            text-decoration: none;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .back-btn:hover {
            background: white;
            color: #667eea;
        }
        
        .settings-section {
            padding: 30px;
        }
        
        .section-title {
            font-size: 20px;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }
        
        .item-list {
            margin-bottom: 30px;
        }
        
        .item {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 10px;
            align-items: center;
        }
        
        .item input {
            flex: 1;
            padding: 8px 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 14px;
        }
        
        .item input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .item button {
            padding: 8px 16px;
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .item button:hover {
            background: #c82333;
        }
        
        .add-btn {
            padding: 10px 20px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 14px;
            margin-bottom: 20px;
            transition: all 0.3s;
        }
        
        .add-btn:hover {
            background: #218838;
            transform: translateY(-2px);
        }
        
        .save-btn {
            padding: 15px 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            display: block;
            margin: 30px auto;
            transition: all 0.3s;
        }
        
        .save-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102,126,234,0.3);
        }
        
        .success-message {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }
        
        .success-message.show {
            display: block;
            animation: fadeIn 0.3s;
        }
        
        .help-text {
            background: #f0f8ff;
            border-left: 4px solid #667eea;
            padding: 12px;
            margin: 20px 0;
            font-size: 13px;
            color: #333;
        }
        
        .project-item {
            background: #e8f4ff;
            border-left: 4px solid #667eea;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-btn">← Back</a>
            <h1>⚙️ Settings</h1>
            <p>Manage team members, job types, and projects</p>
        </div>
        
        <div class="settings-section">
            <div class="success-message" id="successMessage">
                ✅ Settings saved successfully!
            </div>
            
            <div class="section-title">🏗️ Active Projects</div>
            <div class="help-text">
                These projects have been created in ClickUp. Use the project keyword to route tasks.
            </div>
            <div class="item-list" id="projectList"></div>
            
            <div class="section-title">👥 Team Members</div>
            <div class="help-text">
                Team members will appear in task names as [Name]. Example: [Mike] Fix water leak
            </div>
            <div class="item-list" id="teamList"></div>
            <button class="add-btn" onclick="addTeamMember()">+ Add Team Member</button>
            
            <div class="section-title">🔨 Job Types</div>
            <div class="help-text">
                Keywords help categorize tasks automatically. Use comma-separated words.
            </div>
            <div class="item-list" id="jobList"></div>
            <button class="add-btn" onclick="addJobType()">+ Add Job Type</button>
            
            <button class="save-btn" onclick="saveSettings()">💾 Save All Settings</button>
        </div>
    </div>
    
    <script>
        let settings = {
            team_members: {},
            job_types: {},
            projects: {}
        };
        
        async function loadSettings() {
            try {
                const response = await fetch('/api/settings');
                settings = await response.json();
                renderSettings();
            } catch (e) {
                console.error('Error loading settings:', e);
            }
        }
        
        function renderSettings() {
            // Render projects
            const projectList = document.getElementById('projectList');
            projectList.innerHTML = '';
            
            if (settings.projects) {
                for (const [key, project] of Object.entries(settings.projects)) {
                    const item = document.createElement('div');
                    item.className = 'item project-item';
                    item.innerHTML = `
                        <span style="flex: 1"><strong>${project.name}</strong> - Use "${key}:" to add tasks here</span>
                        <button onclick="removeProject('${key}')">Remove</button>
                    `;
                    projectList.appendChild(item);
                }
            }
            
            if (Object.keys(settings.projects || {}).length === 0) {
                projectList.innerHTML = '<p style="color: #666; font-style: italic;">No projects yet. Create one from the main page!</p>';
            }
            
            // Render team members
            const teamList = document.getElementById('teamList');
            teamList.innerHTML = '';
            
            for (const [key, member] of Object.entries(settings.team_members)) {
                const item = document.createElement('div');
                item.className = 'item';
                item.innerHTML = `
                    <input type="text" placeholder="Short ID (e.g., mike)" value="${key}" onchange="updateTeamKey('${key}', this.value)">
                    <input type="text" placeholder="Full Name" value="${member.name}" onchange="updateTeam('${key}', 'name', this.value)">
                    <input type="text" placeholder="Role/Trade" value="${member.role}" onchange="updateTeam('${key}', 'role', this.value)">
                    <button onclick="removeTeam('${key}')">Remove</button>
                `;
                teamList.appendChild(item);
            }
            
            // Render job types
            const jobList = document.getElementById('jobList');
            jobList.innerHTML = '';
            
            for (const [key, job] of Object.entries(settings.job_types)) {
                const item = document.createElement('div');
                item.className = 'item';
                item.innerHTML = `
                    <input type="text" placeholder="ID" value="${key}" onchange="updateJobKey('${key}', this.value)">
                    <input type="text" placeholder="Name" value="${job.name}" onchange="updateJob('${key}', 'name', this.value)">
                    <input type="text" placeholder="Keywords (comma-separated)" value="${job.keywords.join(', ')}" onchange="updateJob('${key}', 'keywords', this.value)" style="flex: 2">
                    <button onclick="removeJob('${key}')">Remove</button>
                `;
                jobList.appendChild(item);
            }
        }
        
        function removeProject(key) {
            if (confirm(`Remove project ${settings.projects[key].name}? This only removes it from settings, not ClickUp.`)) {
                delete settings.projects[key];
                renderSettings();
            }
        }
        
        function updateTeam(key, field, value) {
            if (settings.team_members[key]) {
                settings.team_members[key][field] = value;
            }
        }
        
        function updateTeamKey(oldKey, newKey) {
            if (oldKey !== newKey && settings.team_members[oldKey]) {
                settings.team_members[newKey] = settings.team_members[oldKey];
                delete settings.team_members[oldKey];
                renderSettings();
            }
        }
        
        function removeTeam(key) {
            if (confirm(`Remove ${settings.team_members[key].name}?`)) {
                delete settings.team_members[key];
                renderSettings();
            }
        }
        
        function addTeamMember() {
            const key = 'new' + Date.now();
            settings.team_members[key] = {
                name: 'New Member',
                role: 'General'
            };
            renderSettings();
        }
        
        function updateJob(key, field, value) {
            if (settings.job_types[key]) {
                if (field === 'keywords') {
                    settings.job_types[key][field] = value.split(',').map(k => k.trim()).filter(k => k);
                } else {
                    settings.job_types[key][field] = value;
                }
            }
        }
        
        function updateJobKey(oldKey, newKey) {
            if (oldKey !== newKey && settings.job_types[oldKey]) {
                settings.job_types[newKey] = settings.job_types[oldKey];
                delete settings.job_types[oldKey];
                renderSettings();
            }
        }
        
        function removeJob(key) {
            if (confirm(`Remove ${settings.job_types[key].name}?`)) {
                delete settings.job_types[key];
                renderSettings();
            }
        }
        
        function addJobType() {
            const key = 'newjob' + Date.now();
            settings.job_types[key] = {
                name: 'New Job Type',
                keywords: []
            };
            renderSettings();
        }
        
        async function saveSettings() {
            try {
                const response = await fetch('/api/settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(settings)
                });
                
                if (response.ok) {
                    const successMsg = document.getElementById('successMessage');
                    successMsg.classList.add('show');
                    setTimeout(() => {
                        successMsg.classList.remove('show');
                    }, 3000);
                }
            } catch (e) {
                alert('Error saving settings: ' + e.message);
            }
        }
        
        // Load settings on page load
        window.onload = loadSettings;
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    """Serve the main interface"""
    return render_template_string(HTML_PAGE)

@app.route('/settings')
def settings_page():
    """Serve the settings page"""
    return render_template_string(SETTINGS_PAGE)

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings"""
    return jsonify(SETTINGS)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    global SETTINGS
    try:
        new_settings = request.json
        SETTINGS = new_settings
        save_settings(SETTINGS)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def create_project_in_clickup_with_timeout(project_name, trades=None, timeout=8):
    """Create project with timeout protection"""
    
    headers = {
        'Authorization': CLICKUP_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # Get space with timeout
        space_response = requests.get(
            f'{BASE_URL}/team/{WORKSPACE_ID}/space',
            headers=headers,
            params={'archived': 'false'},
            timeout=timeout
        )
        
        if space_response.status_code != 200:
            return {'success': False, 'error': 'Could not find space'}
        
        spaces = space_response.json().get('spaces', [])
        if not spaces:
            return {'success': False, 'error': 'No spaces found'}
        
        space_id = spaces[0]['id']
        
        # Create list with timeout
        list_data = {
            'name': project_name,
            'content': f'Project created via SMS'
        }
        
        list_response = requests.post(
            f'{BASE_URL}/space/{space_id}/list',
            headers=headers,
            json=list_data,
            timeout=timeout
        )
        
        if list_response.status_code != 200:
            return {'success': False, 'error': 'Could not create project'}
        
        new_list = list_response.json()
        list_id = new_list['id']
        
        # Save to settings (quick operation)
        simple_name = project_name.lower().split()[0]
        if 'projects' not in SETTINGS:
            SETTINGS['projects'] = {}
        
        SETTINGS['projects'][simple_name] = {
            'list_id': list_id,
            'name': project_name,
            'created': datetime.now().isoformat()
        }
        save_settings(SETTINGS)
        
        return {
            'success': True,
            'list_id': list_id,
            'name': project_name,
            'simple_name': simple_name
        }
        
    except requests.exceptions.Timeout:
        print("ClickUp API timeout")
        return {'success': False, 'error': 'ClickUp timeout'}
    except Exception as e:
        print(f"Error creating project: {e}")
        return {'success': False, 'error': str(e)}

def detect_project_from_message(message):
    """Detect which project a task belongs to"""
    lower = message.lower()
    
    # Check for project prefix patterns
    for key, project in SETTINGS.get('projects', {}).items():
        # Check for "project:" or "project -" format
        if lower.startswith(key + ':') or lower.startswith(key + ' -'):
            return project['list_id'], key
        # Check if project name is mentioned
        if key in lower:
            return project['list_id'], key
    
    return None, None

def parse_command_simple(message):
    """Simple parser for SMS - handles various project creation formats"""
    lower = message.lower()
    
    # Check if this is a project creation - handles many variations
    project_indicators = ['create project', 'new project', 'create a project', 
                         'new a project', 'start project', 'start a project',
                         'make project', 'make a project']
    
    is_project_creation = any(indicator in lower for indicator in project_indicators)
    
    if is_project_creation:
        # Extract project name - split by "project" and take everything after
        parts = re.split(r'\s+project\s+', lower, maxsplit=1)
        if len(parts) > 1:
            project_name = parts[1].strip()
            # Remove common connecting words
            connecting_words = ['called', 'named', 'a', 'the', 'is']
            for word in connecting_words:
                # Remove the word if it's at the start
                if project_name.startswith(word + ' '):
                    project_name = project_name[len(word):].strip()
            
            if project_name:
                return {
                    'type': 'create_project',
                    'project_name': project_name.title()
                }
        
        return {'type': 'error', 'message': 'Include project name'}
    
    # Otherwise it's a task
    task_info = {
        'type': 'create_task',
        'name': message,
        'display_name': message,
        'assignee': None,
        'list_id': None
    }
    
    # Check for assignee
    for key, member in SETTINGS['team_members'].items():
        if key.lower() in lower or member['name'].lower() in lower:
            task_info['assignee'] = member['name']
            break
    
    # Check for project
    list_id, project_key = detect_project_from_message(message)
    if list_id:
        task_info['list_id'] = list_id
        # Clean project prefix from name
        for prefix in [f'{project_key}:', f'{project_key} -']:
            if lower.startswith(prefix):
                task_info['name'] = message[len(prefix):].strip()
                break
    
    # Add assignee to display name
    if task_info['assignee']:
        task_info['display_name'] = f"[{task_info['assignee']}] {task_info['name']}"
    
    return task_info

# OpenAI integration functions
def parse_with_openai(message):
    """Use OpenAI to understand complex construction commands"""
    if not OPENAI_API_KEY:
        return None
    
    try:
        # Get list of projects for context
        project_list = ", ".join([f"{key} ({proj['name']})" for key, proj in SETTINGS.get('projects', {}).items()])
        team_list = ", ".join([f"{member['name']} ({member['role']})" for member in SETTINGS['team_members'].values()])
        
        prompt = f"""You are parsing construction site text messages into structured commands.
        
Available projects (use the short key): {project_list}
Team members: {team_list}

Parse this message: "{message}"

Identify if this is:
1. A project creation (return: type=create_project, project_name=name)
2. A task creation (return: type=create_task, name=description, assignee=person if mentioned, project=project_key if mentioned, priority=1-4, due_date=YYYY-MM-DD if mentioned)
3. A safety issue (automatically set priority=1)
4. An inspection (include due date if mentioned)
5. A status update (return: type=status_update, content=update text)

Return a JSON object with the parsed information. For tasks, clean up the language to be professional but keep the meaning.
If it mentions rain, weather delays, or safety issues, mark as urgent (priority=1).

Example input: "Mike found cracks in the foundation at oak street needs fixing asap"
Example output: {{"type": "create_task", "name": "Fix foundation cracks", "assignee": "Mike", "project": "oak", "priority": 1}}
"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"OpenAI parsing error: {e}")
        return None

def handle_mms_image(media_url, message_text, from_number):
    """Process MMS images and create tasks with attachments"""
    try:
        print(f"📸 Downloading image from: {media_url}")
        
        # Download image from Twilio URL
        response = requests.get(
            media_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=10
        )
        
        print(f"Download status: {response.status_code}")
        
        if response.status_code == 200:
            image_data = response.content
            print(f"✅ Image downloaded: {len(image_data)} bytes")
            
            # Create task with description mentioning the photo
            task_description = f"📷 Photo attached\n{message_text}\nFrom: {from_number}"
            
            return {
                'has_image': True,
                'image_data': image_data,
                'description': task_description,
                'media_url': media_url  # Keep URL as backup
            }
        else:
            print(f"❌ Failed to download image: {response.status_code}")
            
    except Exception as e:
        print(f"Error processing MMS: {e}")
    
    return {'has_image': False}

def create_clickup_task_with_attachment(task_info, image_data=None):
    """Enhanced task creation that properly handles attachments"""
    headers = {
        'Authorization': CLICKUP_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # First create the task
        list_id = task_info.get('list_id')
        
        if not list_id:
            # Get first available list or use default
            list_response = requests.get(
                f'{BASE_URL}/team/{WORKSPACE_ID}/list',
                headers=headers,
                timeout=10
            )
            
            if list_response.status_code != 200:
                return {'success': False, 'error': 'Could not find lists'}
            
            lists = list_response.json().get('lists', [])
            if not lists:
                return {'success': False, 'error': 'No lists found'}
            
            list_id = lists[0]['id']
        
        # Create task
        task_data = {
            'name': task_info.get('display_name', task_info.get('name', 'New Task')),
            'description': task_info.get('description', ''),
            'priority': task_info.get('priority', 3),
            'status': 'to do'
        }
        
        if task_info.get('due_date'):
            due_date = datetime.strptime(task_info['due_date'], '%Y-%m-%d')
            task_data['due_date'] = int(due_date.timestamp() * 1000)
        
        print(f"Creating task: {task_data['name']}")
        task_response = requests.post(
            f'{BASE_URL}/list/{list_id}/task',
            headers=headers,
            json=task_data,
            timeout=10
        )
        
        if task_response.status_code == 200:
            task = task_response.json()
            task_id = task['id']
            print(f"✅ Task created: {task_id}")
            
            # If we have an image, attach it
            if image_data:
                try:
                    print(f"📎 Attaching image to task {task_id}")
                    
                    # Create BytesIO object for the image
                    image_file = BytesIO(image_data)
                    image_file.name = 'photo.jpg'
                    
                    attachment_url = f'{BASE_URL}/task/{task_id}/attachment'
                    
                    # Important: Don't include Content-Type for multipart
                    headers_attach = {'Authorization': CLICKUP_KEY}
                    
                    # ClickUp expects 'attachment' as the form field name
                    files = {
                        'attachment': ('photo.jpg', image_file, 'image/jpeg')
                    }
                    
                    attach_response = requests.post(
                        attachment_url,
                        headers=headers_attach,
                        files=files,
                        timeout=15
                    )
                    
                    print(f"Attachment response: {attach_response.status_code}")
                    
                    if attach_response.status_code != 200:
                        print(f"Attachment response body: {attach_response.text}")
                        
                        # If attachment fails, add media URL to description as fallback
                        if task_info.get('media_url'):
                            print("Falling back to URL in description")
                            update_data = {
                                'description': task_data['description'] + f"\n\n📸 Photo: {task_info['media_url']}"
                            }
                            requests.put(
                                f'{BASE_URL}/task/{task_id}',
                                headers=headers,
                                json=update_data,
                                timeout=10
                            )
                    else:
                        print("✅ Image attached successfully!")
                        return {'success': True, 'task': task, 'attachment': True}
                        
                except Exception as e:
                    print(f"Attachment error: {e}")
                    # Task was created, just attachment failed
                    return {'success': True, 'task': task, 'attachment': False}
            
            return {'success': True, 'task': task}
        else:
            print(f"Task creation failed: {task_response.status_code} - {task_response.text}")
            return {'success': False, 'error': 'Could not create task'}
            
    except Exception as e:
        print(f"Error creating task with attachment: {e}")
        return {'success': False, 'error': str(e)}

# Task management functions (rest of the functions remain the same)
def get_clickup_tasks_for_project(project_key):
    """Get all open tasks for a specific project"""
    headers = {
        'Authorization': CLICKUP_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # Get the list ID for this project
        project = SETTINGS.get('projects', {}).get(project_key)
        if not project:
            return {'success': False, 'error': 'Project not found'}
        
        list_id = project['list_id']
        
        # Get tasks from this list
        response = requests.get(
            f'{BASE_URL}/list/{list_id}/task',
            headers=headers,
            params={
                'archived': 'false',
                'statuses[]': ['to do', 'in progress', 'open']  # Only open tasks
            },
            timeout=10
        )
        
        if response.status_code == 200:
            tasks = response.json().get('tasks', [])
            return {'success': True, 'tasks': tasks}
        else:
            return {'success': False, 'error': 'Could not fetch tasks'}
            
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return {'success': False, 'error': str(e)}

def mark_task_complete(task_identifier):
    """Mark a task as complete by ID or partial match"""
    headers = {
        'Authorization': CLICKUP_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # First try to find the task
        task_id = None
        
        if task_identifier.isdigit() or len(task_identifier) <= 10:
            # Direct task ID or short ID
            task_id = task_identifier
        else:
            # Search for task by name across all lists
            for project_key, project in SETTINGS.get('projects', {}).items():
                list_id = project['list_id']
                response = requests.get(
                    f'{BASE_URL}/list/{list_id}/task',
                    headers=headers,
                    params={'archived': 'false'},
                    timeout=10
                )
                
                if response.status_code == 200:
                    tasks = response.json().get('tasks', [])
                    for task in tasks:
                        # Check if identifier matches task name or ID
                        if (task_identifier.lower() in task['name'].lower() or 
                            task_identifier in task.get('id', '') or
                            task.get('id', '').endswith(task_identifier)):
                            task_id = task['id']
                            break
                
                if task_id:
                    break
        
        if not task_id:
            return {'success': False, 'error': 'Task not found'}
        
        # Update task status to complete
        update_response = requests.put(
            f'{BASE_URL}/task/{task_id}',
            headers=headers,
            json={'status': 'complete'},
            timeout=10
        )
        
        if update_response.status_code == 200:
            return {'success': True, 'task_id': task_id}
        else:
            return {'success': False, 'error': 'Could not update task'}
            
    except Exception as e:
        print(f"Error marking task complete: {e}")
        return {'success': False, 'error': str(e)}

def add_comment_to_task(task_id, comment_text):
    """Add a comment/update to a task"""
    headers = {
        'Authorization': CLICKUP_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            f'{BASE_URL}/task/{task_id}/comment',
            headers=headers,
            json={
                'comment_text': comment_text,
                'notify_all': False
            },
            timeout=10
        )
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error adding comment: {e}")
        return False

def build_task_from_ai_result(ai_result, original_message, from_number):
    """Helper to build task info from OpenAI result"""
    task_info = {
        'type': 'create_task',
        'name': ai_result.get('name', original_message),
        'display_name': ai_result.get('name', original_message),
        'priority': ai_result.get('priority', 3),
        'assignee': ai_result.get('assignee'),
        'due_date': ai_result.get('due_date'),
        'description': f"📱 SMS: {original_message}\nFrom: {from_number}\n{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    }
    
    if task_info['assignee']:
        task_info['display_name'] = f"[{task_info['assignee']}] {task_info['name']}"
    
    if ai_result.get('project'):
        for key, proj in SETTINGS['projects'].items():
            if key == ai_result['project']:
                task_info['list_id'] = proj['list_id']
                break
    
    return task_info

# Enhanced SMS handler with fixed MMS support
@app.route('/sms', methods=['POST'])
def handle_sms():
    """Enhanced SMS handler with working MMS photo attachments"""
    
    from_number = request.form.get('From', '')
    message_body = request.form.get('Body', '').strip()
    media_url = request.form.get('MediaUrl0', '')
    num_media = request.form.get('NumMedia', '0')
    
    print(f"📱 SMS from {from_number}: {message_body}")
    if num_media != '0':
        print(f"📸 MMS with {num_media} media files")
    
    resp = MessagingResponse()
    
    try:
        lower = message_body.lower()
        
        # Quick commands
        if lower == "help":
            msg = "Commands:\n"
            msg += "📋 status - projects\n"
            msg += "📝 list [project]\n"
            msg += "✅ done [task#]\n"
            msg += "💬 update [#]: note\n"
            msg += "🏗️ create project\n"
            msg += "🚨 safety issue\n"
            msg += "📸 Send photo"
            resp.message(msg)
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        # List tasks for a project
        if lower.startswith('list'):
            parts = message_body.split(' ', 1)
            if len(parts) > 1:
                project_key = parts[1].strip().lower()
                result = get_clickup_tasks_for_project(project_key)
                
                if result['success']:
                    tasks = result['tasks']
                    if tasks:
                        msg = f"Tasks for {project_key}:\n"
                        for i, task in enumerate(tasks[:10], 1):
                            task_id_short = task['id'][-5:]
                            name = task['name'][:30]
                            msg += f"{task_id_short}: {name}\n"
                            
                            if len(msg) > 140:
                                msg += "...more"
                                break
                    else:
                        msg = f"No open tasks for {project_key}"
                else:
                    msg = "Project not found"
            else:
                msg = "Usage: list [project]"
            
            resp.message(msg)
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        # Mark task as done
        if lower.startswith('done'):
            parts = message_body.split(' ', 1)
            if len(parts) > 1:
                task_identifier = parts[1].strip()
                result = mark_task_complete(task_identifier)
                
                if result['success']:
                    msg = f"✅ Task completed!"
                    add_comment_to_task(
                        result['task_id'],
                        f"Completed via SMS from {from_number}"
                    )
                else:
                    msg = f"❌ Could not complete task"
            else:
                msg = "Usage: done [task#]"
            
            resp.message(msg)
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        # Status command - show projects with task counts
        if lower == "status":
            msg = "Projects:\n"
            if SETTINGS.get('projects'):
                for key, project in SETTINGS['projects'].items():
                    # Get task count
                    result = get_clickup_tasks_for_project(key)
                    count = len(result.get('tasks', [])) if result['success'] else 0
                    msg += f"• {key}: {project['name']} ({count})\n"
                    
                    if len(msg) > 140:
                        remaining = len(SETTINGS['projects']) - len(msg.split('\n')) + 1
                        if remaining > 0:
                            msg += f"...+{remaining} more"
                        break
            else:
                msg = "No projects yet"
            
            resp.message(msg)
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        # Handle photo attachments
        image_data = None
        media_url_backup = None
        if num_media != '0' and media_url:
            mms_result = handle_mms_image(media_url, message_body, from_number)
            if mms_result['has_image']:
                image_data = mms_result['image_data']
                media_url_backup = mms_result.get('media_url')
                if not message_body:
                    message_body = "Site photo"
                message_body = f"📸 {message_body}"
        
        # Safety issue detection
        if any(word in lower for word in ['safety', 'danger', 'hazard', 'emergency', 'urgent', 'accident']):
            project_match = detect_project_from_message(message_body)
            task_info = {
                'type': 'create_task',
                'name': message_body,
                'display_name': f"🚨 SAFETY: {message_body}",
                'priority': 1,
                'list_id': project_match[0] if project_match[0] else None,
                'description': f"⚠️ SAFETY ISSUE\nFrom: {from_number}\n{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'media_url': media_url_backup
            }
            
            # Create the safety task immediately
            if CLICKUP_KEY and WORKSPACE_ID:
                if image_data:
                    created = create_clickup_task_with_attachment(task_info, image_data)
                else:
                    created = create_clickup_task(task_info)
                    
                if created['success']:
                    task_id_short = created['task']['id'][-5:]
                    msg = f"🚨 SAFETY CREATED\nID: {task_id_short}"
