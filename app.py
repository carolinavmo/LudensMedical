import os
import logging
from datetime import datetime, timedelta
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Create the SQLAlchemy base class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Initialize the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
csrf = CSRFProtect(app)

# Initialize Flask extensions
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Import models after db is created to avoid circular imports
from models import User, Course, Module, Quiz, QuizQuestion, Enrollment, Certificate
from models import user_db, course_db, module_db, quiz_db, question_db, enrollment_db, certificate_db

# Import routes after app is created to avoid circular imports
import routes  # noqa: F401

@login_manager.user_loader
def load_user(user_id):
    # Try to get user from the SQLAlchemy database first
    try:
        user = User.query.get(int(user_id))
        if user:
            return user
    except:
        # Fall back to in-memory database during migration
        return user_db.get(int(user_id))
    return None

# Create database tables and initial data
with app.app_context():
    # Create all database tables
    db.create_all()
    
    # Create admin user if it doesn't exist
    if not User.query.filter_by(email='admin@ludens.medical').first():
        from werkzeug.security import generate_password_hash
        admin = User(
            username='admin',
            email='admin@ludens.medical',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            first_name='Admin',
            last_name='User'
        )
        db.session.add(admin)
        db.session.commit()
        logging.info(f"Created admin user: admin@ludens.medical")

    # Create a student user for testing
    if not User.query.filter_by(email='student@ludens.medical').first():
        from werkzeug.security import generate_password_hash
        student = User(
            username='student',
            email='student@ludens.medical',
            password_hash=generate_password_hash('student123'),
            role='student',
            first_name='Student',
            last_name='User'
        )
        db.session.add(student)
        db.session.commit()
        logging.info(f"Created student user: student@ludens.medical")
    
    # Seed initial data
    from utils import seed_data
    seed_data(user_db, course_db, module_db)
    logging.info("Seeded initial data")