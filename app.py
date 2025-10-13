import os
import json
import logging
from datetime import datetime, timedelta
from io import BytesIO
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from twilio.twiml.messaging_response import MessagingResponse
import openai
from functools import wraps
import time
import signal
from contextlib import contextmanager

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
CLICKUP_API_KEY = os.environ.get('CLICKUP_API_KEY')
WORKSPACE_ID = os.environ.get('WORKSPACE_ID')
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
MANAGER_PHONES = os.environ.get('MANAGER_PHONES', '').split(',')

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

# Settings file path
SETTINGS_FILE = 'settings.json'

# In-memory storage for tasks (since we can't use SQLAlchemy with Python 3.13)
recent_tasks = []
task_stats = {
    'daily': {'completed': 0, 'created': 0},
    'weekly': {'completed': 0, 'created': 0}
}

# Timeout handler for Twilio (8-second limit)
class TimeoutException(Exception):
    pass

@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# Load/Save Settings Functions
def load_settings():
    """Load settings from JSON file"""
    default_settings = {
        'team_members': ['Mike', 'Tom', 'John', 'Dave', 'Steve'],
        'job_types': ['Framing', 'Foundation', 'Electrical', 'Plumbing', 'Roofing', 'Drywall'],
        'projects': []
    }
    
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                # Ensure all keys exist
                for key in default_settings:
                    if key not in settings:
                        settings[key] = default_settings[key]
                return settings
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
    
    return default_settings

def save_settings(settings):
    """Save settings to JSON file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

# ClickUp API Functions
def get_clickup_headers():
    """Get headers for ClickUp API requests"""
    return {
        'Authorization': CLICKUP_API_KEY,
        'Content-Type': 'application/json'
    }

def sync_projects():
    """Sync projects from ClickUp"""
    try:
        # Get all spaces in workspace
        spaces_url = f"https://api.clickup.com/api/v2/team/{WORKSPACE_ID}/space"
        response = requests.get(spaces_url, headers=get_clickup_headers())
        
        if response.status_code != 200:
            logger.error(f"Failed to get spaces: {response.status_code}")
            return []
        
        spaces = response.json().get('spaces', [])
        all_lists = []
        
        # Get all lists from all spaces
        for space in spaces:
            space_id = space['id']
            lists_url = f"https://api.clickup.com/api/v2/space/{space_id}/list"
            list_response = requests.get(lists_url, headers=get_clickup_headers())
            
            if list_response.status_code == 200:
                lists = list_response.json().get('lists', [])
                for lst in lists:
                    all_lists.append({
                        'id': lst['id'],
                        'name': lst['name']
                    })
        
        # Update settings with synced projects
        settings = load_settings()
        settings['projects'] = all_lists
        save_settings(settings)
        
        logger.info(f"Synced {len(all_lists)} projects from ClickUp")
        return all_lists
        
    except Exception as e:
        logger.error(f"Error syncing projects: {e}")
        return []

def get_team_members():
    """Get team members from ClickUp workspace"""
    try:
        url = f"https://api.clickup.com/api/v2/team/{WORKSPACE_ID}"
        response = requests.get(url, headers=get_clickup_headers())
        
        if response.status_code == 200:
            team = response.json()
            members = []
            for member in team.get('team', {}).get('members', []):
                user = member.get('user', {})
                members.append({
                    'id': user.get('id'),
                    'username': user.get('username'),
                    'email': user.get('email')
                })
            return members
    except Exception as e:
        logger.error(f"Error getting team members: {e}")
    
    return []

def create_clickup_task(project_name, task_description, assignee=None, priority=None, due_date=None, attachments=None):
    """Create a task in ClickUp"""
    try:
        settings = load_settings()
        
        # Find project/list ID
        list_id = None
        for project in settings['projects']:
            if project_name.lower() in project['name'].lower():
                list_id = project['id']
                break
        
        if not list_id:
            # Try to sync projects and check again
            sync_projects()
            settings = load_settings()
            for project in settings['projects']:
                if project_name.lower() in project['name'].lower():
                    list_id = project['id']
                    break
        
        if not list_id:
            return False, "Project not found"
        
        # Create task
        url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
        
        task_data = {
            'name': task_description,
            'description': f'Created via SMS/Web Assistant'
        }
        
        # Set priority
        if priority:
            priority_map = {
                'urgent': 1,
                'high': 2,
                'normal': 3,
                'low': 4
            }
            task_data['priority'] = priority_map.get(priority.lower(), 3)
        
        # Set due date
        if due_date:
            task_data['due_date'] = int(due_date.timestamp() * 1000)
        
        # Create the task
        response = requests.post(url, json=task_data, headers=get_clickup_headers())
        
        if response.status_code == 200:
            task = response.json()
            task_id = task['id']
            
            # Add to recent tasks
            recent_tasks.append({
                'id': task_id,
                'name': task_description,
                'project': project_name,
                'created_at': datetime.now()
            })
            
            # Update stats
            task_stats['daily']['created'] += 1
            task_stats['weekly']['created'] += 1
            
            # Handle attachments
            if attachments:
                for attachment in attachments:
                    upload_attachment_to_task(task_id, attachment)
            
            return True, task_id
        else:
            return False, f"Failed to create task: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return False, str(e)

def upload_attachment_to_task(task_id, attachment_url):
    """Upload attachment to ClickUp task"""
    try:
        # Download the file
        response = requests.get(attachment_url)
        if response.status_code != 200:
            logger.error(f"Failed to download attachment: {attachment_url}")
            return False
        
        # Upload to ClickUp
        url = f"https://api.clickup.com/api/v2/task/{task_id}/attachment"
        
        files = {
            'attachment': ('image.jpg', BytesIO(response.content), 'image/jpeg')
        }
        
        headers = {
            'Authorization': CLICKUP_API_KEY
        }
        
        response = requests.post(url, files=files, headers=headers)
        
        if response.status_code == 200:
            logger.info(f"Successfully uploaded attachment to task {task_id}")
            return True
        else:
            # If upload fails, add attachment URL as comment
            comment_url = f"https://api.clickup.com/api/v2/task/{task_id}/comment"
            comment_data = {
                'comment_text': f"Attachment: {attachment_url}"
            }
            requests.post(comment_url, json=comment_data, headers=get_clickup_headers())
            logger.warning(f"Added attachment as comment instead: {attachment_url}")
            return True
            
    except Exception as e:
        logger.error(f"Error uploading attachment: {e}")
        return False

def get_tasks_for_project(project_name):
    """Get tasks for a specific project"""
    try:
        settings = load_settings()
        
        # Find project/list ID
        list_id = None
        for project in settings['projects']:
            if project_name.lower() in project['name'].lower():
                list_id = project['id']
                break
        
        if not list_id:
            return []
        
        url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
        params = {
            'statuses[]': ['open', 'in progress']
        }
        
        response = requests.get(url, params=params, headers=get_clickup_headers())
        
        if response.status_code == 200:
            tasks = response.json().get('tasks', [])
            return tasks
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
    
    return []

def complete_task(task_id):
    """Mark a task as complete in ClickUp"""
    try:
        url = f"https://api.clickup.com/api/v2/task/{task_id}"
        data = {
            'status': 'complete'
        }
        
        response = requests.put(url, json=data, headers=get_clickup_headers())
        
        if response.status_code == 200:
            # Update stats
            task_stats['daily']['completed'] += 1
            task_stats['weekly']['completed'] += 1
            return True
        
    except Exception as e:
        logger.error(f"Error completing task: {e}")
    
    return False

def parse_message_with_ai(message):
    """Use OpenAI to parse natural language message"""
    try:
        prompt = f"""Parse this construction message and extract:
1. Task description (clean, without assignee name at start)
2. Assignee name (if mentioned - look for: Mike, Tom, John, Dave, Steve)
3. Priority (if mentioned: urgent, high, normal, low)
4. Due date (if mentioned: today, tomorrow, specific date)
5. Project hint (location, type of work)

Message: "{message}"

Return as JSON with keys: task, assignee, priority, due_date, project_hint
If assignee is mentioned in the task, don't duplicate their name in the task description."""

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            temperature=0.3
        )
        
        result = response.choices[0].text.strip()
        
        # Try to parse JSON response
        try:
            parsed = json.loads(result)
            
            # Clean up task description to avoid duplication
            task = parsed.get('task', message)
            assignee = parsed.get('assignee', '')
            
            # Remove assignee name from start of task if present
            if assignee and task.lower().startswith(assignee.lower()):
                task = task[len(assignee):].strip()
                # Remove leading colons or dashes
                task = task.lstrip(':').lstrip('-').strip()
            
            parsed['task'] = task
            return parsed
            
        except json.JSONDecodeError:
            # Fallback to basic parsing
            return {'task': message, 'assignee': None, 'priority': None, 'due_date': None, 'project_hint': None}
            
    except Exception as e:
        logger.error(f"Error parsing with AI: {e}")
        return {'task': message, 'assignee': None, 'priority': None, 'due_date': None, 'project_hint': None}

def process_sms_command(body, from_number, media_urls=None):
    """Process SMS commands"""
    body = body.strip().lower()
    
    # Help command
    if body == 'help':
        return """Commands:
help - Show this list
status - Show projects
list [project] - Show tasks
done [#] - Complete task
report - Today's stats
create project [name]
[project]: [task] - Add task
Send photo + text for task"""
    
    # Status command
    elif body == 'status':
        settings = load_settings()
        if not settings['projects']:
            sync_projects()
            settings = load_settings()
        
        response = "Projects:\n"
        for project in settings['projects'][:10]:  # Limit to 10 for SMS
            response += f"- {project['name']}\n"
        return response
    
    # List tasks command
    elif body.startswith('list'):
        parts = body.split(' ', 1)
        if len(parts) > 1:
            project_name = parts[1]
            tasks = get_tasks_for_project(project_name)
            
            if not tasks:
                return f"No open tasks in {project_name}"
            
            response = f"Tasks in {project_name}:\n"
            for i, task in enumerate(tasks[:10], 1):  # Limit to 10 for SMS
                response += f"{i}. {task['name']}\n"
            return response
        else:
            return "Please specify a project: list [project name]"
    
    # Complete task command
    elif body.startswith('done'):
        parts = body.split(' ', 1)
        if len(parts) > 1:
            try:
                task_num = int(parts[1]) - 1
                if 0 <= task_num < len(recent_tasks):
                    task = recent_tasks[task_num]
                    if complete_task(task['id']):
                        return f"✓ Completed: {task['name']}"
                    else:
                        return "Failed to complete task"
                else:
                    return "Invalid task number"
            except ValueError:
                return "Please provide a task number: done [#]"
        else:
            return "Please provide a task number: done [#]"
    
    # Report command
    elif body == 'report':
        return f"""Today's Report:
Created: {task_stats['daily']['created']} tasks
Completed: {task_stats['daily']['completed']} tasks
Active: {len(recent_tasks)} in memory"""
    
    # Create project command
    elif body.startswith('create project'):
        project_name = body.replace('create project', '').strip()
        if project_name:
            # This would need ClickUp API to create space/list
            return f"Project '{project_name}' creation requested. Use ClickUp web interface for now."
        else:
            return "Please provide a project name: create project [name]"
    
    # Safety issue - urgent task
    elif 'safety' in body or 'urgent' in body or 'emergency' in body:
        parsed = parse_message_with_ai(body)
        
        # Try to determine project
        settings = load_settings()
        project = settings['projects'][0]['name'] if settings['projects'] else 'General'
        
        success, result = create_clickup_task(
            project_name=project,
            task_description=f"🚨 URGENT: {parsed['task']}",
            priority='urgent',
            attachments=media_urls
        )
        
        if success:
            # Notify managers if configured
            if MANAGER_PHONES:
                # Would send SMS to managers here
                pass
            return f"🚨 Urgent task created: {parsed['task']}"
        else:
            return f"Failed to create urgent task: {result}"
    
    # Task creation with project prefix
    elif ':' in body:
        parts = body.split(':', 1)
        project_hint = parts[0].strip()
        task_description = parts[1].strip()
        
        # Parse with AI
        parsed = parse_message_with_ai(task_description)
        
        # Find matching project
        settings = load_settings()
        project_name = None
        for project in settings['projects']:
            if project_hint in project['name'].lower():
                project_name = project['name']
                break
        
        if not project_name:
            project_name = settings['projects'][0]['name'] if settings['projects'] else 'General'
        
        # Process due date
        due_date = None
        if parsed.get('due_date'):
            if parsed['due_date'] == 'today':
                due_date = datetime.now()
            elif parsed['due_date'] == 'tomorrow':
                due_date = datetime.now() + timedelta(days=1)
        
        success, result = create_clickup_task(
            project_name=project_name,
            task_description=parsed['task'],
            assignee=parsed.get('assignee'),
            priority=parsed.get('priority'),
            due_date=due_date,
            attachments=media_urls
        )
        
        if success:
            response = f"✓ Task created: {parsed['task']}"
            if parsed.get('assignee'):
                response += f" (Assigned to {parsed['assignee']})"
            return response
        else:
            return f"Failed to create task: {result}"
    
    # Default: try to parse as task
    else:
        parsed = parse_message_with_ai(body)
        
        # Try to find a project
        settings = load_settings()
        project_name = settings['projects'][0]['name'] if settings['projects'] else 'General'
        
        # Process due date
        due_date = None
        if parsed.get('due_date'):
            if parsed['due_date'] == 'today':
                due_date = datetime.now()
            elif parsed['due_date'] == 'tomorrow':
                due_date = datetime.now() + timedelta(days=1)
        
        success, result = create_clickup_task(
            project_name=project_name,
            task_description=parsed['task'],
            assignee=parsed.get('assignee'),
            priority=parsed.get('priority'),
            due_date=due_date,
            attachments=media_urls
        )
        
        if success:
            return f"✓ Task created: {parsed['task']}"
        else:
            return "Couldn't understand. Try: [project]: [task] or type 'help'"

# Web Interface HTML
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ClickUp Construction Assistant</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        .main-card {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .input-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }
        input, select, textarea {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        textarea {
            min-height: 120px;
            resize: vertical;
            font-family: inherit;
        }
        .button-group {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin: 20px 0;
        }
        button {
            padding: 12px 20px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        .btn-secondary {
            background: #f5f5f5;
            color: #333;
        }
        .btn-secondary:hover {
            background: #e0e0e0;
        }
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 20px;
        }
        .quick-btn {
            padding: 15px;
            text-align: center;
            background: #f8f9fa;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .quick-btn:hover {
            background: #e9ecef;
            transform: translateY(-2px);
        }
        .status-message {
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            display: none;
        }
        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .info-box {
            background: #e8f4fd;
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }
        .tab {
            padding: 12px 24px;
            background: none;
            border: none;
            color: #666;
            font-weight: 600;
            cursor: pointer;
            position: relative;
            transition: all 0.3s;
        }
        .tab.active {
            color: #667eea;
        }
        .tab.active::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            right: 0;
            height: 2px;
            background: #667eea;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .settings-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        @media (max-width: 768px) {
            .settings-grid {
                grid-template-columns: 1fr;
            }
            .header h1 {
                font-size: 1.8rem;
            }
        }
        .list-item {
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            margin-bottom: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .remove-btn {
            background: #dc3545;
            color: white;
            padding: 5px 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        }
        .remove-btn:hover {
            background: #c82333;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ ClickUp Construction Assistant</h1>
            <p>Manage tasks with natural language - Web & SMS enabled</p>
        </div>

        <div class="main-card">
            <div class="tabs">
                <button class="tab active" onclick="switchTab('tasks')">Create Task</button>
                <button class="tab" onclick="switchTab('settings')">Settings</button>
                <button class="tab" onclick="switchTab('help')">Help</button>
            </div>

            <!-- Tasks Tab -->
            <div id="tasks-tab" class="tab-content active">
                <div class="input-group">
                    <label for="project-select">Project</label>
                    <select id="project-select">
                        <option value="">Loading projects...</option>
                    </select>
                </div>

                <div class="input-group">
                    <label for="task-input">Task Description</label>
                    <textarea id="task-input" placeholder="Example: Mike needs to fix the plumbing leak in unit 5 by tomorrow"></textarea>
                </div>

                <div class="info-box">
                    <strong>💡 AI Auto-Detection:</strong> Just describe the task naturally. The system will detect:
                    <ul style="margin-top: 10px; margin-left: 20px;">
                        <li>Team member assignments (Mike, Tom, John, etc.)</li>
                        <li>Priority levels (urgent, high, normal, low)</li>
                        <li>Due dates (today, tomorrow, next week)</li>
                    </ul>
                </div>

                <button class="btn-primary" onclick="createTask()" style="width: 100%;">
                    Create Task with AI
                </button>

                <div class="quick-actions">
                    <div class="quick-btn" onclick="quickTask('safety')">🚨 Safety Issue</div>
                    <div class="quick-btn" onclick="quickTask('inspection')">🔍 Inspection</div>
                    <div class="quick-btn" onclick="quickTask('materials')">📦 Materials Needed</div>
                    <div class="quick-btn" onclick="quickTask('cleanup')">🧹 Site Cleanup</div>
                    <div class="quick-btn" onclick="quickTask('meeting')">👥 Team Meeting</div>
                    <div class="quick-btn" onclick="quickTask('weather')">🌧️ Weather Delay</div>
                </div>

                <div id="status-message" class="status-message"></div>
            </div>

            <!-- Settings Tab -->
            <div id="settings-tab" class="tab-content">
                <div class="settings-grid">
                    <div>
                        <h3>Team Members</h3>
                        <div id="team-list" style="margin: 10px 0;"></div>
                        <div style="display: flex; gap: 10px;">
                            <input type="text" id="new-member" placeholder="Add team member">
                            <button class="btn-secondary" onclick="addTeamMember()">Add</button>
                        </div>
                    </div>
                    <div>
                        <h3>Job Types</h3>
                        <div id="job-list" style="margin: 10px 0;"></div>
                        <div style="display: flex; gap: 10px;">
                            <input type="text" id="new-job" placeholder="Add job type">
                            <button class="btn-secondary" onclick="addJobType()">Add</button>
                        </div>
                    </div>
                </div>
                <button class="btn-primary" onclick="saveSettings()" style="width: 100%; margin-top: 20px;">
                    Save Settings
                </button>
            </div>

            <!-- Help Tab -->
            <div id="help-tab" class="tab-content">
                <h2>SMS Commands</h2>
                <div class="info-box" style="margin-top: 20px;">
                    <p><strong>Text to: {{ phone_number }}</strong></p>
                </div>
                
                <h3 style="margin-top: 20px;">Available Commands:</h3>
                <ul style="margin-left: 20px; line-height: 2;">
                    <li><code>help</code> - Show command list</li>
                    <li><code>status</code> - List all projects</li>
                    <li><code>list [project]</code> - Show tasks in project</li>
                    <li><code>done [task#]</code> - Mark task complete</li>
                    <li><code>report</code> - Today's statistics</li>
                    <li><code>create project [name]</code> - Create new project</li>
                    <li><code>[project]: [task]</code> - Add task to project</li>
                    <li><code>safety issue</code> - Create urgent task</li>
                    <li>Send photo + text - Create task with image</li>
                </ul>

                <h3 style="margin-top: 30px;">Examples:</h3>
                <ul style="margin-left: 20px; line-height: 2;">
                    <li>"oak street: fix broken window in unit 3"</li>
                    <li>"Mike found water damage needs urgent repair"</li>
                    <li>"done 1" (completes task #1)</li>
                    <li>Send photo of damage + "roof leak at main building"</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        let currentSettings = {};

        // Initialize
        window.onload = function() {
            loadProjects();
            loadSettings();
        };

        function switchTab(tab) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tabBtn => {
                tabBtn.classList.remove('active');
            });

            // Show selected tab
            document.getElementById(tab + '-tab').classList.add('active');
            event.target.classList.add('active');
        }

        async function loadProjects() {
            try {
                const response = await fetch('/api/projects');
                const projects = await response.json();
                
                const select = document.getElementById('project-select');
                select.innerHTML = '<option value="">Select a project...</option>';
                
                projects.forEach(project => {
                    const option = document.createElement('option');
                    option.value = project.name;
                    option.textContent = project.name;
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading projects:', error);
            }
        }

        async function loadSettings() {
            try {
                const response = await fetch('/api/settings');
                currentSettings = await response.json();
                
                // Display team members
                const teamList = document.getElementById('team-list');
                teamList.innerHTML = '';
                currentSettings.team_members.forEach(member => {
                    teamList.innerHTML += `
                        <div class="list-item">
                            ${member}
                            <button class="remove-btn" onclick="removeMember('${member}')">Remove</button>
                        </div>
                    `;
                });

                // Display job types
                const jobList = document.getElementById('job-list');
                jobList.innerHTML = '';
                currentSettings.job_types.forEach(job => {
                    jobList.innerHTML += `
                        <div class="list-item">
                            ${job}
                            <button class="remove-btn" onclick="removeJob('${job}')">Remove</button>
                        </div>
                    `;
                });
            } catch (error) {
                console.error('Error loading settings:', error);
            }
        }

        async function createTask() {
            const project = document.getElementById('project-select').value;
            const description = document.getElementById('task-input').value;
            
            if (!project || !description) {
                showMessage('Please select a project and enter a task description', 'error');
                return;
            }

            try {
                const response = await fetch('/api/task', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        project: project,
                        description: description
                    })
                });

                const result = await response.json();
                
                if (result.success) {
                    showMessage(`✓ Task created successfully! ${result.details || ''}`, 'success');
                    document.getElementById('task-input').value = '';
                } else {
                    showMessage('Failed to create task: ' + result.message, 'error');
                }
            } catch (error) {
                showMessage('Error creating task: ' + error.message, 'error');
            }
        }

        function quickTask(type) {
            const taskInput = document.getElementById('task-input');
            const templates = {
                'safety': 'URGENT: Safety issue found at ',
                'inspection': 'Schedule inspection for ',
                'materials': 'Need materials: ',
                'cleanup': 'Site cleanup needed at ',
                'meeting': 'Team meeting scheduled for ',
                'weather': 'Work delayed due to weather at '
            };
            
            taskInput.value = templates[type] || '';
            taskInput.focus();
        }

        function addTeamMember() {
            const input = document.getElementById('new-member');
            if (input.value) {
                currentSettings.team_members.push(input.value);
                input.value = '';
                loadSettings();
            }
        }

        function addJobType() {
            const input = document.getElementById('new-job');
            if (input.value) {
                currentSettings.job_types.push(input.value);
                input.value = '';
                loadSettings();
            }
        }

        function removeMember(member) {
            currentSettings.team_members = currentSettings.team_members.filter(m => m !== member);
            loadSettings();
        }

        function removeJob(job) {
            currentSettings.job_types = currentSettings.job_types.filter(j => j !== job);
            loadSettings();
        }

        async function saveSettings() {
            try {
                const response = await fetch('/api/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(currentSettings)
                });

                const result = await response.json();
                
                if (result.success) {
                    showMessage('Settings saved successfully!', 'success');
                } else {
                    showMessage('Failed to save settings', 'error');
                }
            } catch (error) {
                showMessage('Error saving settings: ' + error.message, 'error');
            }
        }

        function showMessage(message, type) {
            const messageDiv = document.getElementById('status-message');
            messageDiv.textContent = message;
            messageDiv.className = 'status-message ' + type;
            messageDiv.style.display = 'block';
            
            setTimeout(() => {
                messageDiv.style.display = 'none';
            }, 5000);
        }
    </script>
</body>
</html>
'''

# Flask Routes

@app.route('/')
def index():
    """Render the main web interface"""
    return render_template_string(HTML_TEMPLATE, phone_number=TWILIO_PHONE_NUMBER or 'Not configured')

@app.route('/api/projects', methods=['GET'])
def api_projects():
    """Get list of projects"""
    settings = load_settings()
    return jsonify(settings['projects'])

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update settings"""
    if request.method == 'GET':
        settings = load_settings()
        return jsonify(settings)
    else:
        settings = request.json
        if save_settings(settings):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Failed to save settings'}), 500

@app.route('/api/task', methods=['POST'])
def api_create_task():
    """Create a task via web interface"""
    try:
        data = request.json
        project = data.get('project')
        description = data.get('description')
        
        if not project or not description:
            return jsonify({'success': False, 'message': 'Missing project or description'}), 400
        
        # Parse with AI
        parsed = parse_message_with_ai(description)
        
        # Process due date
        due_date = None
        if parsed.get('due_date'):
            if parsed['due_date'] == 'today':
                due_date = datetime.now()
            elif parsed['due_date'] == 'tomorrow':
                due_date = datetime.now() + timedelta(days=1)
        
        # Create task
        success, result = create_clickup_task(
            project_name=project,
            task_description=parsed['task'],
            assignee=parsed.get('assignee'),
            priority=parsed.get('priority'),
            due_date=due_date
        )
        
        if success:
            details = []
            if parsed.get('assignee'):
                details.append(f"Assigned to {parsed['assignee']}")
            if parsed.get('priority'):
                details.append(f"Priority: {parsed['priority']}")
            if parsed.get('due_date'):
                details.append(f"Due: {parsed['due_date']}")
            
            return jsonify({
                'success': True,
                'task_id': result,
                'details': ' | '.join(details) if details else ''
            })
        else:
            return jsonify({'success': False, 'message': result}), 500
            
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/sms', methods=['POST'])
def sms_webhook():
    """Handle incoming SMS messages"""
    try:
        with time_limit(7):  # 7 second timeout for Twilio
            # Get message details
            body = request.values.get('Body', '').strip()
            from_number = request.values.get('From', '')
            
            # Get media URLs if present
            num_media = int(request.values.get('NumMedia', 0))
            media_urls = []
            for i in range(num_media):
                media_url = request.values.get(f'MediaUrl{i}')
                if media_url:
                    media_urls.append(media_url)
            
            # Process the command
            response_text = process_sms_command(body, from_number, media_urls)
            
            # Create response
            resp = MessagingResponse()
            resp.message(response_text)
            
            return str(resp)
            
    except TimeoutException:
        # Return simple response on timeout
        resp = MessagingResponse()
        resp.message("Processing... Check ClickUp for task.")
        return str(resp)
    except Exception as e:
        logger.error(f"Error handling SMS: {e}")
        resp = MessagingResponse()
        resp.message("Error processing message. Try again or type 'help'")
        return str(resp)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# Initialize on startup
@app.before_first_request
def initialize():
    """Initialize the application"""
    logger.info("Initializing ClickUp Construction Assistant...")
    
    # Sync projects from ClickUp
    projects = sync_projects()
    logger.info(f"Loaded {len(projects)} projects")
    
    # Load settings
    settings = load_settings()
    logger.info(f"Settings loaded: {len(settings['team_members'])} team members, {len(settings['job_types'])} job types")

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
