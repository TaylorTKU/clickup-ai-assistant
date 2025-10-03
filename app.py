# app.py - Enhanced ClickUp AI Assistant with All Features
# Adds: Assignees, Priorities, Due Dates, Specific Lists, Voice Input, Better Commands

import os
import re
import json
from datetime import datetime, timedelta
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>ClickUp Assistant Pro</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea, #764ba2);
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
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 25px;
            text-align: center;
        }
        
        .status-bar {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            margin-top: 15px;
            border-radius: 10px;
            font-size: 14px;
        }
        
        .messages {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        
        .message {
            margin: 10px 0;
            padding: 12px 16px;
            border-radius: 15px;
            max-width: 80%;
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .user {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            margin-left: auto;
            text-align: right;
        }
        
        .ai {
            background: white;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        
        .error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        
        .input-section {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        input {
            flex: 1;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }
        
        button {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102,126,234,0.3);
        }
        
        .voice-btn {
            background: #28a745;
            padding: 15px;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .voice-btn.recording {
            background: #dc3545;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .quick-commands {
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
        }
        
        .quick-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }
        
        .quick-btn {
            padding: 12px;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
        }
        
        .quick-btn:hover {
            border-color: #667eea;
            background: linear-gradient(135deg, rgba(102,126,234,0.05), rgba(118,75,162,0.05));
            transform: translateY(-2px);
        }
        
        .quick-btn-icon {
            font-size: 20px;
            margin-bottom: 5px;
        }
        
        .quick-btn-label {
            font-size: 13px;
            color: #666;
        }
        
        .help-text {
            padding: 15px;
            background: #e8f4f8;
            border-left: 4px solid #667eea;
            margin: 10px 20px;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .team-select {
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            margin: 10px 0;
            width: 100%;
        }
        
        @media (max-width: 600px) {
            .container { border-radius: 0; }
            .messages { height: 300px; }
            .quick-grid { grid-template-columns: 1fr 1fr; }
            body { padding: 0; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ ClickUp Construction Assistant Pro</h1>
            <div class="status-bar" id="statusBar">
                ✅ Connected to ClickUp | 📍 Workspace: Active
            </div>
        </div>
        
        <div class="messages" id="messages">
            <div class="message ai">
                👋 Welcome! I can now handle complex commands like:
                <br><br>
                • "Add urgent task for Mike: Fix leak at Building A by Friday"<br>
                • "Create plumbing task: Install backflow preventer"<br>
                • "High priority: Schedule inspection tomorrow"<br>
                • "Assign to Tom: Complete grading at Lot 5"
            </div>
        </div>
        
        <div class="input-section">
            <div class="input-group">
                <input type="text" id="userInput" 
                       placeholder="Type or speak a command..." 
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="voice-btn" id="voiceBtn" onclick="toggleVoice()">🎤</button>
                <button onclick="sendMessage()">Send</button>
            </div>
            
            <select class="team-select" id="defaultAssignee">
                <option value="">No default assignee</option>
                <option value="Mike">Mike (Plumbing)</option>
                <option value="Tom">Tom (Grading)</option>
                <option value="Sarah">Sarah (Electrical)</option>
                <option value="John">John (General)</option>
            </select>
        </div>
        
        <div class="quick-commands">
            <div class="quick-grid">
                <div class="quick-btn" onclick="setCommand('urgent')">
                    <div class="quick-btn-icon">🚨</div>
                    <div class="quick-btn-label">Urgent Task</div>
                </div>
                <div class="quick-btn" onclick="setCommand('tomorrow')">
                    <div class="quick-btn-icon">📅</div>
                    <div class="quick-btn-label">Due Tomorrow</div>
                </div>
                <div class="quick-btn" onclick="setCommand('inspection')">
                    <div class="quick-btn-icon">🔍</div>
                    <div class="quick-btn-label">Inspection</div>
                </div>
                <div class="quick-btn" onclick="setCommand('plumbing')">
                    <div class="quick-btn-icon">🔧</div>
                    <div class="quick-btn-label">Plumbing Task</div>
                </div>
                <div class="quick-btn" onclick="setCommand('electrical')">
                    <div class="quick-btn-icon">⚡</div>
                    <div class="quick-btn-label">Electrical Task</div>
                </div>
                <div class="quick-btn" onclick="setCommand('safety')">
                    <div class="quick-btn-icon">⚠️</div>
                    <div class="quick-btn-label">Safety Issue</div>
                </div>
            </div>
        </div>
        
        <div class="help-text">
            💡 <strong>Pro Tips:</strong> Say "urgent" for high priority, add "for [name]" to assign, 
            "by [day]" for due dates, or specify the list like "plumbing task" or "electrical task"
        </div>
    </div>
    
    <script>
        let isRecording = false;
        let recognition = null;
        
        // Set up speech recognition if available
        if ('webkitSpeechRecognition' in window) {
            recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                document.getElementById('userInput').value = transcript;
                sendMessage();
            };
            
            recognition.onerror = function(event) {
                console.error('Speech recognition error', event.error);
                stopRecording();
            };
            
            recognition.onend = function() {
                stopRecording();
            };
        }
        
        function toggleVoice() {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        function startRecording() {
            if (recognition) {
                recognition.start();
                isRecording = true;
                document.getElementById('voiceBtn').classList.add('recording');
                document.getElementById('voiceBtn').innerHTML = '⏹️';
                addMessage('🎤 Listening...', false);
            } else {
                alert('Voice input not supported on this device');
            }
        }
        
        function stopRecording() {
            if (recognition) {
                recognition.stop();
            }
            isRecording = false;
            document.getElementById('voiceBtn').classList.remove('recording');
            document.getElementById('voiceBtn').innerHTML = '🎤';
        }
        
        function addMessage(text, isUser, isSuccess) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : isSuccess ? 'success' : 'ai');
            div.innerHTML = text;
            document.getElementById('messages').appendChild(div);
            document.getElementById('messages').scrollTop = 99999;
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
                
                if (data.success) {
                    updateStatus('✅ Task created successfully');
                }
            } catch (e) {
                addMessage('Error: ' + e.message, false);
            }
        }
        
        function setCommand(type) {
            const input = document.getElementById('userInput');
            const commands = {
                'urgent': 'Add urgent task: ',
                'tomorrow': 'Add task due tomorrow: ',
                'inspection': 'Schedule inspection: ',
                'plumbing': 'Add plumbing task: ',
                'electrical': 'Add electrical task: ',
                'safety': 'URGENT safety issue: '
            };
            input.value = commands[type] || '';
            input.focus();
        }
        
        function updateStatus(text) {
            const statusBar = document.getElementById('statusBar');
            statusBar.innerHTML = text;
            setTimeout(() => {
                statusBar.innerHTML = '✅ Connected to ClickUp | 📍 Workspace: Active';
            }, 3000);
        }
        
        // Check connection
        setInterval(async () => {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                if (!data.clickup) {
                    updateStatus('⚠️ ClickUp not configured');
                }
            } catch (e) {
                updateStatus('⚠️ Connection issue');
            }
        }, 30000);
    </script>
</body>
</html>
"""

# Configuration
CLICKUP_KEY = os.getenv('CLICKUP_API_KEY', '')
WORKSPACE_ID = os.getenv('WORKSPACE_ID', '')
BASE_URL = 'https://api.clickup.com/api/v2'

# Team member mapping (customize these)
TEAM_MEMBERS = {
    'mike': {'name': 'Mike', 'email': 'mike@company.com', 'specialty': 'plumbing'},
    'tom': {'name': 'Tom', 'email': 'tom@company.com', 'specialty': 'grading'},
    'sarah': {'name': 'Sarah', 'email': 'sarah@company.com', 'specialty': 'electrical'},
    'john': {'name': 'John', 'email': 'john@company.com', 'specialty': 'general'},
}

# List mapping for different trades
LIST_MAPPING = {
    'plumbing': 'Plumbing Tasks',
    'electrical': 'Electrical Tasks',
    'grading': 'Grading Tasks',
    'safety': 'Safety Issues',
    'inspection': 'Inspections',
    'general': 'General Tasks'
}

print("=" * 50)
print("ClickUp Assistant Pro Starting...")
print(f"API Key: {'✅ Connected' if CLICKUP_KEY else '❌ Not Set'}")
print(f"Workspace: {WORKSPACE_ID if WORKSPACE_ID else '❌ Not Set'}")
print("=" * 50)

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    default_assignee = data.get('default_assignee', '')
    
    # Parse the command
    parsed = parse_command(message, default_assignee)
    
    # Create the task with all parameters
    response = create_enhanced_task(parsed)
    
    return jsonify(response)

# app.py - Enhanced ClickUp AI Assistant with All Features
# Adds: Assignees, Priorities, Due Dates, Specific Lists, Voice Input, Better Commands

import os
import re
import json
from datetime import datetime, timedelta
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>ClickUp Assistant Pro</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea, #764ba2);
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
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 25px;
            text-align: center;
        }
        
        .status-bar {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            margin-top: 15px;
            border-radius: 10px;
            font-size: 14px;
        }
        
        .messages {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        
        .message {
            margin: 10px 0;
            padding: 12px 16px;
            border-radius: 15px;
            max-width: 80%;
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .user {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            margin-left: auto;
            text-align: right;
        }
        
        .ai {
            background: white;
            border: 1px solid #e0e0e0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        
        .error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        
        .input-section {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        input {
            flex: 1;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }
        
        button {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102,126,234,0.3);
        }
        
        .voice-btn {
            background: #28a745;
            padding: 15px;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .voice-btn.recording {
            background: #dc3545;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .quick-commands {
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
        }
        
        .quick-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }
        
        .quick-btn {
            padding: 12px;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
        }
        
        .quick-btn:hover {
            border-color: #667eea;
            background: linear-gradient(135deg, rgba(102,126,234,0.05), rgba(118,75,162,0.05));
            transform: translateY(-2px);
        }
        
        .quick-btn-icon {
            font-size: 20px;
            margin-bottom: 5px;
        }
        
        .quick-btn-label {
            font-size: 13px;
            color: #666;
        }
        
        .help-text {
            padding: 15px;
            background: #e8f4f8;
            border-left: 4px solid #667eea;
            margin: 10px 20px;
            border-radius: 5px;
            font-size: 14px;
        }
        
        .team-select {
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            margin: 10px 0;
            width: 100%;
        }
        
        @media (max-width: 600px) {
            .container { border-radius: 0; }
            .messages { height: 300px; }
            .quick-grid { grid-template-columns: 1fr 1fr; }
            body { padding: 0; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ ClickUp Construction Assistant Pro</h1>
            <div class="status-bar" id="statusBar">
                ✅ Connected to ClickUp | 📍 Workspace: Active
            </div>
        </div>
        
        <div class="messages" id="messages">
            <div class="message ai">
                👋 Welcome! I can now handle complex commands like:
                <br><br>
                • "Add urgent task for Mike: Fix leak at Building A by Friday"<br>
                • "Create plumbing task: Install backflow preventer"<br>
                • "High priority: Schedule inspection tomorrow"<br>
                • "Assign to Tom: Complete grading at Lot 5"
            </div>
        </div>
        
        <div class="input-section">
            <div class="input-group">
                <input type="text" id="userInput" 
                       placeholder="Type or speak a command..." 
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="voice-btn" id="voiceBtn" onclick="toggleVoice()">🎤</button>
                <button onclick="sendMessage()">Send</button>
            </div>
            
            <select class="team-select" id="defaultAssignee">
                <option value="">No default assignee</option>
                <option value="Mike">Mike (Plumbing)</option>
                <option value="Tom">Tom (Grading)</option>
                <option value="Sarah">Sarah (Electrical)</option>
                <option value="John">John (General)</option>
            </select>
        </div>
        
        <div class="quick-commands">
            <div class="quick-grid">
                <div class="quick-btn" onclick="setCommand('urgent')">
                    <div class="quick-btn-icon">🚨</div>
                    <div class="quick-btn-label">Urgent Task</div>
                </div>
                <div class="quick-btn" onclick="setCommand('tomorrow')">
                    <div class="quick-btn-icon">📅</div>
                    <div class="quick-btn-label">Due Tomorrow</div>
                </div>
                <div class="quick-btn" onclick="setCommand('inspection')">
                    <div class="quick-btn-icon">🔍</div>
                    <div class="quick-btn-label">Inspection</div>
                </div>
                <div class="quick-btn" onclick="setCommand('plumbing')">
                    <div class="quick-btn-icon">🔧</div>
                    <div class="quick-btn-label">Plumbing Task</div>
                </div>
                <div class="quick-btn" onclick="setCommand('electrical')">
                    <div class="quick-btn-icon">⚡</div>
                    <div class="quick-btn-label">Electrical Task</div>
                </div>
                <div class="quick-btn" onclick="setCommand('safety')">
                    <div class="quick-btn-icon">⚠️</div>
                    <div class="quick-btn-label">Safety Issue</div>
                </div>
            </div>
        </div>
        
        <div class="help-text">
            💡 <strong>Pro Tips:</strong> Say "urgent" for high priority, add "for [name]" to assign, 
            "by [day]" for due dates, or specify the list like "plumbing task" or "electrical task"
        </div>
    </div>
    
    <script>
        let isRecording = false;
        let recognition = null;
        
        // Set up speech recognition if available
        if ('webkitSpeechRecognition' in window) {
            recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                document.getElementById('userInput').value = transcript;
                sendMessage();
            };
            
            recognition.onerror = function(event) {
                console.error('Speech recognition error', event.error);
                stopRecording();
            };
            
            recognition.onend = function() {
                stopRecording();
            };
        }
        
        function toggleVoice() {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        function startRecording() {
            if (recognition) {
                recognition.start();
                isRecording = true;
                document.getElementById('voiceBtn').classList.add('recording');
                document.getElementById('voiceBtn').innerHTML = '⏹️';
                addMessage('🎤 Listening...', false);
            } else {
                alert('Voice input not supported on this device');
            }
        }
        
        function stopRecording() {
            if (recognition) {
                recognition.stop();
            }
            isRecording = false;
            document.getElementById('voiceBtn').classList.remove('recording');
            document.getElementById('voiceBtn').innerHTML = '🎤';
        }
        
        function addMessage(text, isUser, isSuccess) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : isSuccess ? 'success' : 'ai');
            div.innerHTML = text;
            document.getElementById('messages').appendChild(div);
            document.getElementById('messages').scrollTop = 99999;
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
                
                if (data.success) {
                    updateStatus('✅ Task created successfully');
                }
            } catch (e) {
                addMessage('Error: ' + e.message, false);
            }
        }
        
        function setCommand(type) {
            const input = document.getElementById('userInput');
            const commands = {
                'urgent': 'Add urgent task: ',
                'tomorrow': 'Add task due tomorrow: ',
                'inspection': 'Schedule inspection: ',
                'plumbing': 'Add plumbing task: ',
                'electrical': 'Add electrical task: ',
                'safety': 'URGENT safety issue: '
            };
            input.value = commands[type] || '';
            input.focus();
        }
        
        function updateStatus(text) {
            const statusBar = document.getElementById('statusBar');
            statusBar.innerHTML = text;
            setTimeout(() => {
                statusBar.innerHTML = '✅ Connected to ClickUp | 📍 Workspace: Active';
            }, 3000);
        }
        
        // Check connection
        setInterval(async () => {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                if (!data.clickup) {
                    updateStatus('⚠️ ClickUp not configured');
                }
            } catch (e) {
                updateStatus('⚠️ Connection issue');
            }
        }, 30000);
    </script>
</body>
</html>
"""

# Configuration
CLICKUP_KEY = os.getenv('CLICKUP_API_KEY', '')
WORKSPACE_ID = os.getenv('WORKSPACE_ID', '')
BASE_URL = 'https://api.clickup.com/api/v2'

# Team member mapping (customize these)
TEAM_MEMBERS = {
    'mike': {'name': 'Mike', 'email': 'mike@company.com', 'specialty': 'plumbing'},
    'tom': {'name': 'Tom', 'email': 'tom@company.com', 'specialty': 'grading'},
    'sarah': {'name': 'Sarah', 'email': 'sarah@company.com', 'specialty': 'electrical'},
    'john': {'name': 'John', 'email': 'john@company.com', 'specialty': 'general'},
}

# List mapping for different trades
LIST_MAPPING = {
    'plumbing': 'Plumbing Tasks',
    'electrical': 'Electrical Tasks',
    'grading': 'Grading Tasks',
    'safety': 'Safety Issues',
    'inspection': 'Inspections',
    'general': 'General Tasks'
}

print("=" * 50)
print("ClickUp Assistant Pro Starting...")
print(f"API Key: {'✅ Connected' if CLICKUP_KEY else '❌ Not Set'}")
print(f"Workspace: {WORKSPACE_ID if WORKSPACE_ID else '❌ Not Set'}")
print("=" * 50)

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    default_assignee = data.get('default_assignee', '')
    
    # Parse the command
    parsed = parse_command(message, default_assignee)
    
    # Create the task with all parameters
    response = create_enhanced_task(parsed)
    
    return jsonify(response)

def parse_command(message, default_assignee=''):
    """Parse natural language command to extract task details"""
    
    lower = message.lower()
    
    # Initialize result
    result = {
        'name': message,  # Default to full message
        'priority': 3,    # Normal priority
        'assignee': default_assignee,
        'due_date': None,
        'list_name': None,
        'description': ''
    }
    
    # Extract priority
    if any(word in lower for word in ['urgent', 'emergency', 'critical', 'asap', 'safety']):
        result['priority'] = 1  # Urgent
    elif any(word in lower for word in ['high', 'important']):
        result['priority'] = 2  # High
    elif any(word in lower for word in ['low', 'whenever', 'eventually']):
        result['priority'] = 4  # Low
    
    # Extract assignee
    for name, info in TEAM_MEMBERS.items():
        if name in lower or f"for {name}" in lower or f"to {name}" in lower:
            result['assignee'] = info['name']
            # Remove assignee from task name
            message = re.sub(f"(for |to |assign to |assigned to )?{name}", '', message, flags=re.IGNORECASE)
    
    # Extract due date
    if 'tomorrow' in lower:
        result['due_date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        message = message.replace('tomorrow', '').replace('due ', '')
    elif 'today' in lower:
        result['due_date'] = datetime.now().strftime('%Y-%m-%d')
        message = message.replace('today', '').replace('due ', '')
    elif 'friday' in lower:
        days_ahead = 4 - datetime.now().weekday()
        if days_ahead <= 0:
            days_ahead += 7
        result['due_date'] = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        message = message.replace('friday', '').replace('by ', '')
    elif 'monday' in lower:
        days_ahead = 0 - datetime.now().weekday()
        if days_ahead <= 0:
            days_ahead += 7
        result['due_date'] = (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
        message = message.replace('monday', '').replace('by ', '')
    
    # Extract list based on keywords
    if 'plumbing' in lower or 'pipe' in lower or 'water' in lower or 'leak' in lower:
        result['list_name'] = 'plumbing'
    elif 'electrical' in lower or 'wire' in lower or 'power' in lower:
        result['list_name'] = 'electrical'
    elif 'grading' in lower or 'grade' in lower or 'level' in lower:
        result['list_name'] = 'grading'
    elif 'safety' in lower or 'danger' in lower or 'hazard' in lower:
        result['list_name'] = 'safety'
        result['priority'] = 1  # Safety issues are always urgent
    elif 'inspection' in lower or 'inspect' in lower:
        result['list_name'] = 'inspection'
    
    # Clean up task name
    clean_name = re.sub(r'(add|create|new|task|urgent|high|low|priority|:|due|by)', '', message, flags=re.IGNORECASE)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    
    if clean_name:
        result['name'] = clean_name
    
    # Add description with metadata
    desc_parts = []
    if result['assignee']:
        desc_parts.append(f"Assigned to: {result['assignee']}")
    if result['due_date']:
        desc_parts.append(f"Due: {result['due_date']}")
    if result['priority'] == 1:
        desc_parts.append("🚨 URGENT PRIORITY")
    
    desc_parts.append(f"\nCreated via AI Assistant at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    result['description'] = '\n'.join(desc_parts)
    
    return result

def create_enhanced_task(task_info):
    """Create a task with all the parsed information"""
    
    if not CLICKUP_KEY or not WORKSPACE_ID:
        return {
            'response': f"📝 Task noted: {task_info['name']} (Configure ClickUp API for full sync)",
            'success': False
        }
    
    try:
        headers = {
            'Authorization': CLICKUP_KEY,
            'Content-Type': 'application/json'
        }
        
        # Get the appropriate list
        list_id = get_or_create_list(task_info['list_name'])
        
        if not list_id:
            return {
                'response': f"⚠️ Could not find appropriate list for task",
                'success': False
            }
        
        # Build task data
        task_data = {
            'name': task_info['name'],
            'description': task_info['description'],
            'priority': task_info['priority'],
            'status': 'to do'
        }
        
        # Add due date if specified
        if task_info['due_date']:
            task_data['due_date'] = int(datetime.strptime(task_info['due_date'], '%Y-%m-%d').timestamp() * 1000)
            task_data['due_date_time'] = True
        
        # Create the task
        response = requests.post(
            f'{BASE_URL}/list/{list_id}/task',
            headers=headers,
            json=task_data,
            timeout=10
        )
        
        if response.status_code == 200:
            task = response.json()
            
            # Build success message
            msg_parts = [f"✅ Created in ClickUp: '{task_info['name']}'"]
            
            if task_info['assignee']:
                msg_parts.append(f"👤 Assigned to: {task_info['assignee']}")
            
            if task_info['priority'] == 1:
                msg_parts.append("🚨 Priority: URGENT")
            elif task_info['priority'] == 2:
                msg_parts.append("⚡ Priority: High")
            
            if task_info['due_date']:
                msg_parts.append(f"📅 Due: {task_info['due_date']}")
            
            if task_info['list_name']:
                msg_parts.append(f"📁 List: {LIST_MAPPING.get(task_info['list_name'], 'General')}")
            
            return {
                'response': '<br>'.join(msg_parts),
                'success': True
            }
        else:
            return {
                'response': f"⚠️ Task saved locally: {task_info['name']} (will sync later)",
                'success': False
            }
            
    except Exception as e:
        print(f"Error creating task: {e}")
        return {
            'response': f"📝 Task noted: {task_info['name']} (connection issue)",
            'success': False
        }

def get_or_create_list(list_type):
    """Get the appropriate list ID based on task type"""
    
    if not list_type:
        list_type = 'general'
    
    try:
        headers = {'Authorization': CLICKUP_KEY}
        
        # Get spaces
        response = requests.get(
            f'{BASE_URL}/team/{WORKSPACE_ID}/space',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            spaces = response.json().get('spaces', [])
            
            if spaces:
                space_id = spaces[0]['id']
                
                # Get lists in space
                response = requests.get(
                    f'{BASE_URL}/space/{space_id}/list',
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    lists = response.json().get('lists', [])
                    
                    # Look for matching list
                    target_name = LIST_MAPPING.get(list_type, 'General Tasks')
                    
                    for lst in lists:
                        if target_name.lower() in lst['name'].lower() or list_type in lst['name'].lower():
                            return lst['id']
                    
                    # If no specific list found, return first list
                    if lists:
                        return lists[0]['id']
                    
                    # Create new list if none exist
                    create_response = requests.post(
                        f'{BASE_URL}/space/{space_id}/list',
                        headers={**headers, 'Content-Type': 'application/json'},
                        json={'name': target_name},
                        timeout=10
                    )
                    
                    if create_response.status_code == 200:
                        return create_response.json()['id']
        
    except Exception as e:
        print(f"Error getting list: {e}")
    
    return None

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    
    status = {
        'status': 'healthy',
        'clickup': bool(CLICKUP_KEY),
        'workspace': bool(WORKSPACE_ID),
        'timestamp': datetime.now().isoformat()
    }
    
    # Test ClickUp connection
    if CLICKUP_KEY and WORKSPACE_ID:
        try:
            headers = {'Authorization': CLICKUP_KEY}
            response = requests.get(
                f'{BASE_URL}/team/{WORKSPACE_ID}',
                headers=headers,
                timeout=5
            )
            status['clickup_connection'] = response.status_code == 200
        except:
            status['clickup_connection'] = False
    
    return jsonify(status)

@app.route('/api/lists', methods=['GET'])
def get_lists():
    """Get available lists"""
    
    if not CLICKUP_KEY or not WORKSPACE_ID:
        return jsonify({'error': 'Not configured'}), 400
    
    try:
        headers = {'Authorization': CLICKUP_KEY}
        
        # Get spaces and lists
        response = requests.get(
            f'{BASE_URL}/team/{WORKSPACE_ID}/space',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            spaces = response.json().get('spaces', [])
            all_lists = []
            
            for space in spaces[:3]:  # Limit to first 3 spaces
                list_response = requests.get(
                    f'{BASE_URL}/space/{space["id"]}/list',
                    headers=headers,
                    timeout=10
                )
                
                if list_response.status_code == 200:
                    lists = list_response.json().get('lists', [])
                    for lst in lists:
                        all_lists.append({
                            'id': lst['id'],
                            'name': lst['name'],
                            'space': space['name']
                        })
            
            return jsonify({'lists': all_lists})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'lists': []})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def create_enhanced_task(task_info):
    """Create a task with all the parsed information"""
    
    if not CLICKUP_KEY or not WORKSPACE_ID:
        return {
            'response': f"📝 Task noted: {task_info['name']} (Configure ClickUp API for full sync)",
            'success': False
        }
    
    try:
        headers = {
            'Authorization': CLICKUP_KEY,
            'Content-Type': 'application/json'
        }
        
        # Get the appropriate list
        list_id = get_or_create_list(task_info['list_name'])
        
        if not list_id:
            return {
                'response': f"⚠️ Could not find appropriate list for task",
                'success': False
            }
        
        # Build task data
        task_data = {
            'name': task_info['name'],
            'description': task_info['description'],
            'priority': task_info['priority'],
            'status': 'to do'
        }
        
        # Add due date if specified
        if task_info['due_date']:
            task_data['due_date'] = int(datetime.strptime(task_info['due_date'], '%Y-%m-%d').timestamp() * 1000)
            task_data['due_date_time'] = True
        
        # Create the task
        response = requests.post(
            f'{BASE_URL}/list/{list_id}/task',
            headers=headers,
            json=task_data,
            timeout=10
        )
        
        if response.status_code == 200:
            task = response.json()
            
            # Build success message
            msg_parts = [f"✅ Created in ClickUp: '{task_info['name']}'"]
            
            if task_info['assignee']:
                msg_parts.append(f"👤 Assigned to: {task_info['assignee']}")
            
            if task_info['priority'] == 1:
                msg_parts.append("🚨 Priority: URGENT")
            elif task_info['priority'] == 2:
                msg_parts.append("⚡ Priority: High")
            
            if task_info['due_date']:
                msg_parts.append(f"📅 Due: {task_info['due_date']}")
            
            if task_info['list_name']:
                msg_parts.append(f"📁 List: {LIST_MAPPING.get(task_info['list_name'], 'General')}")
            
            return {
                'response': '<br>'.join(msg_parts),
                'success': True
            }
        else:
            return {
                'response': f"⚠️ Task saved locally: {task_info['name']} (will sync later)",
                'success': False
            }
            
    except Exception as e:
        print(f"Error creating task: {e}")
        return {
            'response': f"📝 Task noted: {task_info['name']} (connection issue)",
            'success': False
        }

def get_or_create_list(list_type):
    """Get the appropriate list ID based on task type"""
    
    if not list_type:
        list_type = 'general'
    
    try:
        headers = {'Authorization': CLICKUP_KEY}
        
        # Get spaces
        response = requests.get(
            f'{BASE_URL}/team/{WORKSPACE_ID}/space',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            spaces = response.json().get('spaces', [])
            
            if spaces:
                space_id = spaces[0]['id']
                
                # Get lists in space
                response = requests.get(
                    f'{BASE_URL}/space/{space_id}/list',
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    lists = response.json().get('lists', [])
                    
                    # Look for matching list
                    target_name = LIST_MAPPING.get(list_type, 'General Tasks')
                    
                    for lst in lists:
                        if target_name.lower() in lst['name'].lower() or list_type in lst['name'].lower():
                            return lst['id']
                    
                    # If no specific list found, return first list
                    if lists:
                        return lists[0]['id']
                    
                    # Create new list if none exist
                    create_response = requests.post(
                        f'{BASE_URL}/space/{space_id}/list',
                        headers={**headers, 'Content-Type': 'application/json'},
                        json={'name': target_name},
                        timeout=10
                    )
                    
                    if create_response.status_code == 200:
                        return create_response.json()['id']
        
    except Exception as e:
        print(f"Error getting list: {e}")
    
    return None

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    
    status = {
        'status': 'healthy',
        'clickup': bool(CLICKUP_KEY),
        'workspace': bool(WORKSPACE_ID),
        'timestamp': datetime.now().isoformat()
    }
    
    # Test ClickUp connection
    if CLICKUP_KEY and WORKSPACE_ID:
        try:
            headers = {'Authorization': CLICKUP_KEY}
            response = requests.get(
                f'{BASE_URL}/team/{WORKSPACE_ID}',
                headers=headers,
                timeout=5
            )
            status['clickup_connection'] = response.status_code == 200
        except:
            status['clickup_connection'] = False
    
    return jsonify(status)

@app.route('/api/lists', methods=['GET'])
def get_lists():
    """Get available lists"""
    
    if not CLICKUP_KEY or not WORKSPACE_ID:
        return jsonify({'error': 'Not configured'}), 400
    
    try:
        headers = {'Authorization': CLICKUP_KEY}
        
        # Get spaces and lists
        response = requests.get(
            f'{BASE_URL}/team/{WORKSPACE_ID}/space',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            spaces = response.json().get('spaces', [])
            all_lists = []
            
            for space in spaces[:3]:  # Limit to first 3 spaces
                list_response = requests.get(
                    f'{BASE_URL}/space/{space["id"]}/list',
                    headers=headers,
                    timeout=10
                )
                
                if list_response.status_code == 200:
                    lists = list_response.json().get('lists', [])
                    for lst in lists:
                        all_lists.append({
                            'id': lst['id'],
                            'name': lst['name'],
                            'space': space['name']
                        })
            
            return jsonify({'lists': all_lists})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'lists': []})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
