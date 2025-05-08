import os
import logging
from datetime import datetime, timedelta
from flask import Flask
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Initialize the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Import routes after app is created to avoid circular imports
from models import User, Course, Module, Quiz, QuizQuestion, Enrollment, Certificate, user_db, course_db, module_db, quiz_db, question_db, enrollment_db, certificate_db
import routes  # noqa: F401

@login_manager.user_loader
def load_user(user_id):
    return user_db.get(int(user_id))

# Create some initial data if needed
with app.app_context():
    # Create admin user if it doesn't exist
    if not any(user.email == 'admin@ludens.medical' for user in user_db.values()):
        from werkzeug.security import generate_password_hash
        admin = User(
            id=len(user_db) + 1,
            username='admin',
            email='admin@ludens.medical',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            first_name='Admin',
            last_name='User',
            created_at=datetime.now()
        )
        user_db[admin.id] = admin
        logging.info(f"Created admin user: {admin.email}")
    
    # Create a student user for testing
    if not any(user.email == 'student@ludens.medical' for user in user_db.values()):
        from werkzeug.security import generate_password_hash
        student = User(
            id=len(user_db) + 1,
            username='student',
            email='student@ludens.medical',
            password_hash=generate_password_hash('student123'),
            role='student',
            first_name='Student',
            last_name='User',
            created_at=datetime.now()
        )
        user_db[student.id] = student
        logging.info(f"Created student user: {student.email}")
