from app import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    goals = db.Column(db.String(500), nullable=True)
    distractions = db.Column(db.String(500), nullable=True)
    occupation = db.Column(db.String(50), nullable=True)
    sessions = db.relationship('Session', backref='user', lazy=True)

    def check_password(self, password):
        return self.password == password  # Direct password comparison

    def __repr__(self):
        return f'<User {self.username}>'
    
class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_type = db.Column(db.String(20), nullable=False)  # 'work' or 'break'
    duration = db.Column(db.Integer, nullable=False)  # Duration in seconds
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Session {self.session_type} by User {self.user_id}>'