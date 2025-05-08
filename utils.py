import os
import io
import uuid
import random
import string
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from flask import url_for, render_template

def generate_reset_token(length=32):
    """Generate a random token for password reset."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def find_user_by_email(email, user_db):
    """Find a user by email address."""
    for user in user_db.values():
        if user.email.lower() == email.lower():
            return user
    return None

def find_user_by_username(username, user_db):
    """Find a user by username."""
    for user in user_db.values():
        if user.username.lower() == username.lower():
            return user
    return None

def get_user_courses(user_id, enrollment_db, course_db):
    """Get all courses a user is enrolled in."""
    enrollments = [e for e in enrollment_db.values() if e.user_id == user_id]
    courses = [course_db.get(e.course_id) for e in enrollments]
    return [c for c in courses if c is not None]

def get_user_enrollments(user_id, enrollment_db):
    """Get all enrollments for a user."""
    return [e for e in enrollment_db.values() if e.user_id == user_id]

def get_user_certificates(user_id, certificate_db):
    """Get all certificates for a user."""
    return [c for c in certificate_db.values() if c.user_id == user_id]

def get_course_modules(course_id, module_db):
    """Get all modules for a course, ordered by their order field."""
    modules = [m for m in module_db.values() if m.course_id == course_id]
    return sorted(modules, key=lambda m: m.order)

def get_next_id(db):
    """Get the next available ID for a database."""
    return max([0] + list(db.keys())) + 1

def filter_courses(courses, category=None, level=None, search=None):
    """Filter courses by category, level, and search term."""
    filtered = courses
    
    if category:
        filtered = [c for c in filtered if c.category == category]
    
    if level:
        filtered = [c for c in filtered if c.level == level]
    
    if search:
        search = search.lower()
        filtered = [c for c in filtered if search in c.title.lower() or search in c.description.lower()]
    
    return filtered

def calculate_course_progress(user_id, course_id, enrollment_db):
    """Calculate a user's progress in a course."""
    for enrollment in enrollment_db.values():
        if enrollment.user_id == user_id and enrollment.course_id == course_id:
            return enrollment.progress
    return 0

def generate_certificate(user, course, certificate_id):
    """Generate a certificate for a completed course."""
    # Create a new white image
    width, height = 800, 600
    certificate = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(certificate)
    
    # Draw border
    draw.rectangle([(20, 20), (width-20, height-20)], outline=(0, 102, 204), width=5)
    
    # Add header
    header_font = ImageFont.load_default()
    header = "CERTIFICATE OF COMPLETION"
    draw.text((width/2, 80), header, fill=(0, 51, 102), anchor="mm", font=header_font)
    
    # Add Ludens Medical Academy text
    academy_text = "Ludens Medical Academy"
    draw.text((width/2, 130), academy_text, fill=(0, 102, 204), anchor="mm", font=header_font)
    
    # Add recipient name
    name_text = f"This certifies that {user.get_full_name()}"
    draw.text((width/2, 200), name_text, fill=(0, 0, 0), anchor="mm", font=header_font)
    
    # Add course completion text
    completion_text = f"has successfully completed the course"
    draw.text((width/2, 250), completion_text, fill=(0, 0, 0), anchor="mm", font=header_font)
    
    # Add course title
    course_text = f"\"{course.title}\""
    draw.text((width/2, 300), course_text, fill=(0, 51, 102), anchor="mm", font=header_font)
    
    # Add date
    date_text = f"Issued on: {datetime.now().strftime('%B %d, %Y')}"
    draw.text((width/2, 370), date_text, fill=(0, 0, 0), anchor="mm", font=header_font)
    
    # Add certificate ID
    cert_id_text = f"Certificate ID: {certificate_id}"
    draw.text((width/2, 420), cert_id_text, fill=(100, 100, 100), anchor="mm", font=header_font)
    
    # Add signature line
    draw.line([(200, 500), (600, 500)], fill=(0, 0, 0), width=1)
    signature_text = "Authorized Signature"
    draw.text((400, 520), signature_text, fill=(0, 0, 0), anchor="mm", font=header_font)
    
    # Save to BytesIO object and return
    img_io = io.BytesIO()
    certificate.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

def get_stats(user_db, course_db, enrollment_db):
    """Get statistics for the admin dashboard."""
    total_users = len(user_db)
    total_courses = len(course_db)
    total_enrollments = len(enrollment_db)
    
    # Users by role
    students = sum(1 for user in user_db.values() if user.role == 'student')
    admins = total_users - students
    
    # Enrollments by course
    course_enrollments = {}
    for course in course_db.values():
        course_enrollments[course.id] = sum(1 for e in enrollment_db.values() if e.course_id == course.id)
    
    # Most popular courses (top 5)
    popular_courses = sorted(
        [(course_id, count) for course_id, count in course_enrollments.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    return {
        'total_users': total_users,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'students': students,
        'admins': admins,
        'course_enrollments': course_enrollments,
        'popular_courses': popular_courses
    }
