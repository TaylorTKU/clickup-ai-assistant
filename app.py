# Enhanced SMS handler with actual task creation, OpenAI, and MMS support
# Add this to replace your current handle_sms function and add new functions

import openai
import base64
from urllib.parse import urlparse

# Configure OpenAI (add this near your other configuration)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
    print(f"🤖 OpenAI: {'Connected' if OPENAI_API_KEY else 'Not configured'}")

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
        # Download image from Twilio URL
        # Note: You'll need to authenticate with Twilio to download
        response = requests.get(
            media_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        )
        
        if response.status_code == 200:
            # Save temporarily or upload to ClickUp
            image_data = response.content
            
            # Create task with description mentioning the photo
            task_description = f"📷 Photo attached\n{message_text}\nFrom: {from_number}"
            
            return {
                'has_image': True,
                'image_data': image_data,
                'description': task_description
            }
    except Exception as e:
        print(f"Error processing MMS: {e}")
    
    return {'has_image': False}

def create_clickup_task_with_attachment(task_info, image_data=None):
    """Enhanced task creation that can include attachments"""
    headers = {
        'Authorization': CLICKUP_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        # First create the task (existing logic)
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
        
        task_response = requests.post(
            f'{BASE_URL}/list/{list_id}/task',
            headers=headers,
            json=task_data,
            timeout=10
        )
        
        if task_response.status_code == 200:
            task = task_response.json()
            task_id = task['id']
            
            # If we have an image, attach it
            if image_data:
                attachment_url = f'{BASE_URL}/task/{task_id}/attachment'
                files = {'file': ('photo.jpg', image_data, 'image/jpeg')}
                headers_attach = {'Authorization': CLICKUP_KEY}
                
                attach_response = requests.post(
                    attachment_url,
                    headers=headers_attach,
                    files=files,
                    timeout=15
                )
                
                if attach_response.status_code == 200:
                    return {'success': True, 'task': task, 'attachment': True}
            
            return {'success': True, 'task': task}
        else:
            return {'success': False, 'error': 'Could not create task'}
            
    except Exception as e:
        print(f"Error creating task with attachment: {e}")
        return {'success': False, 'error': str(e)}

@app.route('/sms', methods=['POST'])
def handle_sms():
    """Enhanced SMS handler with OpenAI, MMS support, and actual task creation"""
    
    from_number = request.form.get('From', '')
    message_body = request.form.get('Body', '').strip()
    media_url = request.form.get('MediaUrl0', '')  # First media attachment
    num_media = request.form.get('NumMedia', '0')
    
    print(f"SMS from {from_number}: {message_body}")
    if num_media != '0':
        print(f"MMS with {num_media} media files")
    
    # Create response
    resp = MessagingResponse()
    
    try:
        lower = message_body.lower()
        
        # Quick commands that don't need ClickUp
        if "help" in lower:
            msg = "Commands:\n"
            msg += "📋 status - list projects\n"
            msg += "🏗️ create project [name]\n"
            msg += "📝 [project]: [task]\n"
            msg += "🚨 safety issue at [project]\n"
            msg += "📸 Send photo + description\n"
            msg += "✅ done [task#]"
            resp.message(msg)
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        if "status" in lower:
            msg = "Projects:\n"
            if SETTINGS.get('projects'):
                for key, project in SETTINGS['projects'].items():
                    msg += f"• {key}: {project['name']}\n"
                    if len(msg) > 140:
                        msg += "..."
                        break
            else:
                msg += "None yet"
            resp.message(msg)
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        # Handle common construction commands
        image_data = None
        if num_media != '0' and media_url:
            # Process MMS image
            mms_result = handle_mms_image(media_url, message_body, from_number)
            if mms_result['has_image']:
                image_data = mms_result['image_data']
                # Enhance message with photo context
                if not message_body:
                    message_body = "Site photo"
                message_body = f"📸 {message_body}"
        
        # Check for safety issues (high priority)
        if any(word in lower for word in ['safety', 'danger', 'hazard', 'emergency', 'urgent', 'accident']):
            # Parse as urgent task
            project_match = detect_project_from_message(message_body)
            task_info = {
                'type': 'create_task',
                'name': message_body,
                'display_name': f"🚨 SAFETY: {message_body}",
                'priority': 1,  # Highest priority
                'list_id': project_match[0] if project_match[0] else None,
                'description': f"⚠️ SAFETY ISSUE reported via SMS\nFrom: {from_number}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M')}\nOriginal: {message_body}"
            }
        
        # Check for inspection tasks
        elif 'inspection' in lower:
            project_match = detect_project_from_message(message_body)
            due_date = None
            if 'tomorrow' in lower:
                due_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            elif 'today' in lower:
                due_date = datetime.now().strftime('%Y-%m-%d')
            
            task_info = {
                'type': 'create_task',
                'name': message_body,
                'display_name': f"🔍 INSPECTION: {message_body}",
                'priority': 2,
                'due_date': due_date,
                'list_id': project_match[0] if project_match[0] else None,
                'description': f"Inspection scheduled\nFrom: {from_number}\n{message_body}"
            }
        
        # Try OpenAI parsing for complex messages
        elif OPENAI_API_KEY and len(message_body) > 20:
            ai_result = parse_with_openai(message_body)
            if ai_result:
                print(f"OpenAI parsed: {ai_result}")
                
                if ai_result.get('type') == 'create_task':
                    # Build task from AI parsing
                    task_info = {
                        'type': 'create_task',
                        'name': ai_result.get('name', message_body),
                        'display_name': ai_result.get('name', message_body),
                        'priority': ai_result.get('priority', 3),
                        'assignee': ai_result.get('assignee'),
                        'due_date': ai_result.get('due_date'),
                        'description': f"📱 SMS: {message_body}\nFrom: {from_number}"
                    }
                    
                    # Add assignee to display name
                    if task_info['assignee']:
                        task_info['display_name'] = f"[{task_info['assignee']}] {task_info['name']}"
                    
                    # Get project
                    if ai_result.get('project'):
                        for key, proj in SETTINGS['projects'].items():
                            if key == ai_result['project']:
                                task_info['list_id'] = proj['list_id']
                                break
                else:
                    # Fall back to simple parsing
                    task_info = parse_command_simple(message_body)
            else:
                # Fall back to simple parsing
                task_info = parse_command_simple(message_body)
        else:
            # Use simple parsing
            task_info = parse_command_simple(message_body)
        
        # Now handle the parsed result
        if task_info.get('type') == 'create_project':
            if CLICKUP_KEY and WORKSPACE_ID:
                project_result = create_project_in_clickup_with_timeout(
                    task_info['project_name'],
                    timeout=8
                )
                
                if project_result['success']:
                    msg = f"✅ Created project: {project_result['name']}\nUse '{project_result['simple_name']}:' for tasks"
                else:
                    msg = "❌ Couldn't create. Try web."
            else:
                msg = "ClickUp not configured"
        
        elif task_info.get('type') == 'create_task':
            # Actually create the task in ClickUp!
            if CLICKUP_KEY and WORKSPACE_ID:
                if image_data:
                    # Create task with image attachment
                    created = create_clickup_task_with_attachment(task_info, image_data)
                    if created['success']:
                        if created.get('attachment'):
                            msg = f"✅ Created with photo: {task_info.get('display_name', 'Task')[:40]}"
                        else:
                            msg = f"✅ Created: {task_info.get('display_name', 'Task')[:40]}"
                    else:
                        msg = "❌ Failed to create task"
                else:
                    # Regular task creation
                    created = create_clickup_task(task_info)
                    if created['success']:
                        msg = f"✅ Created: {task_info.get('display_name', 'Task')[:40]}"
                    else:
                        msg = "❌ Failed to create task"
            else:
                msg = "ClickUp not configured"
        
        else:
            msg = "Text 'help' for commands"
    
    except Exception as e:
        print(f"SMS error: {e}")
        msg = "Error. Text 'help'"
    
    resp.message(msg)
    return str(resp), 200, {'Content-Type': 'text/xml'}
