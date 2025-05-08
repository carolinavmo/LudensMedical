from datetime import datetime
from flask_login import UserMixin

# In-memory databases
user_db = {}
course_db = {}
module_db = {}
quiz_db = {}
question_db = {}
enrollment_db = {}
certificate_db = {}

class User(UserMixin):
    def __init__(self, id, username, email, password_hash, role='student', first_name='', last_name='', bio='', profile_picture=None, created_at=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role  # 'student' or 'admin'
        self.first_name = first_name
        self.last_name = last_name
        self.bio = bio
        self.profile_picture = profile_picture
        self.created_at = created_at or datetime.now()
    
    def get_id(self):
        return str(self.id)
    
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

class Course:
    def __init__(self, id, title, description, category, level, price, instructor_id, image_url=None, created_at=None, updated_at=None):
        self.id = id
        self.title = title
        self.description = description
        self.category = category  # e.g., 'Cardiology', 'Neurology', 'General Practice'
        self.level = level  # e.g., 'Beginner', 'Intermediate', 'Advanced'
        self.price = price
        self.instructor_id = instructor_id
        self.image_url = image_url
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or self.created_at
    
    def get_instructor(self):
        return user_db.get(self.instructor_id)
    
    def get_modules(self):
        return [module for module in module_db.values() if module.course_id == self.id]
    
    def get_enrollments(self):
        return [enrollment for enrollment in enrollment_db.values() if enrollment.course_id == self.id]
    
    def get_enrollment_count(self):
        return len(self.get_enrollments())
    
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

class Module:
    def __init__(self, id, course_id, title, content, order, video_url=None, pdf_url=None, created_at=None, updated_at=None):
        self.id = id
        self.course_id = course_id
        self.title = title
        self.content = content
        self.order = order
        self.video_url = video_url
        self.pdf_url = pdf_url
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or self.created_at
    
    def get_course(self):
        return course_db.get(self.course_id)
    
    def get_quiz(self):
        return next((quiz for quiz in quiz_db.values() if quiz.module_id == self.id), None)

    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'content': self.content,
            'order': self.order,
            'video_url': self.video_url,
            'pdf_url': self.pdf_url,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class Quiz:
    def __init__(self, id, module_id, title, description, passing_score, created_at=None, updated_at=None):
        self.id = id
        self.module_id = module_id
        self.title = title
        self.description = description
        self.passing_score = passing_score  # Percentage required to pass
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or self.created_at
    
    def get_module(self):
        return module_db.get(self.module_id)
    
    def get_questions(self):
        return [question for question in question_db.values() if question.quiz_id == self.id]
    
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

class QuizQuestion:
    def __init__(self, id, quiz_id, question, options, correct_answer, order, created_at=None):
        self.id = id
        self.quiz_id = quiz_id
        self.question = question
        self.options = options  # List of possible answers
        self.correct_answer = correct_answer
        self.order = order
        self.created_at = created_at or datetime.now()
    
    def get_quiz(self):
        return quiz_db.get(self.quiz_id)
    
    def to_dict(self):
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'question': self.question,
            'options': self.options,
            'correct_answer': self.correct_answer,
            'order': self.order,
            'created_at': self.created_at
        }

class Enrollment:
    def __init__(self, id, user_id, course_id, progress=0, completed=False, created_at=None, updated_at=None):
        self.id = id
        self.user_id = user_id
        self.course_id = course_id
        self.progress = progress  # Percentage of course completed
        self.completed = completed
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or self.created_at
    
    def get_user(self):
        return user_db.get(self.user_id)
    
    def get_course(self):
        return course_db.get(self.course_id)
    
    def get_certificate(self):
        return next((cert for cert in certificate_db.values() 
                    if cert.user_id == self.user_id and cert.course_id == self.course_id), None)
    
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

class Certificate:
    def __init__(self, id, user_id, course_id, issue_date=None):
        self.id = id
        self.user_id = user_id
        self.course_id = course_id
        self.issue_date = issue_date or datetime.now()
    
    def get_user(self):
        return user_db.get(self.user_id)
    
    def get_course(self):
        return course_db.get(self.course_id)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'issue_date': self.issue_date
        }
