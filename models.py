from main import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# User model for authentication
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    is_superuser = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'

# Spatial Feature model for geospatial data
class SpatialFeature(db.Model):
    __tablename__ = 'spatial_features'
    
    id = db.Column(db.Integer, primary_key=True)
    feature_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    feature_type = db.Column(db.String(64), nullable=False)
    properties = db.Column(db.JSON, nullable=True)
    # Note: Using simplified representation since PostGIS might not be available
    geometry_json = db.Column(db.JSON, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SpatialFeature {self.feature_id}>'

# Project model for organizing work
class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Project {self.name}>'

# Audit Log model for tracking changes
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    resource_type = db.Column(db.String(64), nullable=False)
    resource_id = db.Column(db.String(64), nullable=False)
    details = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.resource_type}:{self.resource_id}>'

# Data Correction model for managing corrections
class DataCorrection(db.Model):
    __tablename__ = 'data_corrections'
    
    id = db.Column(db.Integer, primary_key=True)
    feature_id = db.Column(db.String(64), db.ForeignKey('spatial_features.feature_id'), nullable=False)
    correction_type = db.Column(db.String(64), nullable=False)  # 'geometry', 'attribute', etc.
    original_value = db.Column(db.JSON, nullable=True)
    corrected_value = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(32), default='pending')  # 'pending', 'approved', 'rejected'
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<DataCorrection {self.id} for {self.feature_id}>'