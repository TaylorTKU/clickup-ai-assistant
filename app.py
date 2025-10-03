# app.py - ClickUp Construction Assistant - Complete Fixed Version
# Assignees show in task names - no ClickUp accounts needed for field workers!

import os
import re
import json
from datetime import datetime, timedelta
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

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
            }
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

# Main interface HTML
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
        
        .team-select {
            width: 100%;
            padding: 10px 15px;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            font-size: 14px;
            background: white;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .team-select:focus {
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
            <p>Create tasks with automatic assignee tracking</p>
            <div class="status-bar" id="status">✅ Connected to ClickUp</div>
        </div>
        
        <div class="messages" id="messages">
            <div class="message ai">
                👋 Welcome! I'll help you create and track tasks with assignees.<br><br>
                <strong>Try these commands:</strong><br>
                📝 "Add urgent task for Mike: Fix water leak"<br>
                📅 "Sarah needs to install outlets tomorrow"<br>
                🔨 "Tom should grade the parking lot by Friday"<br><br>
                Tasks will show as <strong>[Name] Task description</strong> in ClickUp!
            </div>
        </div>
        
        <div class="task-example">
            <strong>How tasks appear in ClickUp:</strong><br>
            [Mike] Fix water leak at Building A<br>
            [Sarah] Install outlets in Unit 5<br>
            [Tom] Grade parking lot
        </div>
        
        <div class="input-section">
            <div class="input-group">
                <input type="text" 
                       class="input-field" 
                       id="userInput" 
                       placeholder="Type a command..." 
                       autocomplete="off"
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="send-btn" onclick="sendMessage()">Send</button>
            </div>
            
            <select class="team-select" id="defaultAssignee">
                <option value="">No default assignee</option>
            </select>
        </div>
        
        <div class="quick-actions">
            <div class="quick-grid" id="quickActions">
                <!-- Will be populated dynamically -->
            </div>
        </div>
    </div>
    
    <script>
        // Load team members and job types
        async function loadSettings() {
            try {
                const response = await fetch('/api/settings');
                const settings = await response.json();
                
                // Update team select
                const select = document.getElementById('defaultAssignee');
                select.innerHTML = '<option value="">No default assignee</option>';
                
                for (const [key, member] of Object.entries(settings.team_members)) {
                    const option = document.createElement('option');
                    option.value = member.name;
                    option.textContent = `${member.name} - ${member.role}`;
                    select.appendChild(option);
                }
                
                // Update quick actions
                const quickActions = document.getElementById('quickActions');
                quickActions.innerHTML = '';
                
                // Add urgent and date actions
                const actions = [
                    {icon: '🚨', label: 'Urgent', command: 'urgent'},
                    {icon: '📅', label: 'Tomorrow', command: 'tomorrow'},
                    {icon: '📆', label: 'Friday', command: 'friday'}
                ];
                
                // Add team member actions
                for (const [key, member] of Object.entries(settings.team_members)) {
                    actions.push({
                        icon: '👤',
                        label: member.name,
                        command: `for ${member.name}: `
                    });
                }
                
                // Add job type actions
                const jobIcons = {
                    'plumbing': '🔧',
                    'electrical': '⚡',
                    'grading': '🚜',
                    'concrete': '🏗️',
                    'framing': '🏠',
                    'safety': '⚠️',
                    'inspection': '🔍'
                };
                
                for (const [key, job] of Object.entries(settings.job_types)) {
                    if (actions.length < 12) { // Limit quick actions
                        actions.push({
                            icon: jobIcons[key] || '📋',
                            label: job.name,
                            command: `${key}`
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
                
            } catch (e) {
                console.error('Error loading settings:', e);
            }
        }
        
        function quickCommand(command) {
            const input = document.getElementById('userInput');
            
            if (command === 'urgent') {
                input.value = 'Add urgent task: ';
            } else if (command === 'tomorrow') {
                input.value = 'Create task due tomorrow: ';
            } else if (command === 'friday') {
                input.value = 'Schedule for Friday: ';
            } else if (command.startsWith('for ')) {
                input.value = `Add task ${command}`;
            } else {
                input.value = `Add ${command} task: `;
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
            
            const defaultAssignee = document.getElementById('defaultAssignee').value;
            
            addMessage(msg, true);
            input.value = '';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: msg,
                        default_assignee: defaultAssignee
                    })
                });
                
                const data = await response.json();
                addMessage(data.response, false, data.success);
                
                // Update status
                if (data.success) {
                    document.getElementById('status').innerHTML = '✅ Task created successfully!';
                    setTimeout(() => {
                        document.getElementById('status').innerHTML = '✅ Connected to ClickUp';
                    }, 3000);
                }
                
            } catch (error) {
                addMessage('⚠️ Connection error. Please try again.', false, false);
                console.error('Error:', error);
            }
        }
        
        // Load settings on page load
        window.onload = function() {
            loadSettings();
            document.getElementById('userInput').focus();
        };
        
        // Check connection periodically
        setInterval(async () => {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                if (!data.clickup) {
                    document.getElementById('status').innerHTML = '⚠️ ClickUp not configured';
                }
            } catch (e) {
                document.getElementById('status').innerHTML = '⚠️ Connection issue';
            }
        }, 30000);
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-btn">← Back</a>
            <h1>⚙️ Settings</h1>
            <p>Manage team members and job types</p>
        </div>
        
        <div class="settings-section">
            <div class="success-message" id="successMessage">
                ✅ Settings saved successfully!
            </div>
            
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
            job_types: {}
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

# Configuration from environment variables
CLICKUP_KEY = os.getenv('CLICKUP_API_KEY', '')
WORKSPACE_ID = os.getenv('WORKSPACE_ID', '')
BASE_URL = 'https://api.clickup.com/api/v2'

# Startup message
print("=" * 60)
print("🏗️  ClickUp Construction Assistant")
print("=" * 60)
print(f"📌 ClickUp: {'Connected' if CLICKUP_KEY else 'Not configured'}")
print(f"🏢 Workspace: {WORKSPACE_ID if WORKSPACE_ID else 'Not configured'}")
print(f"📁 Settings: {SETTINGS_FILE}")
print(f"👥 Assignees: Show in task names [Name] format")
print("=" * 60)

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

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process chat messages and create tasks"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        default_assignee = data.get('default_assignee', '')
        
        if not message:
            return jsonify({'response': 'Please provide a message', 'success': False})
        
        # Parse the command
        task_info = parse_command(message, default_assignee)
        
        # Create the task in ClickUp
        if CLICKUP_KEY and WORKSPACE_ID:
            result = create_task_in_clickup(task_info)
        else:
            result = {
                'response': f"📝 Task noted locally: '{task_info['display_name']}'<br>⚠️ Configure ClickUp API in environment variables to sync",
                'success': False
            }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({
            'response': '⚠️ An error occurred. Please try again.',
            'success': False
        })

def parse_command(message, default_assignee=''):
    """Parse natural language command to extract task details - FIXED VERSION"""
    
    original_message = message
    lower = message.lower()
    
    # Initialize task info
    task_info = {
        'name': message,  # Original task name without assignee
        'display_name': message,  # Task name with [Assignee] prefix
        'priority': 3,  # Normal
        'assignee': default_assignee,
        'due_date': None,
        'description': '',
        'tags': []
    }
    
    # Extract priority
    if any(word in lower for word in ['urgent', 'emergency', 'critical', 'asap']):
        task_info['priority'] = 1  # Urgent
        task_info['tags'].append('URGENT')
    elif any(word in lower for word in ['high', 'important']):
        task_info['priority'] = 2  # High
    elif any(word in lower for word in ['low', 'whenever']):
        task_info['priority'] = 4  # Low
    
    # Safety issues are always urgent
    if 'safety' in lower:
        task_info['priority'] = 1
        task_info['tags'].append('SAFETY')
    
    # Extract assignee from team members - FIXED VERSION with word boundaries
    assignee_found = False
    for key, member in SETTINGS['team_members'].items():
        member_name = member['name'].lower()
        key_lower = key.lower()
        
        # Create patterns that check for whole words only
        patterns = [
            f"\\bfor {key_lower}\\b",  # "for mike"
            f"\\bfor {member_name}\\b",  # "for Mike"
            f"\\bto {key_lower}\\b",  # "to mike"
            f"\\bto {member_name}\\b",  # "to Mike"
            f"\\bassign to {key_lower}\\b",  # "assign to mike"
            f"\\bassign to {member_name}\\b",  # "assign to Mike"
            f"\\b{key_lower} needs to\\b",  # "mike needs to"
            f"\\b{member_name} needs to\\b",  # "Mike needs to"
            f"\\b{key_lower} should\\b",  # "mike should"
            f"\\b{member_name} should\\b",  # "Mike should"
            f"\\b{key_lower} must\\b",  # "mike must"
            f"\\b{member_name} must\\b",  # "Mike must"
            f"\\b{key_lower}:\\b",  # "mike:"
            f"\\b{member_name}:\\b",  # "Mike:"
        ]
        
        # Check each pattern
        for pattern in patterns:
            if re.search(pattern, lower, re.IGNORECASE):
                task_info['assignee'] = member['name']
                assignee_found = True
                print(f"Found assignee '{member['name']}' using pattern '{pattern}'")
                break
        
        if assignee_found:
            break
    
    # Extract due date - do this AFTER assignee to avoid conflicts
    today = datetime.now()
    
    if 'tomorrow' in lower:
        task_info['due_date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'today' in lower:
        task_info['due_date'] = today.strftime('%Y-%m-%d')
    elif re.search(r'\bfriday\b', lower):  # Use word boundary for friday
        days_until = (4 - today.weekday()) % 7
        if days_until == 0:
            days_until = 7
        task_info['due_date'] = (today + timedelta(days=days_until)).strftime('%Y-%m-%d')
    elif re.search(r'\bmonday\b', lower):  # Use word boundary for monday
        days_until = (0 - today.weekday()) % 7
        if days_until == 0:
            days_until = 7
        task_info['due_date'] = (today + timedelta(days=days_until)).strftime('%Y-%m-%d')
    
    # Detect job type and add as tag
    for job_key, job_data in SETTINGS['job_types'].items():
        for keyword in job_data.get('keywords', []):
            if keyword.lower() in lower:
                task_info['tags'].append(job_data['name'])
                break
    
    # Clean up task name (remove command words and assignee references)
    clean_name = original_message
    
    # Remove command prefixes
    clean_name = re.sub(r'^(add|create|schedule|new)\s+(task\s+)?', '', clean_name, flags=re.IGNORECASE)
    
    # Remove priority words
    clean_name = re.sub(r'\b(urgent|emergency|high priority|low priority|asap)\b\s*', '', clean_name, flags=re.IGNORECASE)
    
    # Remove assignee phrases - be more careful with word boundaries
    for key, member in SETTINGS['team_members'].items():
        member_name = member['name']
        key_lower = key.lower()
        
        # Remove variations of assignee mentions with word boundaries
        patterns_to_remove = [
            f'\\bfor {key_lower}\\b',
            f'\\bfor {member_name}\\b',
            f'\\bto {key_lower}\\b',
            f'\\bto {member_name}\\b',
            f'\\bassign to {key_lower}\\b',
            f'\\bassign to {member_name}\\b',
            f'\\b{key_lower} needs to\\b',
            f'\\b{member_name} needs to\\b',
            f'\\b{key_lower} should\\b',
            f'\\b{member_name} should\\b',
            f'\\b{key_lower} must\\b',
            f'\\b{member_name} must\\b',
            f'\\b{key_lower}:\\b',
            f'\\b{member_name}:\\b',
        ]
        
        for pattern in patterns_to_remove:
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
    
    # Remove due date phrases - be careful with word boundaries
    clean_name = re.sub(r'\b(due tomorrow|by tomorrow|tomorrow)\b', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\b(due today|by today|today)\b', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\b(due friday|by friday|friday)\b', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'\b(due monday|by monday|monday)\b', '', clean_name, flags=re.IGNORECASE)
    
    # Clean up punctuation and extra spaces
    clean_name = re.sub(r':\s*', '', clean_name)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    
    # Set the cleaned task name
    if clean_name:
        task_info['name'] = clean_name
    
    # Create display name with [Assignee] prefix
    if task_info['assignee']:
        task_info['display_name'] = f"[{task_info['assignee']}] {task_info['name']}"
    else:
        task_info['display_name'] = task_info['name']
    
    # Build description
    desc_parts = []
    desc_parts.append(f"📱 Created via Construction Assistant")
    
    if task_info['assignee']:
        desc_parts.append(f"👤 Assigned to: {task_info['assignee']}")
    
    if task_info['due_date']:
        desc_parts.append(f"📅 Due: {task_info['due_date']}")
    
    if task_info['priority'] == 1:
        desc_parts.append("🚨 URGENT PRIORITY")
    elif task_info['priority'] == 2:
        desc_parts.append("⚡ HIGH PRIORITY")
    
    if task_info['tags']:
        desc_parts.append(f"🏷️ Tags: {', '.join(task_info['tags'])}")
    
    desc_parts.append(f"\n⏰ Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    task_info['description'] = '\n'.join(desc_parts)
    
    # Debug output
    print(f"Parsed: Assignee='{task_info['assignee']}', Task='{task_info['name']}', Display='{task_info['display_name']}'")
    
    return task_info

def create_task_in_clickup(task_info):
    """Create a task in ClickUp with assignee in the task name"""
    
    try:
        headers = {
            'Authorization': CLICKUP_KEY,
            'Content-Type': 'application/json'
        }
        
        # Get the first available list
        list_id = get_list_id()
        if not list_id:
            return {
                'response': '⚠️ Could not find a ClickUp list. Please create a list in ClickUp first.',
                'success': False
            }
        
        # Build task data with assignee in the name
        task_data = {
            'name': task_info['display_name'],  # This includes [Assignee] prefix
            'description': task_info['description'],
            'priority': task_info['priority'],
            'status': 'to do'
        }
        
        # Add tags if any
        if task_info['tags']:
            task_data['tags'] = task_info['tags']
        
        # Add due date (set to noon to avoid timezone issues)
        if task_info['due_date']:
            due_date = datetime.strptime(task_info['due_date'], '%Y-%m-%d')
            due_date = due_date.replace(hour=12, minute=0, second=0, microsecond=0)
            task_data['due_date'] = int(due_date.timestamp() * 1000)
            task_data['due_date_time'] = True
        
        # Make the API call to create the task
        response = requests.post(
            f'{BASE_URL}/list/{list_id}/task',
            headers=headers,
            json=task_data,
            timeout=10
        )
        
        if response.status_code == 200:
            created_task = response.json()
            
            # Build success response
            response_parts = []
            response_parts.append(f"<strong>✅ Task Created Successfully!</strong>")
            response_parts.append(f"")
            response_parts.append(f"📝 <strong>{task_info['display_name']}</strong>")
            
            if task_info['assignee']:
                response_parts.append(f"👤 Assigned to: {task_info['assignee']}")
            else:
                response_parts.append(f"👤 No assignee (unassigned task)")
            
            if task_info['priority'] == 1:
                response_parts.append("🚨 Priority: URGENT")
            elif task_info['priority'] == 2:
                response_parts.append("⚡ Priority: HIGH")
            else:
                response_parts.append("📊 Priority: Normal")
            
            if task_info['due_date']:
                due_date = datetime.strptime(task_info['due_date'], '%Y-%m-%d')
                formatted_date = due_date.strftime('%B %d, %Y')
                response_parts.append(f"📅 Due: {formatted_date}")
            
            if task_info['tags']:
                response_parts.append(f"🏷️ Tags: {', '.join(task_info['tags'])}")
            
            return {
                'response': '<br>'.join(response_parts),
                'success': True,
                'task_id': created_task.get('id')
            }
        else:
            print(f"ClickUp API error: {response.status_code} - {response.text}")
            return {
                'response': f"⚠️ Could not create task in ClickUp. Error code: {response.status_code}",
                'success': False
            }
            
    except requests.exceptions.Timeout:
        return {
            'response': '⏱️ ClickUp took too long to respond. Please try again.',
            'success': False
        }
    except Exception as e:
        print(f"Error creating task: {e}")
        return {
            'response': f"⚠️ Error: {str(e)}",
            'success': False
        }

def get_list_id():
    """Get the first available list ID from ClickUp"""
    
    try:
        headers = {'Authorization': CLICKUP_KEY}
        
        # Get all spaces
        response = requests.get(
            f'{BASE_URL}/team/{WORKSPACE_ID}/space',
            headers=headers,
            params={'archived': 'false'},
            timeout=10
        )
        
        if response.status_code == 200:
            spaces = response.json().get('spaces', [])
            
            # Try to find a list in the first available space
            for space in spaces:
                # Get lists in this space
                list_response = requests.get(
                    f'{BASE_URL}/space/{space["id"]}/list',
                    headers=headers,
                    params={'archived': 'false'},
                    timeout=10
                )
                
                if list_response.status_code == 200:
                    lists = list_response.json().get('lists', [])
                    if lists:
                        print(f"Using list: {lists[0]['name']} (ID: {lists[0]['id']})")
                        return lists[0]['id']
        
        print("No lists found in workspace")
        return None
        
    except Exception as e:
        print(f"Error getting list: {e}")
        return None

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'clickup': bool(CLICKUP_KEY),
        'workspace': bool(WORKSPACE_ID),
        'settings_loaded': bool(SETTINGS),
        'team_count': len(SETTINGS.get('team_members', {})),
        'job_types_count': len(SETTINGS.get('job_types', {}))
    }
    
    return jsonify(health_status)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    print(f"🚀 Starting server on port {port}")
    print(f"📱 Main interface: http://localhost:{port}")
    print(f"⚙️  Settings page: http://localhost:{port}/settings")
    app.run(host='0.0.0.0', port=port, debug=False)
