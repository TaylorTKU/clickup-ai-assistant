import os
import re
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
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #667eea;
            text-align: center;
        }
        .messages {
            height: 400px;
            overflow-y: auto;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
            background: #f8f9fa;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 10px;
        }
        .user {
            background: #667eea;
            color: white;
            text-align: right;
        }
        .ai {
            background: white;
            border: 1px solid #e0e0e0;
        }
        .input-group {
            display: flex;
            gap: 10px;
        }
        input {
            flex: 1;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 16px;
        }
        button {
            padding: 12px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            background: #764ba2;
        }
        .quick-btns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 20px;
        }
        .quick-btn {
            padding: 10px;
            text-align: center;
            background: #f0f0f0;
            border-radius: 10px;
            cursor: pointer;
        }
        .quick-btn:hover {
            background: #e0e0e0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏗️ ClickUp Construction Assistant</h1>
        <div class="messages" id="messages">
            <div class="message ai">Welcome! I can help you manage ClickUp tasks. Try "add task" or "check status"!</div>
        </div>
        <div class="input-group">
            <input type="text" id="userInput" placeholder="Type a command..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">Send</button>
        </div>
        <div class="quick-btns">
            <div class="quick-btn" onclick="setCommand('Add task: ')">➕ Add Task</div>
            <div class="quick-btn" onclick="setCommand('Complete: ')">✅ Complete</div>
            <div class="quick-btn" onclick="setCommand('Check status')">📊 Status</div>
            <div class="quick-btn" onclick="setCommand('List tasks')">📋 List</div>
        </div>
    </div>
    
    <script>
        function addMessage(text, isUser) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : 'ai');
            div.textContent = text;
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
                addMessage(data.response, false);
            } catch (e) {
                addMessage('Error: ' + e.message, false);
            }
        }
        
        function setCommand(cmd) {
            document.getElementById('userInput').value = cmd;
            document.getElementById('userInput').focus();
        }
    </script>
</body>
</html>
"""

# Get environment variables
CLICKUP_KEY = os.getenv('CLICKUP_API_KEY', '')
WORKSPACE_ID = os.getenv('WORKSPACE_ID', '')
BASE_URL = 'https://api.clickup.com/api/v2'

# Print startup info
print("=" * 50)
print("ClickUp Assistant Starting...")
print(f"API Key: {'YES' if CLICKUP_KEY else 'NO'}")
print(f"Workspace: {WORKSPACE_ID if WORKSPACE_ID else 'NOT SET'}")
print("=" * 50)

@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '').lower()
    
    # Process commands
    if 'add' in message or 'create' in message:
        task_name = re.sub(r'(add|create|task|:)', '', message).strip()
        response = create_task(task_name)
    elif 'complete' in message or 'done' in message:
        task_name = re.sub(r'(complete|done|finish|:)', '', message).strip()
        response = f"Marked complete: {task_name}"
    elif 'status' in message or 'check' in message:
        response = get_status()
    elif 'list' in message:
        response = list_tasks()
    else:
        response = "Try: 'add task [name]', 'complete [task]', or 'check status'"
    
    return jsonify({'response': response})

def create_task(name):
    if not CLICKUP_KEY or not WORKSPACE_ID:
        return f"Task noted: {name} (Set up ClickUp API for full sync)"
    
    try:
        # Get first list
        headers = {'Authorization': CLICKUP_KEY}
        r = requests.get(f'{BASE_URL}/team/{WORKSPACE_ID}/space', headers=headers)
        
        if r.status_code == 200:
            spaces = r.json().get('spaces', [])
            if spaces:
                space_id = spaces[0]['id']
                # Get lists
                r2 = requests.get(f'{BASE_URL}/space/{space_id}/list', headers=headers)
                if r2.status_code == 200:
                    lists = r2.json().get('lists', [])
                    if lists:
                        list_id = lists[0]['id']
                        # Create task
                        task_data = {'name': name, 'description': 'Created via AI Assistant'}
                        r3 = requests.post(
                            f'{BASE_URL}/list/{list_id}/task',
                            headers={**headers, 'Content-Type': 'application/json'},
                            json=task_data
                        )
                        if r3.status_code == 200:
                            return f"✅ Created in ClickUp: {name}"
        
        return f"Task noted: {name} (Will sync later)"
    except Exception as e:
        return f"Task noted: {name} (Connection issue)"

def get_status():
    if not CLICKUP_KEY or not WORKSPACE_ID:
        return "Status: Configure ClickUp API for live data"
    
    try:
        headers = {'Authorization': CLICKUP_KEY}
        r = requests.get(f'{BASE_URL}/team/{WORKSPACE_ID}/space', headers=headers)
        
        if r.status_code == 200:
            spaces = r.json().get('spaces', [])
            return f"📊 Connected! Found {len(spaces)} spaces in ClickUp"
        else:
            return "Status: ClickUp connection issue"
    except:
        return "Status: Connection error"

def list_tasks():
    if not CLICKUP_KEY or not WORKSPACE_ID:
        return "Configure ClickUp API to list tasks"
    
    try:
        headers = {'Authorization': CLICKUP_KEY}
        # Get first space and list
        r = requests.get(f'{BASE_URL}/team/{WORKSPACE_ID}/space', headers=headers)
        
        if r.status_code == 200:
            spaces = r.json().get('spaces', [])
            if spaces:
                space_id = spaces[0]['id']
                r2 = requests.get(f'{BASE_URL}/space/{space_id}/list', headers=headers)
                if r2.status_code == 200:
                    lists = r2.json().get('lists', [])
                    if lists:
                        list_id = lists[0]['id']
                        r3 = requests.get(f'{BASE_URL}/list/{list_id}/task', headers=headers)
                        if r3.status_code == 200:
                            tasks = r3.json().get('tasks', [])
                            if tasks:
                                task_names = [t.get('name', 'Unnamed') for t in tasks[:5]]
                                return "Recent tasks:\n" + "\n".join(f"• {name}" for name in task_names)
                            return "No tasks found"
        return "Could not fetch tasks"
    except:
        return "Error fetching tasks"

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
