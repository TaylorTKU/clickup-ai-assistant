# app.py - Clean Enhanced ClickUp Assistant
import os
import re
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
    <title>ClickUp Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, Arial, sans-serif;
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
        }
        .header {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 25px;
            text-align: center;
            border-radius: 20px 20px 0 0;
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
        }
        .success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .input-section {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        .input-group {
            display: flex;
            gap: 10px;
        }
        input {
            flex: 1;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 16px;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102,126,234,0.3);
        }
        .quick-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            padding: 20px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
        }
        .quick-btn {
            padding: 12px;
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            cursor: pointer;
            text-align: center;
            transition: all 0.3s;
        }
        .quick-btn:hover {
            border-color: #667eea;
            transform: translateY(-2px);
        }
        .help {
            padding: 15px 20px;
            background: #e8f4f8;
            font-size: 14px;
            color: #333;
        }
        @media (max-width: 600px) {
            .container { border-radius: 0; }
            .messages { height: 300px; }
            body { padding: 0; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ ClickUp Construction Assistant</h1>
            <p>Create tasks with natural language</p>
        </div>
        
        <div class="messages" id="messages">
            <div class="message ai">
                👋 Welcome! Try these commands:<br><br>
                • "Add urgent task for Mike: Fix leak at Building A"<br>
                • "Create task due tomorrow: Order supplies"<br>
                • "Schedule inspection for Friday"<br>
                • "High priority: Safety issue at Lot 5"
            </div>
        </div>
        
        <div class="input-section">
            <div class="input-group">
                <input type="text" id="userInput" 
                       placeholder="Type a command..." 
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
        
        <div class="quick-grid">
            <div class="quick-btn" onclick="setCmd('Add urgent task: ')">🚨 Urgent</div>
            <div class="quick-btn" onclick="setCmd('Add task for Mike: ')">👤 For Mike</div>
            <div class="quick-btn" onclick="setCmd('Due tomorrow: ')">📅 Tomorrow</div>
            <div class="quick-btn" onclick="setCmd('Schedule inspection: ')">🔍 Inspection</div>
            <div class="quick-btn" onclick="setCmd('Safety issue: ')">⚠️ Safety</div>
            <div class="quick-btn" onclick="setCmd('Add task: ')">➕ Add Task</div>
        </div>
        
        <div class="help">
            💡 Tips: Say "urgent" for high priority | "for [name]" to assign | "tomorrow/Friday" for due dates
        </div>
    </div>
    
    <script>
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
            
            addMessage(msg, true);
            input.value = '';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg})
                });
                const data = await response.json();
                addMessage(data.response, false, data.success);
            } catch (e) {
                addMessage('Error: ' + e.message, false);
            }
        }
        
        function setCmd(cmd) {
            document.getElementById('userInput').value = cmd;
            document.getElementById('userInput').focus();
        }
    </script>
</body>
</html>
"""

# Configuration
CLICKUP_KEY = os.getenv('CLICKUP_API_KEY', '')
WORKSPACE_ID = os.getenv('WORKSPACE_ID', '')
BASE_URL = 'https://api.clickup.com/api/v2'

# Team members
TEAM_MEMBERS = {
    'mike': 'Mike',
    'tom': 'Tom',
    'sarah': 'Sarah',
    'john': 'John'
}

print("=" * 50)
print("ClickUp Assistant Starting...")
print(f"API Key: {'✅ Connected' if CLICKUP_KEY else '❌ Not Set'}")
print(f"Workspace: {WORKSPACE_ID or 'Not Set'}")
print("=" * 50)

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    
    # Parse the command
    parsed = parse_smart_command(message)
    
    # Create the task
    if CLICKUP_KEY and WORKSPACE_ID:
        response = create_smart_task(parsed)
    else:
        response = {'response': f"Task noted: {parsed['name']}", 'success': False}
    
    return jsonify(response)

def parse_smart_command(message):
    """Smart parsing that doesn't break words"""
    
    result = {
        'name': message,
        'priority': 3,
        'assignee': None,
        'due_date': None,
        'description': ''
    }
    
    lower = message.lower()
    
    # Extract priority
    if any(word in lower for word in ['urgent', 'emergency', 'critical', 'safety']):
        result['priority'] = 1
    elif 'high' in lower:
        result['priority'] = 2
    elif 'low' in lower:
        result['priority'] = 4
    
    # Extract assignee
    for key, name in TEAM_MEMBERS.items():
        if key in lower:
            result['assignee'] = name
    
    # Extract due date
    if 'tomorrow' in lower:
        result['due_date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'today' in lower:
        result['due_date'] = datetime.now().strftime('%Y-%m-%d')
    elif 'friday' in lower:
        days = (4 - datetime.now().weekday()) % 7
        if days == 0: days = 7
        result['due_date'] = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
    
    # Clean task name - only remove command prefixes
    name = message
    name = re.sub(r'^(add|create|schedule|new)\s+(task\s+)?', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^(urgent|high priority|low priority)\s+', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+for\s+\w+', '', name, flags=re.IGNORECASE)  # Remove "for Mike" etc
    name = re.sub(r'(due\s+)?(tomorrow|today|friday)', '', name, flags=re.IGNORECASE)
    name = re.sub(r':\s*', '', name)  # Remove colons
    name = re.sub(r'\s+', ' ', name).strip()
    
    if name:
        result['name'] = name
    
    # Build description
    desc = []
    if result['assignee']:
        desc.append(f"Assigned to: {result['assignee']}")
    if result['due_date']:
        desc.append(f"Due: {result['due_date']}")
    if result['priority'] == 1:
        desc.append("🚨 URGENT")
    desc.append(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    result['description'] = '\n'.join(desc)
    
    return result

def create_smart_task(task_info):
    """Create task in ClickUp"""
    
    try:
        headers = {
            'Authorization': CLICKUP_KEY,
            'Content-Type': 'application/json'
        }
        
        # Get first available list
        list_id = get_first_list()
        if not list_id:
            return {'response': 'Could not find a list', 'success': False}
        
        # Build task data
        task_data = {
            'name': task_info['name'],
            'description': task_info['description'],
            'priority': task_info['priority']
        }
        
        if task_info['due_date']:
            timestamp = int(datetime.strptime(task_info['due_date'], '%Y-%m-%d').timestamp() * 1000)
            task_data['due_date'] = timestamp
        
        # Create task
        response = requests.post(
            f'{BASE_URL}/list/{list_id}/task',
            headers=headers,
            json=task_data,
            timeout=10
        )
        
        if response.status_code == 200:
            # Build response message
            msg = [f"✅ Created: '{task_info['name']}'"]
            
            if task_info['assignee']:
                msg.append(f"👤 Assigned to: {task_info['assignee']}")
            
            if task_info['priority'] == 1:
                msg.append("🚨 Priority: URGENT")
            
            if task_info['due_date']:
                msg.append(f"📅 Due: {task_info['due_date']}")
            
            return {
                'response': '<br>'.join(msg),
                'success': True
            }
    
    except Exception as e:
        print(f"Error: {e}")
    
    return {
        'response': f"Task saved locally: {task_info['name']}",
        'success': False
    }

def get_first_list():
    """Get the first available list ID"""
    
    try:
        headers = {'Authorization': CLICKUP_KEY}
        
        # Get spaces
        r = requests.get(f'{BASE_URL}/team/{WORKSPACE_ID}/space', headers=headers, timeout=10)
        
        if r.status_code == 200:
            spaces = r.json().get('spaces', [])
            
            if spaces:
                space_id = spaces[0]['id']
                
                # Get lists
                r2 = requests.get(f'{BASE_URL}/space/{space_id}/list', headers=headers, timeout=10)
                
                if r2.status_code == 200:
                    lists = r2.json().get('lists', [])
                    if lists:
                        return lists[0]['id']
    
    except Exception as e:
        print(f"Error getting list: {e}")
    
    return None

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'clickup': bool(CLICKUP_KEY),
        'workspace': bool(WORKSPACE_ID)
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
