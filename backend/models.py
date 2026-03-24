"""Database models for AdaptiveQuiz."""
from datetime import datetime, date

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    preferred_difficulty = db.Column(db.String(20), default="medium")
    streak = db.Column(db.Integer, default=0)
    last_quiz_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text)
    correct_answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.String(20), default="medium")
    q_type = db.Column(db.String(20), default="mcq")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    topic = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    score = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    topic = db.Column(db.String(200))
    difficulty = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class TopicMastery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    topic = db.Column(db.String(200))
    correct_count = db.Column(db.Integer, default=0)
    total_count = db.Column(db.Integer, default=0)

    @property
    def percentage(self):
        if self.total_count == 0:
            return 0
        return int(self.correct_count / self.total_count * 100)


class MistakeBank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    question_text = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text)
    topic = db.Column(db.String(200))
    explanation = db.Column(db.Text)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
