from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
from app import db

# Keep in-memory databases for compatibility during migration
user_db = {}
course_db = {}
module_db = {}
quiz_db = {}
question_db = {}
enrollment_db = {}
certificate_db = {}

def refresh_quizzes():
    """Refresh only the quiz-related data in the in-memory dictionaries."""
    # Clear quiz data
    quiz_db.clear()
    question_db.clear()
    
    try:
        # Quizzes
        quizzes = Quiz.query.all()
        for quiz in quizzes:
            quiz_db[quiz.id] = quiz
        
        # Questions
        questions = QuizQuestion.query.all()
        for question in questions:
            question_db[question.id] = question
            
        print(f"Refreshed quiz data: {len(quiz_db)} quizzes, {len(question_db)} questions")
        return True
    except Exception as e:
        print(f"Error refreshing quiz data: {str(e)}")
        return False

def populate_in_memory_db():
    """Populate in-memory dictionaries from the database."""
    # Clear current data
    user_db.clear()
    course_db.clear()
    module_db.clear()
    quiz_db.clear()
    question_db.clear()
    enrollment_db.clear()
    certificate_db.clear()
    
    # Populate from database
    try:
        # Users
        users = User.query.all()
        for user in users:
            user_db[user.id] = user
        
        # Courses
        courses = Course.query.all()
        for course in courses:
            course_db[course.id] = course
        
        # Modules
        modules = Module.query.all()
        for module in modules:
            module_db[module.id] = module
        
        # Quizzes
        quizzes = Quiz.query.all()
        for quiz in quizzes:
            quiz_db[quiz.id] = quiz
        
        # Questions
        questions = QuizQuestion.query.all()
        for question in questions:
            question_db[question.id] = question
        
        # Enrollments
        enrollments = Enrollment.query.all()
        for enrollment in enrollments:
            enrollment_db[enrollment.id] = enrollment
        
        # Certificates
        certificates = Certificate.query.all()
        for certificate in certificates:
            certificate_db[certificate.id] = certificate
        
        print(f"Populated in-memory DB with: {len(user_db)} users, {len(course_db)} courses, {len(module_db)} modules")
    except Exception as e:
        print(f"Error populating in-memory database: {str(e)}")

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='student', nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    courses = db.relationship('Course', backref='instructor', lazy='dynamic')
    enrollments = db.relationship('Enrollment', backref='user', lazy='dynamic')
    certificates = db.relationship('Certificate', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}" if self.first_name and self.last_name else self.username
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'bio': self.bio,
            'created_at': self.created_at
        }


class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    modules = db.relationship('Module', backref='course', lazy='dynamic')
    enrollments = db.relationship('Enrollment', backref='course', lazy='dynamic')
    certificates = db.relationship('Certificate', backref='course', lazy='dynamic')
    
    def get_modules(self):
        return self.modules.order_by(Module.order).all()
    
    def get_enrollment_count(self):
        return self.enrollments.count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'level': self.level,
            'price': self.price,
            'instructor_id': self.instructor_id,
            'image_url': self.image_url,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class Module(db.Model):
    __tablename__ = 'modules'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    video_url = db.Column(db.String(255))
    pdf_url = db.Column(db.String(255))
    video_file = db.Column(db.String(255))
    pdf_file = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    quiz = db.relationship('Quiz', backref='module', uselist=False)
    
    def get_quiz(self):
        return self.quiz
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'content': self.content,
            'order': self.order,
            'video_url': self.video_url,
            'pdf_url': self.pdf_url,
            'video_file': self.video_file,
            'pdf_file': self.pdf_file,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class Quiz(db.Model):
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    passing_score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    questions = db.relationship('QuizQuestion', backref='quiz', lazy='dynamic')
    
    def get_questions(self):
        return self.questions.order_by(QuizQuestion.order).all()
    
    def to_dict(self):
        return {
            'id': self.id,
            'module_id': self.module_id,
            'title': self.title,
            'description': self.description,
            'passing_score': self.passing_score,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class QuizQuestion(db.Model):
    __tablename__ = 'quiz_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    question = db.Column(db.String(255), nullable=False)
    options = db.Column(db.Text, nullable=False)  # JSON string of options
    correct_answer = db.Column(db.Integer, nullable=False)
    order = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def get_options(self):
        try:
            return json.loads(self.options)
        except (json.JSONDecodeError, TypeError):
            # Return a default list if JSON decoding fails
            return ["Option 1", "Option 2", "Option 3", "Option 4"]
    
    def set_options(self, options_list):
        if isinstance(options_list, list):
            self.options = json.dumps(options_list)
        else:
            # Handle case where options_list is not a list
            self.options = json.dumps(["Option 1", "Option 2", "Option 3", "Option 4"])
    
    def to_dict(self):
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question': self.question,
            'options': self.get_options(),
            'correct_answer': self.correct_answer,
            'order': self.order,
            'created_at': self.created_at
        }


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    progress = db.Column(db.Integer, default=0, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def get_certificate(self):
        return Certificate.query.filter_by(user_id=self.user_id, course_id=self.course_id).first()
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'progress': self.progress,
            'completed': self.completed,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class Certificate(db.Model):
    __tablename__ = 'certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    issue_date = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'issue_date': self.issue_date
        }
