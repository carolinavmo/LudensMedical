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
    """Generate a certificate for a completed course with personalized user name."""
    # Create a new white image with higher resolution
    width, height = 1200, 900
    certificate = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(certificate)
    
    # Add decorative background
    # Draw a light blue background pattern with gradient
    for y in range(0, height, 5):
        color_value = int(240 + (y / height) * 15)  # Subtle gradient
        draw.line([(0, y), (width, y)], fill=(color_value, color_value, 255), width=1)
    
    # Draw border with rounded corners effect
    border_width = 10
    for i in range(border_width):
        offset = i
        draw.rectangle(
            [(20 + offset, 20 + offset), (width - 20 - offset, height - 20 - offset)], 
            outline=(0, 102 - i*5, 204 - i*10), 
            width=1
        )
    
    # Draw decorative corners
    corner_size = 40
    for x, y in [(20, 20), (width-20-corner_size, 20), (20, height-20-corner_size), (width-20-corner_size, height-20-corner_size)]:
        draw.rectangle([(x, y), (x+corner_size, y+corner_size)], fill=(0, 82, 184), outline=None)
    
    # Use default font since custom fonts might not be available
    header_font = ImageFont.load_default()
    body_font = ImageFont.load_default()
    
    # Add header with larger size
    header = "CERTIFICATE OF COMPLETION"
    draw.text((width/2, 120), header, fill=(0, 51, 102), anchor="mm", font=header_font)
    
    # Add Ludens Medical Academy text
    academy_text = "Ludens Medical Academy"
    draw.text((width/2, 190), academy_text, fill=(0, 102, 204), anchor="mm", font=header_font)
    
    # Add decorative line
    draw.line([(width/4, 240), (width*3/4, 240)], fill=(0, 102, 204), width=3)
    
    # Add "This certifies that" text
    cert_intro_text = "This certifies that"
    draw.text((width/2, 300), cert_intro_text, fill=(0, 0, 0), anchor="mm", font=body_font)
    
    # Add recipient name with emphasis
    full_name = user.get_full_name()
    # Make the name stand out by drawing it larger and with a different color
    draw.text((width/2, 360), full_name, fill=(0, 51, 102), anchor="mm", font=header_font)
    
    # Add completion text
    completion_text = "has successfully completed the course"
    draw.text((width/2, 430), completion_text, fill=(0, 0, 0), anchor="mm", font=body_font)
    
    # Add course name with emphasis
    course_text = f'"{course.title}"'
    draw.text((width/2, 500), course_text, fill=(0, 51, 102), anchor="mm", font=header_font)
    
    # Add course category and level
    category = course.category.replace('_', ' ').title()
    level = course.level.title()
    course_details = f"Category: {category} | Level: {level}"
    draw.text((width/2, 550), course_details, fill=(80, 80, 80), anchor="mm", font=body_font)
    
    # Add date with nice formatting
    issue_date = datetime.now().strftime('%B %d, %Y')
    date_text = f"Issued on {issue_date}"
    draw.text((width/2, 620), date_text, fill=(0, 0, 0), anchor="mm", font=body_font)
    
    # Add certificate ID
    cert_id_text = f"Certificate ID: {certificate_id}"
    draw.text((width/2, 680), cert_id_text, fill=(102, 102, 102), anchor="mm", font=body_font)
    
    # Add verification text
    verification_text = "This certificate can be verified on the Ludens Medical Academy website"
    draw.text((width/2, 740), verification_text, fill=(120, 120, 120), anchor="mm", font=body_font)
    
    # Add signature line
    draw.line([(width/2 - 200, 800), (width/2 + 200, 800)], fill=(0, 0, 0), width=1)
    signature_text = "Authorized Signature"
    draw.text((width/2, 830), signature_text, fill=(0, 0, 0), anchor="mm", font=body_font)
    
    # Add a decorative seal/badge
    seal_size = 100
    seal_x = width - 150
    seal_y = height - 150
    
    # Draw a circular seal
    for i in range(3):
        radius = seal_size//2 - i*5
        draw.ellipse(
            [(seal_x - radius, seal_y - radius), (seal_x + radius, seal_y + radius)],
            outline=(0, 51, 102),
            width=2
        )
    
    # Add text to the seal
    draw.text((seal_x, seal_y), "LMA", fill=(0, 51, 102), anchor="mm", font=body_font)
    
    # Save to BytesIO
    img_io = io.BytesIO()
    certificate.save(img_io, 'PNG', quality=95)
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
