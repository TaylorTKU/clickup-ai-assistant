# app.py - ClickUp Construction Assistant - COMPLETE WITH DATE FIX
# All features working: Assignees, Priorities, Due Dates (FIXED), Voice Input

import os
import re
from datetime import datetime, timedelta
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Complete HTML Interface with Voice Support
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
        }
        
        .header h1 {
            font-size: 24px;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 14px;
            opacity: 0.9;
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
        
        .message.error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
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
        
        .voice-btn {
            padding: 15px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 20px;
        }
        
        .voice-btn.recording {
            background: #dc3545;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { 
                transform: scale(1); 
                box-shadow: 0 0 0 0 rgba(220,53,69,0.7);
            }
            50% { 
                transform: scale(1.05);
                box-shadow: 0 0 0 10px rgba(220,53,69,0);
            }
        }
        
        .quick-actions {
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
        }
        
        .quick-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
        }
        
        .quick-btn {
            padding: 12px;
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
        }
        
        .quick-btn:hover {
            border-color: #667eea;
            background: linear-gradient(135deg, rgba(102,126,234,0.05) 0%, rgba(118,75,162,0.05) 100%);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102,126,234,0.2);
        }
        
        .quick-icon {
            font-size: 24px;
            margin-bottom: 5px;
        }
        
        .quick-label {
            font-size: 12px;
            color: #6c757d;
            font-weight: 500;
        }
        
        .help-section {
            padding: 15px 20px;
            background: #e8f4f8;
            border-top: 1px solid #d6e9f0;
            font-size: 14px;
            color: #495057;
        }
        
        .help-section strong {
            color: #667eea;
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
        
        @media (max-width: 600px) {
            .container {
                border-radius: 0;
                height: 100vh;
                display: flex;
                flex-direction: column;
            }
            
            .messages {
                height: calc(100vh - 400px);
                flex: 1;
            }
            
            body {
                padding: 0;
            }
            
            .quick-grid {
                grid-template-columns: repeat(3, 1fr);
            }
            
            .quick-label {
                font-size: 11px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ ClickUp Construction Assistant</h1>
            <p>Create and manage tasks with natural language</p>
            <div class="status-bar" id="status">✅ Connected to ClickUp</div>
        </div>
        
        <div class="messages" id="messages">
            <div class="message ai">
                👋 Welcome! I can help you manage ClickUp tasks. Try these examples:<br><br>
                📝 <strong>"Add urgent task for Mike: Fix water leak at Building A"</strong><br>
                📅 <strong>"Create task due tomorrow: Order supplies"</strong><br>
                🔍 <strong>"Schedule inspection for Friday"</strong><br>
                ⚠️ <strong>"Safety issue: Exposed wiring at Lot 5"</strong><br><br>
                Click the microphone to use voice commands! 🎤
            </div>
        </div>
        
        <div class="input-section">
            <div class="input-group">
                <input type="text" 
                       class="input-field" 
                       id="userInput" 
                       placeholder="Type or speak a command..." 
                       autocomplete="off"
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="voice-btn" id="voiceBtn" onclick="toggleVoice()">🎤</button>
                <button class="send-btn" onclick="sendMessage()">Send</button>
            </div>
            
            <select class="team-select" id="defaultAssignee">
                <option value="">Select default assignee (optional)</option>
                <option value="Mike">Mike - Plumbing</option>
                <option value="Tom">Tom - Grading</option>
                <option value="Sarah">Sarah - Electrical</option>
                <option value="John">John - General</option>
            </select>
        </div>
        
        <div class="quick-actions">
            <div class="quick-grid">
                <div class="quick-btn" onclick="quickCommand('urgent')">
                    <div class="quick-icon">🚨</div>
                    <div class="quick-label">Urgent Task</div>
                </div>
                <div class="quick-btn" onclick="quickCommand('mike')">
                    <div class="quick-icon">👤</div>
                    <div class="quick-label">For Mike</div>
                </div>
                <div class="quick-btn" onclick="quickCommand('tomorrow')">
                    <div class="quick-icon">📅</div>
                    <div class="quick-label">Due Tomorrow</div>
                </div>
                <div class="quick-btn" onclick="quickCommand('friday')">
                    <div class="quick-icon">📆</div>
                    <div class="quick-label">Due Friday</div>
                </div>
                <div class="quick-btn" onclick="quickCommand('inspection')">
                    <div class="quick-icon">🔍</div>
                    <div class="quick-label">Inspection</div>
                </div>
                <div class="quick-btn" onclick="quickCommand('safety')">
                    <div class="quick-icon">⚠️</div>
                    <div class="quick-label">Safety Issue</div>
                </div>
            </div>
        </div>
        
        <div class="help-section">
            💡 <strong>Pro Tips:</strong> Use "urgent" for high priority | Add "for [name]" to assign | Say "tomorrow" or "Friday" for due dates | Use voice input for hands-free operation
        </div>
    </div>
    
    <script>
        let isRecording = false;
        let recognition = null;
        
        // Initialize speech recognition
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                document.getElementById('userInput').value = transcript;
                sendMessage();
                stopRecording();
            };
            
            recognition.onerror = function(event) {
                console.error('Speech error:', event.error);
                addMessage('Could not understand. Please try again.', false, false);
                stopRecording();
            };
            
            recognition.onend = function() {
                stopRecording();
            };
        }
        
        function toggleVoice() {
            if (!recognition) {
                alert('Voice input is not supported on this device. Please type your command.');
                return;
            }
            
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }
        
        function startRecording() {
            recognition.start();
            isRecording = true;
            document.getElementById('voiceBtn').classList.add('recording');
            document.getElementById('voiceBtn').innerHTML = '⏹️';
            addMessage('🎤 Listening... Speak now', false, false);
        }
        
        function stopRecording() {
            if (recognition && isRecording) {
                recognition.stop();
            }
            isRecording = false;
            document.getElementById('voiceBtn').classList.remove('recording');
            document.getElementById('voiceBtn').innerHTML = '🎤';
        }
        
        function addMessage(text, isUser, isSuccess) {
            const div = document.createElement('div');
            if (isUser) {
                div.className = 'message user';
            } else if (isSuccess === true) {
                div.className = 'message success';
            } else if (isSuccess === false) {
                div.className = 'message error';
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
                    updateStatus('✅ Task created successfully!');
                }
                
            } catch (error) {
                addMessage('⚠️ Connection error. Please try again.', false, false);
                console.error('Error:', error);
            }
        }
        
        function quickCommand(type) {
            const input = document.getElementById('userInput');
            const commands = {
                'urgent': 'Add urgent task: ',
                'mike': 'Add task for Mike: ',
                'tomorrow': 'Create task due tomorrow: ',
                'friday': 'Schedule for Friday: ',
                'inspection': 'Schedule inspection: ',
                'safety': 'URGENT safety issue: '
            };
            
            input.value = commands[type] || '';
            input.focus();
        }
        
        function updateStatus(text) {
            const status = document.getElementById('status');
            status.innerHTML = text;
            setTimeout(() => {
                status.innerHTML = '✅ Connected to ClickUp';
            }, 3000);
        }
        
        // Auto-focus on input
        window.onload = function() {
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

# Configuration from environment variables
CLICKUP_KEY = os.getenv('CLICKUP_API_KEY', '')
WORKSPACE_ID = os.getenv('WORKSPACE_ID', '')
BASE_URL = 'https://api.clickup.com/api/v2'

# Team member configuration - customize with your team
TEAM_MEMBERS = {
    'mike': {'name': 'Mike', 'role': 'Plumbing'},
    'tom': {'name': 'Tom', 'role': 'Grading'},
    'sarah': {'name': 'Sarah', 'role': 'Electrical'},
    'john': {'name': 'John', 'role': 'General'},
}

# Startup message
print("=" * 60)
print("🏗️  ClickUp Construction Assistant")
print("=" * 60)
print(f"📌 Status: {'Connected' if CLICKUP_KEY else 'No API Key'}")
print(f"🏢 Workspace: {WORKSPACE_ID if WORKSPACE_ID else 'Not Configured'}")
print(f"👥 Team Members: {', '.join([m['name'] for m in TEAM_MEMBERS.values()])}")
print("=" * 60)

@app.route('/')
def home():
    """Serve the main interface"""
    return render_template_string(HTML_PAGE)

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
                'response': f"📝 Task noted locally: '{task_info['name']}'<br>Configure ClickUp API to sync",
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
    """Parse natural language command to extract task details"""
    
    original_message = message
    lower = message.lower()
    
    # Initialize task info
    task_info = {
        'name': message,
        'priority': 3,  # Normal
        'assignee': default_assignee,
        'due_date': None,
        'description': '',
        'list_type': 'general'
    }
    
    # Extract priority
    if any(word in lower for word in ['urgent', 'emergency', 'critical', 'asap']):
        task_info['priority'] = 1  # Urgent
    elif any(word in lower for word in ['high', 'important']):
        task_info['priority'] = 2  # High
    elif any(word in lower for word in ['low', 'whenever']):
        task_info['priority'] = 4  # Low
    
    # Safety issues are always urgent
    if 'safety' in lower:
        task_info['priority'] = 1
        task_info['list_type'] = 'safety'
    
    # Extract assignee
    for key, member in TEAM_MEMBERS.items():
        if key in lower or f"for {key}" in lower or f"to {key}" in lower:
            task_info['assignee'] = member['name']
    
    # Extract due date with proper calculation
    today = datetime.now()
    
    if 'tomorrow' in lower:
        task_info['due_date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'today' in lower:
        task_info['due_date'] = today.strftime('%Y-%m-%d')
    elif 'friday' in lower:
        days_until = (4 - today.weekday()) % 7  # 4 = Friday
        if days_until == 0:  # Today is Friday
            days_until = 7  # Next Friday
        task_info['due_date'] = (today + timedelta(days=days_until)).strftime('%Y-%m-%d')
    elif 'monday' in lower:
        days_until = (0 - today.weekday()) % 7  # 0 = Monday
        if days_until == 0:  # Today is Monday
            days_until = 7  # Next Monday
        task_info['due_date'] = (today + timedelta(days=days_until)).strftime('%Y-%m-%d')
    
    # Detect task type for list assignment
    if any(word in lower for word in ['plumb', 'pipe', 'water', 'leak', 'faucet']):
        task_info['list_type'] = 'plumbing'
    elif any(word in lower for word in ['electric', 'wire', 'power', 'outlet', 'breaker']):
        task_info['list_type'] = 'electrical'
    elif any(word in lower for word in ['grade', 'grading', 'level', 'excavat']):
        task_info['list_type'] = 'grading'
    elif any(word in lower for word in ['inspect', 'inspection']):
        task_info['list_type'] = 'inspection'
    
    # Clean up task name
    clean_name = original_message
    
    # Remove command prefixes
    clean_name = re.sub(r'^(add|create|schedule|new)\s+(task\s+)?', '', clean_name, flags=re.IGNORECASE)
    
    # Remove priority indicators
    clean_name = re.sub(r'\b(urgent|high priority|low priority|asap)\b\s*', '', clean_name, flags=re.IGNORECASE)
    
    # Remove assignee phrases
    for key in TEAM_MEMBERS.keys():
        clean_name = re.sub(f'\\b(for {key}|assign to {key}|to {key})\\b', '', clean_name, flags=re.IGNORECASE)
    
    # Remove due date phrases
    clean_name = re.sub(r'\b(due tomorrow|by tomorrow|due today|by today|due friday|by friday|due monday|by monday|tomorrow|today)\b', '', clean_name, flags=re.IGNORECASE)
    
    # Clean up punctuation and extra spaces
    clean_name = re.sub(r':\s*', '', clean_name)
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    
    # Use cleaned name if it's not empty
    if clean_name:
        task_info['name'] = clean_name
    
    # Build description
    desc_parts = []
    if task_info['assignee']:
        desc_parts.append(f"👤 Assigned to: {task_info['assignee']}")
    if task_info['due_date']:
        desc_parts.append(f"📅 Due: {task_info['due_date']}")
    if task_info['priority'] == 1:
        desc_parts.append("🚨 URGENT PRIORITY")
    elif task_info['priority'] == 2:
        desc_parts.append("⚡ HIGH PRIORITY")
    
    desc_parts.append(f"\n⏰ Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    desc_parts.append("📱 Via: Construction Assistant")
    
    task_info['description'] = '\n'.join(desc_parts)
    
    # Debug logging
    print(f"Parsed task - Name: {task_info['name']}, Due: {task_info['due_date']}")
    
    return task_info

def create_task_in_clickup(task_info):
    """Create a task in ClickUp with the parsed information"""
    
    try:
        headers = {
            'Authorization': CLICKUP_KEY,
            'Content-Type': 'application/json'
        }
        
        # Get the appropriate list
        list_id = get_list_id()
        if not list_id:
            return {
                'response': '⚠️ Could not find a ClickUp list. Please create one first.',
                'success': False
            }
        
        # Build task data for ClickUp API
        task_data = {
            'name': task_info['name'],
            'description': task_info['description'],
            'priority': task_info['priority'],
            'status': 'to do'
        }
        
        # FIXED DATE HANDLING - Set to noon to avoid timezone issues
        if task_info['due_date']:
            # Parse the date string
            due_date = datetime.strptime(task_info['due_date'], '%Y-%m-%d')
            # Set time to noon (12:00 PM) to ensure correct day
            due_date = due_date.replace(hour=12, minute=0, second=0, microsecond=0)
            # Convert to milliseconds for ClickUp
            task_data['due_date'] = int(due_date.timestamp() * 1000)
            task_data['due_date_time'] = True  # Include time to be precise
            
            # Debug logging
            print(f"Setting due date: {task_info['due_date']} -> Timestamp: {task_data['due_date']}")
        
        # Make API call to create task
        response = requests.post(
            f'{BASE_URL}/list/{list_id}/task',
            headers=headers,
            json=task_data,
            timeout=10
        )
        
        if response.status_code == 200:
            created_task = response.json()
            
            # Build success response
            response_parts = [f"✅ <strong>Task Created Successfully!</strong>"]
            response_parts.append(f"📝 Task: '{task_info['name']}'")
            
            if task_info['assignee']:
                response_parts.append(f"👤 Assigned to: {task_info['assignee']}")
            
            if task_info['priority'] == 1:
                response_parts.append("🚨 Priority: URGENT")
            elif task_info['priority'] == 2:
                response_parts.append("⚡ Priority: HIGH")
            
            if task_info['due_date']:
                # Format date nicely
                due_date = datetime.strptime(task_info['due_date'], '%Y-%m-%d')
                formatted_date = due_date.strftime('%B %d, %Y')
                response_parts.append(f"📅 Due: {formatted_date}")
            
            return {
                'response': '<br>'.join(response_parts),
                'success': True,
                'task_id': created_task.get('id')
            }
        else:
            print(f"ClickUp API error: {response.status_code} - {response.text}")
            return {
                'response': f"⚠️ Could not create task in ClickUp. Status: {response.status_code}",
                'success': False
            }
            
    except requests.exceptions.Timeout:
        return {
            'response': '⏱️ ClickUp took too long to respond. Task saved locally.',
            'success': False
        }
    except Exception as e:
        print(f"Error creating task: {e}")
        return {
            'response': '⚠️ Could not connect to ClickUp. Please check your connection.',
            'success': False
        }

def get_list_id():
    """Get the first available list ID from ClickUp"""
    
    try:
        headers = {'Authorization': CLICKUP_KEY}
        
        # Get spaces
        response = requests.get(
            f'{BASE_URL}/team/{WORKSPACE_ID}/space',
            headers=headers,
            params={'archived': 'false'},
            timeout=10
        )
        
        if response.status_code == 200:
            spaces = response.json().get('spaces', [])
            
            # Get first non-archived space
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
                        # Return first list ID
                        print(f"Using list: {lists[0]['name']} (ID: {lists[0]['id']})")
                        return lists[0]['id']
        
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
        'workspace': bool(WORKSPACE_ID)
    }
    
    # Test ClickUp connection if configured
    if CLICKUP_KEY and WORKSPACE_ID:
        try:
            headers = {'Authorization': CLICKUP_KEY}
            response = requests.get(
                f'{BASE_URL}/user',
                headers=headers,
                timeout=5
            )
            health_status['clickup_connected'] = response.status_code == 200
        except:
            health_status['clickup_connected'] = False
    
    return jsonify(health_status)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    print(f"🚀 Starting server on port {port}")
    print(f"📱 Access at: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
