# Add these modifications to your app.py file

# 1. ADD THESE IMPORTS AT THE TOP (after existing imports):
from database import (
    init_db, migrate_from_json, get_db,
    Project, TeamMember, Task, TimeEntry, SMSLog,
    save_task_to_db, get_daily_summary, get_weekly_summary,
    log_sms, mark_task_complete_in_db
)

# 2. REPLACE THE load_settings() FUNCTION:
def load_settings():
    """Load settings from database or create defaults"""
    db = get_db()
    settings = {
        'team_members': {},
        'job_types': {},
        'projects': {}
    }
    
    try:
        # Load team members from database
        members = db.query(TeamMember).filter_by(active=True).all()
        for member in members:
            settings['team_members'][member.key] = member.to_dict()
        
        # Load projects from database
        projects = db.query(Project).filter_by(active=True).all()
        for project in projects:
            settings['projects'][project.simple_key] = project.to_dict()
        
        # If no data in database, try loading from JSON file
        if not members and not projects:
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    json_settings = json.load(f)
                    # Migrate JSON to database
                    migrate_from_json(json_settings)
                    return json_settings
            except:
                # Return defaults
                settings = {
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
                    'projects': {}
                }
                # Save defaults to database
                migrate_from_json(settings)
        
        # Job types still from settings (not in DB yet)
        settings['job_types'] = {
            'plumbing': {'name': 'Plumbing', 'keywords': ['plumb', 'pipe', 'water', 'leak', 'faucet', 'valve']},
            'electrical': {'name': 'Electrical', 'keywords': ['electric', 'wire', 'power', 'outlet', 'breaker', 'panel']},
            'grading': {'name': 'Grading', 'keywords': ['grade', 'level', 'excavat', 'dirt', 'soil', 'slope']},
            'concrete': {'name': 'Concrete', 'keywords': ['concrete', 'pour', 'slab', 'foundation', 'cement']},
            'framing': {'name': 'Framing', 'keywords': ['frame', 'wall', 'roof', 'truss', 'stud']},
            'safety': {'name': 'Safety', 'keywords': ['safety', 'danger', 'hazard', 'violation', 'osha']},
            'inspection': {'name': 'Inspection', 'keywords': ['inspect', 'review', 'check', 'permit']}
        }
    except Exception as e:
        print(f"Error loading from database: {e}")
    finally:
        db.close()
    
    return settings

# 3. REPLACE THE save_settings() FUNCTION:
def save_settings(settings):
    """Save settings to database"""
    db = get_db()
    try:
        # Save team members
        for key, member_data in settings.get('team_members', {}).items():
            member = db.query(TeamMember).filter_by(key=key).first()
            if not member:
                member = TeamMember(key=key)
            member.name = member_data['name']
            member.role = member_data.get('role', 'General')
            member.active = True
            db.add(member)
        
        # Save projects
        for key, project_data in settings.get('projects', {}).items():
            project = db.query(Project).filter_by(simple_key=key).first()
            if not project:
                project = Project(
                    simple_key=key,
                    clickup_list_id=project_data['list_id']
                )
            project.name = project_data['name']
            project.space = project_data.get('space', '')
            project.active = True
            project.synced_at = datetime.now()
            db.add(project)
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error saving to database: {e}")
        db.rollback()
        return False
    finally:
        db.close()

# 4. ADD TO sync_clickup_lists_on_startup() FUNCTION (at the end, before save_settings):
        # Save to database
        db = get_db()
        try:
            for simple_key, project_data in SETTINGS['projects'].items():
                project = db.query(Project).filter_by(simple_key=simple_key).first()
                if not project:
                    project = Project(
                        clickup_list_id=project_data['list_id'],
                        name=project_data['name'],
                        simple_key=simple_key,
                        space=project_data.get('space', ''),
                        synced_at=datetime.now()
                    )
                    db.add(project)
                else:
                    project.synced_at = datetime.now()
            db.commit()
        except Exception as e:
            print(f"Error syncing to database: {e}")
            db.rollback()
        finally:
            db.close()

# 5. ADD AFTER create_clickup_task() function succeeds:
        # Save to database
        if created_task['success']:
            save_task_to_db(
                task_info, 
                created_task['task']['id'],
                created_via='web',
                phone=None
            )

# 6. ADD AFTER create_clickup_task_with_attachment() succeeds:
        # Save to database
        if task_response.status_code == 200:
            task_info['has_photo'] = image_data is not None
            save_task_to_db(
                task_info,
                task_id,
                created_via='sms',
                phone=task_info.get('from_number')
            )

# 7. ADD NEW SMS COMMANDS IN handle_sms() function (after the "help" command):

        # Daily report command
        if lower == "report" or lower == "daily":
            summary = get_daily_summary()
            if summary:
                msg = f"📊 Today: {summary['completed_count']} done, {summary['created_count']} new\n"
                if summary['overdue_count'] > 0:
                    msg += f"⚠️ {summary['overdue_count']} overdue\n"
                if summary['tomorrow_count'] > 0:
                    msg += f"📅 {summary['tomorrow_count']} due tomorrow"
                
                # Log the SMS
                log_sms(from_number, message_body, msg, command_type='report')
            else:
                msg = "No report data available"
            
            resp.message(msg)
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        # Weekly report command
        if lower == "weekly":
            summary = get_weekly_summary()
            if summary:
                msg = f"📊 Week: {summary['total_completed']}/{summary['total_created']} tasks\n"
                msg += f"Rate: {summary['completion_rate']}\n"
                if summary['top_performers']:
                    top = summary['top_performers'][0]
                    msg += f"⭐ MVP: {top[0]} ({top[1]} tasks)"
                
                # Log the SMS
                log_sms(from_number, message_body, msg, command_type='weekly')
            else:
                msg = "No weekly data"
            
            resp.message(msg)
            return str(resp), 200, {'Content-Type': 'text/xml'}
        
        # Tomorrow's tasks
        if lower == "tomorrow":
            tomorrow = datetime.now().date() + timedelta(days=1)
            summary = get_daily_summary(tomorrow)
            if summary and summary['tomorrow_tasks']:
                msg = f"📅 Tomorrow ({tomorrow.strftime('%m/%d')}):\n"
                for task in summary['tomorrow_tasks'][:5]:
                    msg += f"• {task['name'][:25]}\n"
                    if len(msg) > 140:
                        msg += "...more"
                        break
            else:
                msg = "No tasks scheduled for tomorrow"
            
            resp.message(msg)
            return str(resp), 200, {'Content-Type': 'text/xml'}

# 8. UPDATE THE help command to include new features:
        if lower == "help":
            msg = "Commands:\n"
            msg += "📊 report - today\n"
            msg += "📊 weekly - week stats\n"
            msg += "📅 tomorrow - tasks\n"
            msg += "📋 status - projects\n"
            msg += "📝 list [project]\n"
            msg += "✅ done [task#]\n"
            msg += "🏗️ create project\n"
            msg += "📸 Send photo"
            resp.message(msg)
            return str(resp), 200, {'Content-Type': 'text/xml'}

# 9. ADD NEW API ENDPOINTS (before if __name__ == '__main__'):

@app.route('/api/report/daily', methods=['GET'])
def api_daily_report():
    """Get daily report via API"""
    date_str = request.args.get('date')
    date = None
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            pass
    
    summary = get_daily_summary(date)
    return jsonify(summary if summary else {'error': 'No data'})

@app.route('/api/report/weekly', methods=['GET'])
def api_weekly_report():
    """Get weekly report via API"""
    summary = get_weekly_summary()
    return jsonify(summary if summary else {'error': 'No data'})

@app.route('/api/send-daily-reports', methods=['POST'])
def send_daily_reports():
    """Send daily reports to managers (can be triggered by cron job)"""
    if not TWILIO_ACCOUNT_SID:
        return jsonify({'error': 'SMS not configured'}), 400
    
    # Get manager numbers from request or environment
    manager_numbers = request.json.get('numbers', [])
    if not manager_numbers:
        # Get from environment variable
        manager_numbers = os.getenv('MANAGER_PHONES', '').split(',')
    
    if not manager_numbers:
        return jsonify({'error': 'No manager numbers configured'}), 400
    
    summary = get_daily_summary()
    if not summary:
        return jsonify({'error': 'No data available'}), 400
    
    # Format message
    msg = f"📊 Daily Report - {datetime.now().strftime('%m/%d')}\n"
    msg += f"✅ Completed: {summary['completed_count']}\n"
    msg += f"📝 Created: {summary['created_count']}\n"
    if summary['overdue_count'] > 0:
        msg += f"⚠️ Overdue: {summary['overdue_count']}\n"
    msg += f"📅 Tomorrow: {summary['tomorrow_count']}"
    
    # Send to each manager
    from twilio.rest import Client
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    sent = 0
    for number in manager_numbers:
        number = number.strip()
        if number:
            try:
                client.messages.create(
                    body=msg,
                    from_=TWILIO_PHONE_NUMBER,
                    to=number
                )
                sent += 1
            except Exception as e:
                print(f"Error sending to {number}: {e}")
    
    return jsonify({'sent': sent, 'message': msg})

# 10. INITIALIZE DATABASE ON STARTUP (add after sync_clickup_lists_on_startup()):
# Initialize database
init_db()

# Migrate existing JSON data if present
if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, 'r') as f:
            json_settings = json.load(f)
            migrate_from_json(json_settings)
            print("✅ Migrated existing settings to database")
    except Exception as e:
        print(f"Could not migrate JSON: {e}")

print("✅ Database initialized")
