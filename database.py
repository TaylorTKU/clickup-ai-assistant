# database.py - Database setup and models for ClickUp Construction Assistant
# Add this as a new file in your project

import os
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import NullPool

# Database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///construction.db')

# Fix for Render's postgres:// vs postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Good for serverless
    echo=False  # Set to True for debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(SessionLocal)

# Base class for models
Base = declarative_base()

# Models
class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    clickup_list_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    simple_key = Column(String(50), unique=True, nullable=False)
    space = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    synced_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)
    
    # Relationships
    tasks = relationship("Task", back_populates="project")
    
    def to_dict(self):
        return {
            'list_id': self.clickup_list_id,
            'name': self.name,
            'space': self.space,
            'created': self.created_at.isoformat() if self.created_at else None,
            'synced': self.synced_at.isoformat() if self.synced_at else None
        }

class TeamMember(Base):
    __tablename__ = 'team_members'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(100))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)
    
    # Relationships
    tasks = relationship("Task", back_populates="assignee")
    time_entries = relationship("TimeEntry", back_populates="member")
    
    def to_dict(self):
        return {
            'name': self.name,
            'role': self.role,
            'phone': self.phone
        }

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    clickup_task_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    priority = Column(Integer, default=3)
    status = Column(String(50), default='to do')
    due_date = Column(DateTime)
    
    # Foreign keys
    project_id = Column(Integer, ForeignKey('projects.id'))
    assignee_id = Column(Integer, ForeignKey('team_members.id'))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    created_via = Column(String(50))  # 'sms', 'web', 'api'
    created_by_phone = Column(String(20))
    has_photo = Column(Boolean, default=False)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("TeamMember", back_populates="tasks")
    comments = relationship("TaskComment", back_populates="task")

class TaskComment(Base):
    __tablename__ = 'task_comments'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))
    
    # Relationships
    task = relationship("Task", back_populates="comments")

class TimeEntry(Base):
    __tablename__ = 'time_entries'
    
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('team_members.id'))
    project_id = Column(Integer, ForeignKey('projects.id'))
    clock_in = Column(DateTime, nullable=False)
    clock_out = Column(DateTime)
    break_minutes = Column(Integer, default=0)
    total_hours = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    member = relationship("TeamMember", back_populates="time_entries")
    project = relationship("Project")

class SMSLog(Base):
    __tablename__ = 'sms_logs'
    
    id = Column(Integer, primary_key=True)
    from_number = Column(String(20), nullable=False)
    to_number = Column(String(20))
    message = Column(Text)
    response = Column(Text)
    has_media = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    command_type = Column(String(50))  # 'task', 'status', 'report', etc.

class DailyReport(Base):
    __tablename__ = 'daily_reports'
    
    id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, nullable=False)
    tasks_completed = Column(Integer, default=0)
    tasks_created = Column(Integer, default=0)
    total_hours = Column(Float, default=0)
    active_projects = Column(Integer, default=0)
    report_data = Column(Text)  # JSON string with detailed data
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_to = Column(Text)  # JSON list of phone numbers

# Create all tables
Base.metadata.create_all(bind=engine)

# Database helper functions
def get_db():
    """Get database session"""
    return Session()

def init_db():
    """Initialize database with tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized")

def migrate_from_json(settings_dict):
    """Migrate existing JSON settings to database"""
    db = get_db()
    try:
        # Migrate projects
        for key, proj in settings_dict.get('projects', {}).items():
            existing = db.query(Project).filter_by(simple_key=key).first()
            if not existing:
                project = Project(
                    clickup_list_id=proj['list_id'],
                    name=proj['name'],
                    simple_key=key,
                    space=proj.get('space', ''),
                    created_at=datetime.fromisoformat(proj['created']) if 'created' in proj else datetime.utcnow(),
                    synced_at=datetime.fromisoformat(proj['synced']) if 'synced' in proj else datetime.utcnow()
                )
                db.add(project)
        
        # Migrate team members
        for key, member in settings_dict.get('team_members', {}).items():
            existing = db.query(TeamMember).filter_by(key=key).first()
            if not existing:
                team_member = TeamMember(
                    key=key,
                    name=member['name'],
                    role=member.get('role', 'General')
                )
                db.add(team_member)
        
        db.commit()
        print("✅ Migrated settings to database")
    except Exception as e:
        print(f"❌ Migration error: {e}")
        db.rollback()
    finally:
        db.close()

def save_task_to_db(task_info, clickup_task_id, created_via='web', phone=None):
    """Save a created task to database"""
    db = get_db()
    try:
        # Find project
        project = None
        if task_info.get('list_id'):
            project = db.query(Project).filter_by(
                clickup_list_id=task_info['list_id']
            ).first()
        
        # Find assignee
        assignee = None
        if task_info.get('assignee'):
            assignee = db.query(TeamMember).filter_by(
                name=task_info['assignee']
            ).first()
        
        # Create task record
        task = Task(
            clickup_task_id=clickup_task_id,
            name=task_info.get('display_name', task_info.get('name')),
            description=task_info.get('description', ''),
            priority=task_info.get('priority', 3),
            status='to do',
            due_date=datetime.strptime(task_info['due_date'], '%Y-%m-%d') if task_info.get('due_date') else None,
            project_id=project.id if project else None,
            assignee_id=assignee.id if assignee else None,
            created_via=created_via,
            created_by_phone=phone,
            has_photo=task_info.get('has_photo', False)
        )
        db.add(task)
        db.commit()
        return task.id
    except Exception as e:
        print(f"Error saving task to DB: {e}")
        db.rollback()
    finally:
        db.close()

def get_daily_summary(date=None):
    """Get summary for a specific date"""
    if not date:
        date = datetime.now().date()
    
    db = get_db()
    try:
        start = datetime.combine(date, datetime.min.time())
        end = datetime.combine(date, datetime.max.time())
        
        # Tasks created today
        created = db.query(Task).filter(
            Task.created_at >= start,
            Task.created_at <= end
        ).all()
        
        # Tasks completed today
        completed = db.query(Task).filter(
            Task.completed_at >= start,
            Task.completed_at <= end
        ).all()
        
        # Overdue tasks
        overdue = db.query(Task).filter(
            Task.due_date < datetime.now(),
            Task.status != 'complete'
        ).all()
        
        # Tasks due tomorrow
        tomorrow = date + timedelta(days=1)
        tomorrow_start = datetime.combine(tomorrow, datetime.min.time())
        tomorrow_end = datetime.combine(tomorrow, datetime.max.time())
        due_tomorrow = db.query(Task).filter(
            Task.due_date >= tomorrow_start,
            Task.due_date <= tomorrow_end,
            Task.status != 'complete'
        ).all()
        
        return {
            'date': date.isoformat(),
            'created_count': len(created),
            'created_tasks': [{'name': t.name, 'project': t.project.name if t.project else 'None'} for t in created],
            'completed_count': len(completed),
            'completed_tasks': [{'name': t.name, 'assignee': t.assignee.name if t.assignee else 'None'} for t in completed],
            'overdue_count': len(overdue),
            'overdue_tasks': [{'name': t.name, 'days_overdue': (datetime.now() - t.due_date).days} for t in overdue[:5]],
            'tomorrow_count': len(due_tomorrow),
            'tomorrow_tasks': [{'name': t.name, 'assignee': t.assignee.name if t.assignee else 'TBD'} for t in due_tomorrow]
        }
    except Exception as e:
        print(f"Error getting daily summary: {e}")
        return None
    finally:
        db.close()

def get_weekly_summary(date=None):
    """Get summary for the week"""
    if not date:
        date = datetime.now().date()
    
    # Get start of week (Monday)
    start_of_week = date - timedelta(days=date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    db = get_db()
    try:
        # Tasks this week
        created = db.query(Task).filter(
            Task.created_at >= datetime.combine(start_of_week, datetime.min.time()),
            Task.created_at <= datetime.combine(end_of_week, datetime.max.time())
        ).all()
        
        completed = db.query(Task).filter(
            Task.completed_at >= datetime.combine(start_of_week, datetime.min.time()),
            Task.completed_at <= datetime.combine(end_of_week, datetime.max.time())
        ).all()
        
        # Group by project
        project_stats = {}
        for task in created + completed:
            if task.project:
                if task.project.name not in project_stats:
                    project_stats[task.project.name] = {'created': 0, 'completed': 0}
                if task in created:
                    project_stats[task.project.name]['created'] += 1
                if task in completed:
                    project_stats[task.project.name]['completed'] += 1
        
        # Top performers (most tasks completed)
        performer_stats = {}
        for task in completed:
            if task.assignee:
                if task.assignee.name not in performer_stats:
                    performer_stats[task.assignee.name] = 0
                performer_stats[task.assignee.name] += 1
        
        top_performers = sorted(performer_stats.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'week_start': start_of_week.isoformat(),
            'week_end': end_of_week.isoformat(),
            'total_created': len(created),
            'total_completed': len(completed),
            'completion_rate': f"{(len(completed) / len(created) * 100):.0f}%" if created else "N/A",
            'project_stats': project_stats,
            'top_performers': top_performers
        }
    except Exception as e:
        print(f"Error getting weekly summary: {e}")
        return None
    finally:
        db.close()

def log_sms(from_number, message, response, has_media=False, command_type=None):
    """Log SMS interactions"""
    db = get_db()
    try:
        log = SMSLog(
            from_number=from_number,
            message=message[:500],  # Truncate long messages
            response=response[:500],
            has_media=has_media,
            command_type=command_type
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"Error logging SMS: {e}")
        db.rollback()
    finally:
        db.close()

def mark_task_complete_in_db(clickup_task_id):
    """Mark a task as complete in database"""
    db = get_db()
    try:
        task = db.query(Task).filter_by(clickup_task_id=clickup_task_id).first()
        if task:
            task.status = 'complete'
            task.completed_at = datetime.utcnow()
            db.commit()
            return True
    except Exception as e:
        print(f"Error marking task complete: {e}")
        db.rollback()
    finally:
        db.close()
    return False
