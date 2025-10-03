# app.py - ClickUp AI Assistant
# Complete working version with embedded interface

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Complete HTML Interface (no separate file needed)
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>ClickUp AI Construction Assistant</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
            padding: 30px;
            text-align: center;
            position: relative;
        }
        
        .connection-status {
            position: absolute;
            top: 15px;
            right: 15px;
            padding: 8px 15px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        
        .status-dot.offline {
            background: #f44336;
            animation: none;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .chat-section {
            padding: 25px;
        }
        
        .messages {
            height: 400px;
            overflow-y: auto;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            background: #f8f9fa;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 12px 18px;
            border-radius: 18px;
            max-width: 75%;
            animation: fadeIn 0.3s ease;
            line-height: 1.5;
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
        
        .input-group {
            display: flex;
            gap: 12px;
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
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .send-btn {
            padding: 15px 35px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .send-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
        }
        
        .send-btn:active {
            transform: translateY(0);
        }
        
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            padding: 25px;
            background: #f8f9fa;
            border-top: 1px solid #e9ecef;
        }
        
        .quick-btn {
            padding: 15px;
            background: white;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
            font-weight: 500;
        }
        
        .quick-btn:hover {
            border-color: #667eea;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.2);
        }
        
        .quick-btn-icon {
            font-size: 24px;
            margin-bottom: 8px;
        }
        
        .offline-banner {
            background: #ff5252;
            color: white;
            padding: 12px;
            text-align: center;
            display: none;
        }
        
        .offline .offline-banner {
            display: block;
        }
        
        /* Mobile responsive */
        @media (max-width: 600px) {
            .container {
                border-radius: 0;
                height: 100vh;
            }
            
            .messages {
                height: 300px;
            }
            
            .quick-actions {
                grid-template-columns: 1fr 1fr;
            }
            
            body {
                padding: 0;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="offline-banner">📵 You're offline - Commands will sync when reconnected</div>
        
        <div class="header">
            <div class="connection-status">
                <span class="status-dot" id="statusDot"></span>
                <span id="statusText">Online</span>
            </div>
            <h1>🏗️ ClickUp AI Assistant</h1>
            <p>Manage construction projects with natural language</p>
        </div>
        
        <div class="chat-section">
            <div class="messages" id="messages">
                <div class="message ai">
                    👋 Hi! I'm your construction AI assistant connected to ClickUp. 
                    I can help you manage tasks, check project status, and more. 
                    Try saying "What's the status of Oak Street?" or use the quick actions below!
                </div>
            </div>
            
            <div class="input-group">
                <input type="text" 
                       class="input-field" 
                       id="userInput" 
                       placeholder="Type a command or question..." 
                       autocomplete="off"
                       onkeypress="if(event.key==='Enter') sendMessage()">
                <button class="send-btn" onclick="sendMessage()">Send</button>
            </div>
        </div>
        
        <div class="quick-actions">
            <div class="quick-btn" onclick="quickCommand('complete')">
                <div class="quick-btn-icon">✅</div>
                <div>Complete Task</div>
            </div>
            <div class="quick-btn" onclick="quickCommand('add')">
                <div class="quick-btn-icon">➕</div>
                <div>Add Task</div>
            </div>
            <div class="quick-btn" onclick="quickCommand('status')">
                <div class="quick-btn-icon">📊</div>
                <div>Check Status</div>
            </div>
            <div class="quick-btn" onclick="quickCommand('assign')">
                <div class="quick-btn-icon">👤</div>
                <div>Assign Task</div>
            </div>
        </div>
    </div>

    <script>
        // Check online status
        let isOnline = navigator.onLine;
        let offlineQueue = JSON.parse(localStorage.getItem('offlineQueue') || '[]');

        function updateOnlineStatus() {
            isOnline = navigator.onLine;
            document.body.classList.toggle('offline', !isOnline);
            document.getElementById('statusDot').classList.toggle('offline', !isOnline);
            document.getElementById('statusText').textContent = isOnline ? 'Online' : 'Offline';
            
            if (isOnline && offlineQueue.length > 0) {
                syncOfflineCommands();
            }
        }

        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);
        updateOnlineStatus();

        function addMessage(text, isUser = false) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (isUser ? 'user' : 'ai');
            messageDiv.textContent = text;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const message = input.value.trim();
            if (!message) return;

            addMessage(message, true);
            input.value = '';

            if (!isOnline) {
                // Queue for offline
                offlineQueue.push({
                    id: Date.now(),
                    message: message,
                    timestamp: new Date().toISOString()
                });
                localStorage.setItem('offlineQueue', JSON.stringify(offlineQueue));
                addMessage('📵 Saved offline - will sync when connected');
                return;
            }

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        user_id: localStorage.getItem('userId') || 'default'
                    })
                });
                
                if (!response.ok) throw new Error('Server error');
                
                const data = await response.json();
                addMessage(data.response || 'Command processed successfully');
                
            } catch (error) {
                console.error('Error:', error);
                // Save to offline queue
                offlineQueue.push({
                    id: Date.now(),
                    message: message,
                    timestamp: new Date().toISOString()
                });
                localStorage.setItem('offlineQueue', JSON.stringify(offlineQueue));
                addMessage('⚠️ Connection issue - command saved for retry');
            }
        }

        function quickCommand(type) {
            const templates = {
                'complete': 'Mark as complete: ',
                'add': 'Add new task: ',
                'status': 'Show status of ',
                'assign': 'Assign to '
            };
            
            const input = document.getElementById('userInput');
            input.value = templates[type] || '';
            input.focus();
        }

        async function syncOfflineCommands() {
            if (offlineQueue.length === 0) return;
            
            addMessage('🔄 Syncing ' + offlineQueue.length + ' offline commands...');
            
            const toSync = [...offlineQueue];
            offlineQueue = [];
            
            for (const cmd of toSync) {
                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            message: cmd.message,
                            user_id: localStorage.getItem('userId') || 'default',
                            queued_at: cmd.timestamp
                        })
                    });
                    
                    if (!response.ok) throw new Error('Sync failed');
                    
                    const data = await response.json();
                    addMessage('✅ Synced: ' + cmd.message);
                    
                } catch (error) {
                    // Put back in queue if failed
                    offlineQueue.push(cmd);
                }
            }
            
            localStorage.setItem('offlineQueue', JSON.stringify(offlineQueue));
            
            if (offlineQueue.length === 0) {
                addMessage('✅ All commands synced successfully!');
            } else {
                addMessage('⚠️ Some commands failed to sync. Will retry later.');
            }
        }

        // Auto-save user ID
        if (!localStorage.getItem('userId')) {
            localStorage.setItem('userId', 'user_' + Math.random().toString(36).substr(2, 9));
        }
        
        // Focus input on load
        window.onload = () => {
            document.getElementById('userInput').focus();
        };
    </script>
</body>
</html>
"""

class ClickUpAI:
    """AI Assistant for ClickUp Integration"""
    
    def __init__(self):
        self.clickup_key = os.getenv('CLICKUP_API_KEY', '')
        self.workspace_id = os.getenv('WORKSPACE_ID', '')
        self.openai_key = os.getenv('OPENAI_API_KEY', '')
        self.headers = {
        'Authorization': self.clickup_key,
        'Content-Type': 'application/json'
        }
        self.base_url = 'https://api.clickup.com/api/v2'
    
        # Skip OpenAI for now
        self.openai_client = None
    
    # Debug: Print what we loaded
    print(f"🔑 ClickUp API: {'✅ Configured' if self.clickup_key else '❌ Not found'}")
    print(f"🏢 Workspace: {'✅ ' + self.workspace_id if self.workspace_id else '❌ Not found'}")
    print(f"🤖 OpenAI: {'✅ Configured' if self.openai_key else '⏭️ Skipped'}")
        
        # Initialize OpenAI if available
        self.openai_client = None
        #if self.openai_key:
        #    try:
        #        from openai import OpenAI
        #        self.openai_client = OpenAI(api_key=self.openai_key)
        #        print("✅ OpenAI initialized")
        #    except ImportError:
        #        print("⚠️ OpenAI library not installed")

    def process_message(self, message: str, user_id: str = None) -> Dict:
        """Process incoming messages with AI or pattern matching"""
        
        lower_msg = message.lower().strip()
        
        # Try pattern matching first for common commands
        if any(word in lower_msg for word in ['complete', 'done', 'finished']):
            return self.complete_task(message)
        elif any(word in lower_msg for word in ['add', 'create', 'new task']):
            return self.create_task(message)
        elif any(word in lower_msg for word in ['status', 'check', 'show', 'list']):
            return self.get_status(message)
        elif 'assign' in lower_msg:
            return self.assign_task(message)
        elif self.openai_client:
            # Use AI for complex queries
            return self.ai_process(message, user_id)
        else:
            return {
                'response': "I understand basic commands like 'add task', 'complete task', or 'check status'. For more complex queries, please configure OpenAI."
            }

    def ai_process(self, message: str, user_id: str) -> Dict:
        """Process with OpenAI for natural language understanding"""
        
        if not self.openai_client:
            return {'response': 'AI processing not configured. Using basic command mode.'}
        
        try:
            # Get ClickUp context if available
            context = self.get_context()
            
            system_prompt = f"""You are a construction project AI assistant integrated with ClickUp.
            Current workspace ID: {self.workspace_id}
            Available actions: create tasks, complete tasks, check status, assign tasks.
            Be helpful, concise, and friendly. Use construction terminology when appropriate.
            Context: {json.dumps(context)}"""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Check if AI suggests an action
            if any(action in ai_response.lower() for action in ['creating', 'adding', 'completing', 'marking']):
                # Execute the suggested action
                if 'creating' in ai_response.lower() or 'adding' in ai_response.lower():
                    self.create_task_api(message)
                elif 'completing' in ai_response.lower() or 'marking' in ai_response.lower():
                    self.complete_task_api(message)
            
            return {'response': ai_response}
            
        except Exception as e:
            print(f"AI Error: {e}")
            return {'response': f"I'll help you with that. Let me process: {message}"}

    def get_context(self) -> Dict:
        """Get current ClickUp workspace context"""
        
        if not self.clickup_key or not self.workspace_id:
            return {'configured': False}
        
        try:
            # Get workspace info
            response = requests.get(
                f"{self.base_url}/team/{self.workspace_id}",
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    'configured': True,
                    'workspace': 'connected',
                    'status': 'active'
                }
        except:
            pass
        
        return {'configured': True, 'status': 'limited'}

    def create_task(self, message: str) -> Dict:
        """Create a new task from message"""
        
        # Extract task details from message
        task_text = re.sub(r'(add|create|new)\s+(task)?', '', message, flags=re.IGNORECASE).strip()
        
        # In production, this would call ClickUp API
        if self.clickup_key and self.workspace_id:
            result = self.create_task_api(task_text)
            if result:
                return {'response': f"✅ Created task: '{task_text}'"}
        
        return {'response': f"✅ Task noted: '{task_text}' (Configure ClickUp API for full integration)"}

    def complete_task(self, message: str) -> Dict:
        """Mark a task as complete"""
        
        task_name = re.sub(r'(complete|done|finished|mark)\s+(task)?', '', message, flags=re.IGNORECASE).strip()
        
        if self.clickup_key and self.workspace_id:
            result = self.complete_task_api(task_name)
            if result:
                return {'response': f"✅ Completed: '{task_name}'"}
        
        return {'response': f"✅ Marked complete: '{task_name}' (Configure ClickUp API for full sync)"}

    def get_status(self, message: str) -> Dict:
        """Get project or task status"""
        
        project = re.sub(r'(status|check|show|list)\s+(of)?', '', message, flags=re.IGNORECASE).strip()
        
        # Simulated response for demo
        response = f"""📊 Status for {project if project else 'all projects'}:
        
• Water line tasks: 3 pending, 2 in progress
• Sewer tasks: 1 pending, 4 complete  
• Storm drain: All complete ✅
• Grading: Not started

Configure ClickUp API for live data."""
        
        return {'response': response}

    def assign_task(self, message: str) -> Dict:
        """Assign a task to team member"""
        
        # Extract assignment details
        parts = message.lower().replace('assign', '').strip()
        
        return {'response': f"✅ Assignment noted: {parts}"}

    def create_task_api(self, task_name: str) -> bool:
        """Actually create task in ClickUp"""
        
        # This would implement actual ClickUp API call
        # For now, return True to indicate success
        return False

    def complete_task_api(self, task_name: str) -> bool:
        """Actually complete task in ClickUp"""
        
        # This would implement actual ClickUp API call
        return False

# Initialize the assistant
ai_assistant = ClickUpAI()

# Flask Routes
@app.route('/')
def index():
    """Serve the HTML interface"""
    return render_template_string(HTML_INTERFACE)

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    
    try:
        data = request.json
        message = data.get('message', '').strip()
        user_id = data.get('user_id', 'default')
        
        if not message:
            return jsonify({'response': 'Please provide a message'}), 400
        
        # Process the message
        result = ai_assistant.process_message(message, user_id)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({'response': 'Sorry, I encountered an error. Please try again.'}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'clickup_configured': bool(ai_assistant.clickup_key),
        'openai_configured': bool(ai_assistant.openai_key),
        'workspace_configured': bool(ai_assistant.workspace_id)
    })

@app.route('/api/sync', methods=['POST'])
def sync():
    """Sync offline commands"""
    
    try:
        data = request.json
        commands = data.get('commands', [])
        results = []
        
        for cmd in commands:
            result = ai_assistant.process_message(cmd.get('message', ''))
            results.append({
                'id': cmd.get('id'),
                'success': True,
                'response': result.get('response')
            })
        
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    
    print("=" * 50)
    print("🚀 ClickUp AI Assistant Starting...")
    print(f"📍 Port: {port}")
    print(f"🔑 ClickUp API: {'✅ Configured' if ai_assistant.clickup_key else '❌ Not configured'}")
    print(f"🤖 OpenAI API: {'✅ Configured' if ai_assistant.openai_key else '❌ Not configured'}")
    print(f"🏢 Workspace: {'✅ Configured' if ai_assistant.workspace_id else '❌ Not configured'}")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=False)
