from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import backref
from flask import url_for

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(512))
    about_me = db.Column(db.String(500))
    skills = db.Column(db.String(500))
    avatar = db.Column(db.String(120))

    created_projects = db.relationship('Project', backref='creator', lazy='dynamic')
    tasks = db.relationship('Task', backref='assignee', lazy='dynamic')
    applications = db.relationship('Application', backref='applicant', lazy='dynamic')
    invitations = db.relationship('Invitation', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills_required = db.Column(db.String(500))
    deadline = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    tasks = db.relationship('Task', backref='project', lazy='dynamic')
    participants = db.relationship('ProjectParticipant', backref='project', lazy='dynamic')
    applications = db.relationship('Application', backref='project', lazy='dynamic')
    messages = db.relationship('Message', backref='project', lazy='dynamic')


class ProjectParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='project_participations')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='not_started')  # not_started, in_progress, completed
    deadline = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    parent_task_id = db.Column(db.Integer, db.ForeignKey('task.id'))
    completed = db.Column(db.Boolean, default=False)
    hidden = db.Column(db.Boolean, default=False)

    subtasks = db.relationship('SubTask', backref='task')

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

class Invitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    status = db.Column(db.String(20), default='pending')
    invited_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='invitations')
    project = db.relationship('Project', backref=backref('invitations', lazy='dynamic'))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

    user = db.relationship('User', backref='messages')

class SubTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)

    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@property
def avatar_url(self):
    if self.avatar:
        return url_for('static', filename=f'uploads/avatars/{self.avatar}')
    return None