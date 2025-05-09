import os
import logging
from datetime import datetime
from io import BytesIO
from flask import render_template, redirect, url_for, flash, request, jsonify, session, abort, send_file, json
from werkzeug.utils import secure_filename
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse
from app import app, db
from models import User, Course, Module, Quiz, QuizQuestion, Enrollment, Certificate
from models import user_db, course_db, module_db, quiz_db, question_db, enrollment_db, certificate_db
from models import populate_in_memory_db
from forms import (LoginForm, SignupForm, ResetPasswordRequestForm, ResetPasswordForm, 
                  CourseForm, ModuleForm, QuizForm, QuestionForm, QuizSubmissionForm,
                  ProfileForm, PasswordChangeForm, UserForm)
from utils import (generate_reset_token, find_user_by_email, find_user_by_username,
                  get_user_courses, get_user_enrollments, get_user_certificates,
                  get_course_modules, get_next_id, filter_courses, calculate_course_progress,
                  generate_certificate, get_stats)

# Public routes
@app.route('/')
def index():
    # Get 3 featured courses for the homepage
    featured_courses = list(course_db.values())[:3] if course_db else []
    return render_template('index.html', featured_courses=featured_courses)

@app.route('/courses')
def courses():
    category = request.args.get('category')
    level = request.args.get('level')
    search = request.args.get('search')
    
    # Log information for debugging
    logging.info(f"Courses route accessed. In-memory course_db has {len(course_db)} courses")
    
    # Force refresh in-memory DB to ensure we have the latest data
    populate_in_memory_db()
    logging.info(f"After refresh: course_db has {len(course_db)} courses")
    
    all_courses = list(course_db.values())
    filtered_courses = filter_courses(all_courses, category, level, search)
    
    logging.info(f"Filtered courses: {len(filtered_courses)}")
    
    # Get categories and levels for filter dropdowns
    categories = sorted(set(c.category for c in all_courses))
    levels = sorted(set(c.level for c in all_courses))
    
    # Use different template based on authentication status
    template = 'student/courses.html' if current_user.is_authenticated else 'courses.html'
    
    return render_template(template, 
                          courses=filtered_courses, 
                          categories=categories, 
                          levels=levels,
                          current_category=category,
                          current_level=level,
                          search=search)

@app.route('/my-courses')
@login_required
def my_courses():
    # Get courses the user is enrolled in
    user_enrollments = get_user_enrollments(current_user.id, enrollment_db)
    courses = [course_db[enrollment.course_id] for enrollment in user_enrollments]
    
    # Calculate progress for each course
    progress = {}
    for course in courses:
        progress[course.id] = calculate_course_progress(current_user.id, course.id, enrollment_db)
    
    return render_template('my_courses.html', courses=courses, progress=progress)

@app.route('/courses/<int:course_id>')
def course_detail(course_id):
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('courses'))
    
    modules = get_course_modules(course_id, module_db)
    instructor = user_db.get(course.instructor_id)
    
    # Check if user is enrolled
    enrolled = False
    progress = 0
    current_enrollment = None
    if current_user.is_authenticated:
        for enrollment in enrollment_db.values():
            if enrollment.user_id == current_user.id and enrollment.course_id == course_id:
                enrolled = True
                progress = enrollment.progress
                current_enrollment = enrollment
                break
    
    # If the user is enrolled and there's progress, find the most appropriate module to continue from
    if enrolled and current_enrollment and progress > 0 and modules:
        # Sort modules by order first to ensure they're in the correct sequence
        modules = sorted(modules, key=lambda m: m.order)
        
        # If progress is less than 100%, find the appropriate module based on progress
        if progress < 100:
            # Calculate which module the user should continue from
            total_modules = len(modules)
            # This gives us the index of the module the user should be at based on their progress
            current_module_index = min(int((progress / 100) * total_modules), total_modules - 1)
            
            # We'll keep the modules in their original order, but we know which one to link to
            # from the "Continue Learning" button
            next_module_id = modules[current_module_index].id
            
            # We'll pass this ID to the template to create the proper link
            template = 'student/course_detail.html' if current_user.is_authenticated else 'course_detail.html'
            return render_template(template, 
                                  course=course, 
                                  modules=modules, 
                                  instructor=instructor,
                                  enrolled=enrolled,
                                  progress=progress,
                                  next_module_id=next_module_id)
    
    template = 'student/course_detail.html' if current_user.is_authenticated else 'course_detail.html'
    return render_template(template, 
                          course=course, 
                          modules=modules, 
                          instructor=instructor,
                          enrolled=enrolled,
                          progress=progress)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # First try to find user in the database
        try:
            user = User.query.filter_by(email=form.email.data).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user, remember=form.remember_me.data)
                logging.info(f"User logged in via SQLAlchemy: {user.username}")
                
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    if user.role == 'admin':
                        logging.info(f"User {user.username} has role: {user.role}, redirecting to admin dashboard")
                        next_page = url_for('admin_dashboard')
                    else:
                        logging.info(f"User {user.username} has role: {user.role}, redirecting to student dashboard")
                        next_page = url_for('dashboard')
                return redirect(next_page)
        except Exception as e:
            logging.error(f"Database error during login: {str(e)}")
            # Fall back to in-memory database
        
        # Fall back to in-memory database
        user = find_user_by_email(form.email.data, user_db)
        if user is None or not check_password_hash(user.password_hash, form.password.data):
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        logging.info(f"User logged in via in-memory DB: {user.username}")
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            if user.role == 'admin':
                logging.info(f"User {user.username} has role: {user.role}, redirecting to admin dashboard")
                next_page = url_for('admin_dashboard')
            else:
                logging.info(f"User {user.username} has role: {user.role}, redirecting to student dashboard")
                next_page = url_for('dashboard')
        return redirect(next_page)
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = SignupForm()
    if form.validate_on_submit():
        try:
            # Check if email already exists in database first
            user_exists_db = User.query.filter_by(email=form.email.data).first()
            if user_exists_db:
                flash('Email already registered', 'error')
                return redirect(url_for('signup'))
                
            # Check if username already exists in database
            username_exists_db = User.query.filter_by(username=form.username.data).first()
            if username_exists_db:
                flash('Username already taken', 'error')
                return redirect(url_for('signup'))
        except Exception as e:
            logging.error(f"Error checking database for existing user: {str(e)}")
            # Continue with in-memory checks
        
        # Also check in-memory data
        if find_user_by_email(form.email.data, user_db):
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))
        
        # Check if username already exists
        if find_user_by_username(form.username.data, user_db):
            flash('Username already taken', 'error')
            return redirect(url_for('signup'))
        
        try:
            # Try to create user in the database first
            password_hash = generate_password_hash(form.password.data)
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                password_hash=password_hash,
                role='student',  # Always set role to student for signup
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                created_at=datetime.now()
            )
            
            db.session.add(new_user)
            db.session.commit()
            logging.info(f"New user created in database: {new_user.username}")
            
            # Refresh in-memory data
            populate_in_memory_db()
            
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Error creating user in database: {str(e)}")
            db.session.rollback()
            
            # Fall back to in-memory storage
            user_id = get_next_id(user_db)
            # Generate the password hash again in case it wasn't defined earlier
            password_hash = generate_password_hash(form.password.data)
            user = User(
                id=user_id,
                username=form.username.data,
                email=form.email.data,
                password_hash=password_hash,
                role='student',  # Always set role to student for signup
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                created_at=datetime.now()
            )
            user_db[user_id] = user
            
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
    
    # Add this for debugging form validation errors
    if form.errors:
        logging.error(f"Form validation errors: {form.errors}")
    
    return render_template('signup.html', form=form)

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = find_user_by_email(form.email.data, user_db)
        if user:
            # Generate token (in a real app, you would send this by email)
            token = generate_reset_token()
            session['reset_token'] = token
            session['reset_email'] = user.email
            
            # In a real application, you would send an email with the reset link
            flash(f'Password reset instructions have been sent to {user.email}', 'info')
            # For demo purposes, redirect directly to reset page
            return redirect(url_for('reset_password', token=token))
        else:
            flash('Email not found', 'error')
    
    return render_template('reset_password_request.html', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Check if token is valid
    if not session.get('reset_token') or session.get('reset_token') != token:
        flash('Invalid or expired password reset token', 'error')
        return redirect(url_for('reset_password_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = find_user_by_email(session['reset_email'], user_db)
        if user:
            user.password_hash = generate_password_hash(form.password.data)
            
            # Clear session
            session.pop('reset_token', None)
            session.pop('reset_email', None)
            
            flash('Your password has been reset', 'success')
            return redirect(url_for('login'))
    
    return render_template('reset_password.html', form=form)

# Student routes
@app.route('/dashboard')
@login_required
def dashboard():
    # Log user role for debugging
    logging.info(f"User {current_user.username} has role: {current_user.role}")
    
    # Only redirect if the user is an admin AND is directly accessing the dashboard route
    # This prevents an infinite redirect loop but still maintains proper access control
    if current_user.role == 'admin' and request.path == '/dashboard':
        logging.info(f"Redirecting admin user to admin dashboard")
        return redirect(url_for('admin_dashboard'))
    
    logging.info(f"Loading student dashboard for user: {current_user.username}")
    
    # Try to use the SQLAlchemy model first
    try:
        user_enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
        if user_enrollments:
            courses = [Course.query.get(e.course_id) for e in user_enrollments]
            
            # Get progress for each course
            progress = {}
            for enrollment in user_enrollments:
                progress[enrollment.course_id] = enrollment.progress
            
            # Get certificates
            user_certificates = Certificate.query.filter_by(user_id=current_user.id).all()
            certificate_courses = [Course.query.get(c.course_id) for c in user_certificates]
            certificate_courses = [c for c in certificate_courses if c]  # Filter out None values
            
            return render_template('dashboard.html', 
                                courses=courses, 
                                progress=progress, 
                                certificates=user_certificates,
                                certificate_courses=certificate_courses)
    except Exception as e:
        logging.error(f"Error accessing database: {str(e)}")
        # Fall back to in-memory data
        pass
    
    # Fall back to in-memory data if database access fails
    enrollments = get_user_enrollments(current_user.id, enrollment_db)
    courses = [course_db.get(e.course_id) for e in enrollments]
    courses = [c for c in courses if c]  # Filter out None values
    
    # Get progress for each course
    progress = {}
    for enrollment in enrollments:
        progress[enrollment.course_id] = enrollment.progress
    
    # Get certificates
    certificates = get_user_certificates(current_user.id, certificate_db)
    certificate_courses = [course_db.get(c.course_id) for c in certificates]
    certificate_courses = [c for c in certificate_courses if c]  # Filter out None values
    
    return render_template('dashboard.html', 
                          courses=courses, 
                          progress=progress, 
                          certificates=certificates,
                          certificate_courses=certificate_courses)

@app.route('/course/<int:course_id>/module/<int:module_id>')
@login_required
def module_detail(course_id, module_id):
    # Try to get the course from SQLAlchemy first
    try:
        course = Course.query.get(course_id)
        if not course:
            course = course_db.get(course_id)
    except:
        course = course_db.get(course_id)
    
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('courses'))
    
    # Try to get the module from SQLAlchemy
    try:
        module = Module.query.get(module_id)
        if not module or module.course_id != course_id:
            module = module_db.get(module_id)
            if module and module.course_id != course_id:
                module = None
    except:
        module = module_db.get(module_id)
        if module and module.course_id != course_id:
            module = None
    
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Check if user is enrolled using SQLAlchemy
    try:
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
        if enrollment:
            enrolled = True
            progress = enrollment.progress
        else:
            # Fall back to in-memory database
            enrolled = False
            progress = 0
            for e in enrollment_db.values():
                if e.user_id == current_user.id and e.course_id == course_id:
                    enrolled = True
                    progress = e.progress
                    break
    except:
        # Fall back to in-memory database
        enrolled = False
        progress = 0
        for e in enrollment_db.values():
            if e.user_id == current_user.id and e.course_id == course_id:
                enrolled = True
                progress = e.progress
                break
    
    if not enrolled and current_user.role != 'admin':
        flash('You must enroll in this course to view modules', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Get all modules for navigation
    try:
        modules = Module.query.filter_by(course_id=course_id).order_by(Module.order).all()
        if not modules:
            modules = get_course_modules(course_id, module_db)
    except:
        modules = get_course_modules(course_id, module_db)
    
    # Find previous and next modules
    prev_module = None
    next_module = None
    for i, mod in enumerate(modules):
        if mod.id == module_id:
            if i > 0:
                prev_module = modules[i-1]
            if i < len(modules) - 1:
                next_module = modules[i+1]
            break
    
    # Get quiz for this module if exists
    try:
        quiz = Quiz.query.filter_by(module_id=module_id).first()
        quiz_completed = False
        quiz_score = 0
        
        if not quiz:
            # Fall back to in-memory
            for q in quiz_db.values():
                if q.module_id == module_id:
                    quiz = q
                    # Check if user has completed this quiz
                    if hasattr(q, 'user_scores') and current_user.id in q.user_scores:
                        quiz_completed = True
                        quiz_score = q.user_scores[current_user.id]
                    break
    except:
        quiz = None
        quiz_completed = False
        quiz_score = 0
        for q in quiz_db.values():
            if q.module_id == module_id:
                quiz = q
                # Check if user has completed this quiz
                if hasattr(q, 'user_scores') and current_user.id in q.user_scores:
                    quiz_completed = True
                    quiz_score = q.user_scores[current_user.id]
                break
    
    # Check if all modules are completed (for certificate link)
    all_modules_completed = enrolled and progress >= 100
    
    # Update progress to track that this module was viewed
    if enrolled and current_user.role != 'admin':
        try:
            # Get enrollment directly from the database
            enrollment_record = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
            
            if enrollment_record:
                # Increment progress slightly for viewing the module
                module_count = len(modules)
                if module_count > 0:
                    view_increment = int(50 / module_count)  # 50% of progress is from viewing
                    if progress < 100:  # Only update if not already completed
                        enrollment_record.progress = min(100, progress + view_increment)
                        db.session.commit()
        except Exception as e:
            logging.error(f"Error updating progress: {str(e)}")
    
    return render_template('module_detail.html',
                          course=course,
                          module=module,
                          modules=modules,
                          prev_module=prev_module,
                          next_module=next_module,
                          quiz=quiz,
                          quiz_completed=quiz_completed,
                          quiz_score=quiz_score,
                          progress=progress,
                          all_modules_completed=all_modules_completed)

@app.route('/course/<int:course_id>/module/<int:module_id>/quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def take_quiz(course_id, module_id, quiz_id):
    # Try to get the course from SQLAlchemy
    try:
        course = Course.query.get(course_id)
        if not course:
            course = course_db.get(course_id)
    except Exception as e:
        logging.error(f"Error accessing course database: {str(e)}")
        course = course_db.get(course_id)
    
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('courses'))
    
    # Try to get the module from SQLAlchemy
    try:
        module = Module.query.get(module_id)
        if not module or module.course_id != course_id:
            module = module_db.get(module_id)
            if module and module.course_id != course_id:
                module = None
    except Exception as e:
        logging.error(f"Error accessing module database: {str(e)}")
        module = module_db.get(module_id)
        if module and module.course_id != course_id:
            module = None
    
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Try to get the quiz from SQLAlchemy
    try:
        quiz = Quiz.query.get(quiz_id)
        if not quiz or quiz.module_id != module_id:
            quiz = quiz_db.get(quiz_id)
            if quiz and quiz.module_id != module_id:
                quiz = None
    except Exception as e:
        logging.error(f"Error accessing quiz database: {str(e)}")
        quiz = quiz_db.get(quiz_id)
        if quiz and quiz.module_id != module_id:
            quiz = None
    
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('module_detail', course_id=course_id, module_id=module_id))
    
    # Check if user is enrolled using SQLAlchemy
    try:
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
        enrolled = enrollment is not None
    except Exception as e:
        logging.error(f"Error accessing enrollment database: {str(e)}")
        # Fall back to in-memory database
        enrolled = False
        for e in enrollment_db.values():
            if e.user_id == current_user.id and e.course_id == course_id:
                enrolled = True
                break
    
    if not enrolled and current_user.role != 'admin':
        flash('You must be enrolled in this course to take quizzes', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Get questions for this quiz using SQLAlchemy
    try:
        questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).order_by(QuizQuestion.order).all()
        if not questions:
            # Fall back to in-memory database
            questions = [q for q in question_db.values() if q.quiz_id == quiz_id]
    except Exception as e:
        logging.error(f"Error accessing question database: {str(e)}")
        # Fall back to in-memory database
        questions = [q for q in question_db.values() if q.quiz_id == quiz_id]
    
    if not questions:
        flash('This quiz has no questions', 'info')
        return redirect(url_for('module_detail', course_id=course_id, module_id=module_id))
    
    # Generate the form
    form = QuizSubmissionForm()
    
    return render_template('take_quiz.html',
                          course=course,
                          module=module,
                          quiz=quiz,
                          questions=questions,
                          form=form)

@app.route('/course/<int:course_id>/module/<int:module_id>/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(course_id, module_id, quiz_id):
    # Check if course exists
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('courses'))
    
    # Check if module exists
    module = module_db.get(module_id)
    if not module or module.course_id != course_id:
        flash('Module not found', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Check if quiz exists
    quiz = quiz_db.get(quiz_id)
    if not quiz or quiz.module_id != module_id:
        flash('Quiz not found', 'error')
        return redirect(url_for('module_detail', course_id=course_id, module_id=module_id))
    
    # Get questions for this quiz
    questions = [q for q in question_db.values() if q.quiz_id == quiz_id]
    
    # Get user's answers
    answers = {}
    for question in questions:
        answer_key = f'question_{question.id}'
        if answer_key in request.form:
            try:
                answers[question.id] = int(request.form[answer_key])
            except ValueError:
                answers[question.id] = -1  # Invalid answer
    
    # Calculate score
    correct_count = 0
    results = []
    
    for question in questions:
        user_answer = answers.get(question.id, -1)
        is_correct = user_answer == int(question.correct_answer)
        if is_correct:
            correct_count += 1
        results.append((question, user_answer, is_correct))
    
    score = int((correct_count / len(questions)) * 100) if questions else 0
    
    # Store the score
    if not hasattr(quiz, 'user_scores'):
        quiz.user_scores = {}
    quiz.user_scores[current_user.id] = score
    
    # Update course progress if quiz passed (score >= 70%)
    if score >= 70:
        # Find enrollment
        for enrollment in enrollment_db.values():
            if enrollment.user_id == current_user.id and enrollment.course_id == course_id:
                # Update progress - increment by 10% for each passed quiz
                new_progress = min(100, enrollment.progress + 10)
                enrollment.progress = new_progress
                if new_progress == 100:
                    enrollment.completed = True
                break
    
    return render_template('quiz_result.html',
                          course=course,
                          module=module,
                          quiz=quiz,
                          score=score,
                          results=results)

@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll(course_id):
    # First, check if the course exists in the in-memory database
    course = course_db.get(course_id)
    
    if not course:
        try:
            # Also try to get from SQL database as a fallback
            course = Course.query.get(course_id)
        except Exception as e:
            logging.error(f"Error checking for course in database: {str(e)}")
            course = None
    
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('courses'))
    
    # Now check if already enrolled - first check in-memory
    is_enrolled = False
    for enrollment in enrollment_db.values():
        if enrollment.user_id == current_user.id and enrollment.course_id == course_id:
            is_enrolled = True
            break
    
    # If not found in memory, try SQL
    if not is_enrolled:
        try:
            existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
            is_enrolled = existing_enrollment is not None
        except Exception as e:
            logging.error(f"Error checking enrollment in database: {str(e)}")
    
    if is_enrolled:
        flash('You are already enrolled in this course', 'info')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Not enrolled yet, so create new enrollment - first try in-memory
    enrollment_id = get_next_id(enrollment_db)
    new_enrollment = Enrollment(
        id=enrollment_id,
        user_id=current_user.id,
        course_id=course_id,
        progress=0,
        completed=False,
        created_at=datetime.now()
    )
    enrollment_db[enrollment_id] = new_enrollment
    
    # Only try to create in SQL if we have both a user and course in the SQL database
    try:
        # Check if user and course exist in SQL DB first
        db_user = User.query.get(current_user.id)
        db_course = Course.query.get(course_id)
        
        if db_user and db_course:
            # Both exist, so create enrollment
            sql_enrollment = Enrollment(
                user_id=current_user.id,
                course_id=course_id,
                progress=0,
                completed=False
            )
            db.session.add(sql_enrollment)
            db.session.commit()
            logging.info(f"User {current_user.username} enrolled in course {course.title} (SQLAlchemy)")
        else:
            logging.info(f"User {current_user.username} enrolled in course {course.title} (In-memory only - SQL entities not found)")
    except Exception as e:
        logging.error(f"Database enrollment error (non-critical): {str(e)}")
        # We continue with the in-memory enrollment, which we already created
        db.session.rollback()  # Ensure session is cleaned up
    
    flash(f'Successfully enrolled in {course.title}', 'success')
    
    # Find the first module - check in-memory first
    modules = get_course_modules(course_id, module_db)
    if modules:
        return redirect(url_for('module_detail', course_id=course_id, module_id=modules[0].id))
    
    # Also check SQL for modules
    try:
        first_module = Module.query.filter_by(course_id=course_id).order_by(Module.order).first()
        if first_module:
            return redirect(url_for('module_detail', course_id=course_id, module_id=first_module.id))
    except Exception as e:
        logging.error(f"Error finding modules in database: {str(e)}")
    
    # If no modules, go to dashboard
    return redirect(url_for('dashboard'))

@app.route('/profile')
@login_required
def profile():
    enrollments = get_user_enrollments(current_user.id, enrollment_db)
    courses = [course_db.get(e.course_id) for e in enrollments]
    courses = [c for c in courses if c]  # Filter out None values
    
    # Get certificates
    certificates = get_user_certificates(current_user.id, certificate_db)
    certificate_courses = [course_db.get(c.course_id) for c in certificates]
    certificate_courses = [c for c in certificate_courses if c]  # Filter out None values
    
    return render_template('profile.html', 
                          user=current_user, 
                          courses=courses, 
                          certificates=certificates,
                          certificate_courses=certificate_courses)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    form = ProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        # Check if email is changed and already exists
        if form.email.data != current_user.email and find_user_by_email(form.email.data, user_db):
            flash('Email already registered', 'error')
            return redirect(url_for('profile_edit'))
        
        # Check if username is changed and already exists
        if form.username.data != current_user.username and find_user_by_username(form.username.data, user_db):
            flash('Username already taken', 'error')
            return redirect(url_for('profile_edit'))
        
        # Update user data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.bio = form.bio.data
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile_edit.html', form=form)

@app.route('/course/<int:course_id>/certificate')
@login_required
def course_certificate(course_id):
    # Check if course exists
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('courses'))
    
    # Check if user has completed the course
    enrollment_completed = False
    for enrollment in enrollment_db.values():
        if enrollment.user_id == current_user.id and enrollment.course_id == course_id:
            if enrollment.completed or enrollment.progress >= 100:
                enrollment_completed = True
            break
    
    # Allow admins to view certificates without enrollment
    if not enrollment_completed and current_user.role != 'admin':
        flash('You must complete the course to receive a certificate', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Check if certificate already exists
    certificate = None
    for cert in certificate_db.values():
        if cert.user_id == current_user.id and cert.course_id == course_id:
            certificate = cert
            break
    
    # Create certificate if it doesn't exist
    if not certificate:
        certificate_id = get_next_id(certificate_db)
        certificate = Certificate(
            id=certificate_id,
            user_id=current_user.id,
            course_id=course_id,
            issue_date=datetime.now()
        )
        certificate_db[certificate_id] = certificate
        flash('Certificate generated successfully', 'success')
    
    return render_template('certificate.html', certificate=certificate, course=course)

@app.route('/update_progress/<int:course_id>/<int:progress>', methods=['POST'])
@login_required
def update_progress(course_id, progress):
    if progress < 0 or progress > 100:
        return jsonify({"success": False, "message": "Invalid progress value"}), 400
    
    # Find enrollment
    enrollment = None
    for e in enrollment_db.values():
        if e.user_id == current_user.id and e.course_id == course_id:
            enrollment = e
            break
    
    if not enrollment:
        return jsonify({"success": False, "message": "Not enrolled in this course"}), 404
    
    # Update progress
    enrollment.progress = progress
    enrollment.updated_at = datetime.now()
    
    # Mark as completed if 100%
    if progress == 100 and not enrollment.completed:
        enrollment.completed = True
        
        # Generate certificate if doesn't exist
        certificate_exists = False
        for cert in certificate_db.values():
            if cert.user_id == current_user.id and cert.course_id == course_id:
                certificate_exists = True
                break
        
        if not certificate_exists:
            certificate_id = get_next_id(certificate_db)
            certificate = Certificate(
                id=certificate_id,
                user_id=current_user.id,
                course_id=course_id,
                issue_date=datetime.now()
            )
            certificate_db[certificate_id] = certificate
    
    return jsonify({"success": True})

@app.route('/certificate/<int:certificate_id>')
@login_required
def view_certificate(certificate_id):
    certificate = certificate_db.get(certificate_id)
    
    # Allow admins to view any certificate
    if not certificate or (certificate.user_id != current_user.id and current_user.role != 'admin'):
        flash('Certificate not found', 'error')
        return redirect(url_for('dashboard'))
    
    user = user_db.get(certificate.user_id)
    course = course_db.get(certificate.course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('certificate.html', 
                          certificate=certificate, 
                          user=user, 
                          course=course)

@app.route('/certificate/<int:certificate_id>/show')
@login_required
def show_certificate(certificate_id):
    certificate = certificate_db.get(certificate_id)
    
    # Allow admins to view any certificate
    if not certificate or (certificate.user_id != current_user.id and current_user.role != 'admin'):
        flash('Certificate not found', 'error')
        return redirect(url_for('dashboard'))
    
    user = user_db.get(certificate.user_id)
    course = course_db.get(certificate.course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('dashboard'))
    
    cert_img = generate_certificate(user, course, certificate.id)
    
    return send_file(
        cert_img,
        mimetype='image/png',
        as_attachment=False
    )

@app.route('/certificate/<int:certificate_id>/download')
@login_required
def download_certificate(certificate_id):
    certificate = certificate_db.get(certificate_id)
    
    # Allow admins to download any certificate
    if not certificate or (certificate.user_id != current_user.id and current_user.role != 'admin'):
        flash('Certificate not found', 'error')
        return redirect(url_for('dashboard'))
    
    user = user_db.get(certificate.user_id)
    course = course_db.get(certificate.course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('dashboard'))
    
    cert_img = generate_certificate(user, course, certificate.id)
    
    return send_file(cert_img, 
                     mimetype='image/png',
                     as_attachment=True,
                     download_name=f'certificate_{certificate.id}.png')

# Utility routes
@app.route('/refresh-data')
@login_required
def refresh_data():
    """Refresh in-memory data from the database"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    try:
        populate_in_memory_db()
        flash('Data refreshed successfully', 'success')
    except Exception as e:
        flash(f'Error refreshing data: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Add additional logging for debugging
    logging.info(f"Admin dashboard access by user: {current_user.username}, role: {current_user.role}")
    
    if current_user.role != 'admin':
        logging.warning(f"Access denied to admin dashboard for user: {current_user.username}, role: {current_user.role}")
        flash('Access denied: Admin privileges required', 'error')
        return redirect(url_for('dashboard'))
    
    stats = get_stats(user_db, course_db, enrollment_db)
    
    # Get popular courses with full course data
    popular_courses = [(course_db.get(course_id), count) for course_id, count in stats['popular_courses']]
    
    return render_template('admin/dashboard.html', 
                          stats=stats,
                          popular_courses=popular_courses)

@app.route('/admin/courses')
@login_required
def admin_courses():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    courses = list(course_db.values())
    
    # Get enrollment counts for each course
    enrollments = {}
    for course in courses:
        enrollments[course.id] = sum(1 for e in enrollment_db.values() if e.course_id == course.id)
    
    return render_template('admin/courses.html', 
                          courses=courses,
                          enrollments=enrollments)

@app.route('/admin/courses/new', methods=['GET', 'POST'])
@login_required
def admin_course_new():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    form = CourseForm()
    if form.validate_on_submit():
        course_id = get_next_id(course_db)
        course = Course(
            id=course_id,
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            level=form.level.data,
            price=form.price.data,
            instructor_id=current_user.id,
            image_url=form.image_url.data,
            created_at=datetime.now()
        )
        course_db[course_id] = course
        
        flash('Course created successfully', 'success')
        return redirect(url_for('admin_course_edit', course_id=course_id))
    
    return render_template('admin/course_edit.html', 
                          form=form,
                          course=None,
                          modules=[],
                          edit_mode=False)

@app.route('/admin/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_course_edit(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    form = CourseForm(obj=course)
    if form.validate_on_submit():
        course.title = form.title.data
        course.description = form.description.data
        course.category = form.category.data
        course.level = form.level.data
        course.price = form.price.data
        course.image_url = form.image_url.data
        course.updated_at = datetime.now()
        
        flash('Course updated successfully', 'success')
        return redirect(url_for('admin_course_edit', course_id=course_id))
    
    modules = get_course_modules(course_id, module_db)
    
    # Get all quizzes for checking if modules have quizzes
    quizzes = []
    try:
        # Try to use SQLAlchemy first
        quizzes = Quiz.query.all()
    except Exception as e:
        logging.error(f"Error fetching quizzes from database: {str(e)}")
        # Fall back to in-memory
        quizzes = list(quiz_db.values())
    
    return render_template('admin/course_edit.html', 
                          form=form,
                          course=course,
                          modules=modules,
                          quizzes=quizzes,
                          edit_mode=True)

@app.route('/admin/courses/<int:course_id>/modules/reorder', methods=['POST'])
@login_required
def admin_modules_reorder(course_id):
    app.logger.info(f"Module reorder request received for course {course_id}")
    
    if current_user.role != 'admin':
        app.logger.warning(f"Access denied for user {current_user.id} trying to reorder modules")
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Verify the course exists
        course = Course.query.get(course_id)
        if not course:
            app.logger.error(f"Course {course_id} not found for module reordering")
            return jsonify({'success': False, 'message': 'Course not found'}), 404
        
        # Process the request data
        data = request.get_json()
        app.logger.debug(f"Received reorder data: {data}")
        
        if not data or 'modules' not in data:
            app.logger.error(f"Invalid reorder data format: {data}")
            return jsonify({'success': False, 'message': 'Invalid data format'}), 400
        
        try:
            # Parse and validate module data
            updates = []
            for item in data['modules']:
                module_id = int(item['module_id'])
                new_order = int(item['order'])
                updates.append({'id': module_id, 'order': new_order})
            
            if not updates:
                app.logger.error("No valid module data to process")
                return jsonify({'success': False, 'message': 'No modules to update'}), 400
            
            app.logger.info(f"Processing {len(updates)} module order updates")
            
            # Create a fresh session to ensure isolation
            with db.engine.begin() as connection:
                # First verify all modules belong to this course
                for update in updates:
                    result = connection.execute(
                        "SELECT course_id FROM modules WHERE id = :id",
                        {"id": update['id']}
                    ).first()
                    
                    if not result:
                        app.logger.error(f"Module {update['id']} not found in database")
                        return jsonify({'success': False, 'message': f'Module {update["id"]} not found'}), 404
                    
                    if result[0] != course_id:
                        app.logger.error(f"Module {update['id']} belongs to course {result[0]}, not {course_id}")
                        return jsonify({'success': False, 'message': f'Module {update["id"]} belongs to a different course'}), 403
                
                # Use raw SQL to force updates to be committed properly
                update_count = 0
                
                # Track the current order values for debugging
                for update in updates:
                    # Get current order value from database
                    current = connection.execute(
                        "SELECT \"order\" FROM modules WHERE id = :id", 
                        {"id": update['id']}
                    ).first()
                    update['current_order'] = current[0] if current else None
                    app.logger.info(f"Module {update['id']} current order={update['current_order']}, new order={update['order']}")
                
                # Execute all updates
                connection.execute("BEGIN")  # Explicitly start transaction
                try:
                    for update in updates:
                        # Use a timestamped update to avoid caching issues
                        result = connection.execute(
                            "UPDATE modules SET \"order\" = :order, updated_at = NOW() WHERE id = :id AND course_id = :course_id",
                            {"order": update['order'], "id": update['id'], "course_id": course_id}
                        )
                        
                        if result.rowcount > 0:
                            update_count += 1
                            app.logger.info(f"SQL UPDATE: Changed module {update['id']} order from {update['current_order']} to {update['order']}")
                        else:
                            app.logger.warning(f"SQL UPDATE: Failed to update module {update['id']} - no rows affected")
                    
                    # Force the transaction to commit
                    connection.execute("COMMIT")
                    app.logger.info(f"Transaction explicitly committed: {update_count} updates")
                except Exception as e:
                    connection.execute("ROLLBACK")
                    app.logger.error(f"Error during transaction, rolled back: {str(e)}")
                    raise
                
                # Verify all updates were applied successfully
                verified_count = 0
                for update in updates:
                    verify = connection.execute(
                        "SELECT \"order\" FROM modules WHERE id = :id", 
                        {"id": update['id']}
                    ).first()
                    
                    if verify and verify[0] == update['order']:
                        verified_count += 1
                        app.logger.info(f"✅ Verified module {update['id']} now has order={update['order']} in database")
                    else:
                        app.logger.warning(f"❌ Verification failed for module {update['id']}: expected {update['order']}, got {verify[0] if verify else 'none'}")
                
                app.logger.info(f"Successfully updated {update_count} out of {len(updates)} modules in database, with {verified_count} verified.")
            
            # Reload modules from database to memory to ensure consistency
            # First, reload the specific modules we just updated
            updated_ids = [update['id'] for update in updates]
            updated_modules = Module.query.filter(Module.id.in_(updated_ids)).all()
            
            for module in updated_modules:
                module_db[module.id] = module
                app.logger.info(f"Refreshed module {module.id} in memory, order is now {module.order}")
            
            # Now refresh all course data for consistency
            app.logger.debug(f"Refreshed data for course {course_id}: {len(course.get_modules())} modules, {Quiz.query.join(Module).filter(Module.course_id == course_id).count()} quizzes")
            
            # Also refresh in-memory data for consistency
            # Force a full reload from database to ensure all changes are reflected
            try:
                # Execute a direct query to verify
                with db.engine.connect() as conn:
                    results = conn.execute(f"SELECT id, \"order\" FROM modules WHERE course_id = {course_id} ORDER BY \"order\"").fetchall()
                    for result in results:
                        app.logger.info(f"Verified module {result[0]} has order {result[1]}")
                
                # Completely refresh in-memory database
                db.session.expire_all()
                populate_in_memory_db()
            except Exception as e:
                app.logger.error(f"Error during final verification: {str(e)}")
            
            return jsonify({
                'success': True, 
                'message': f'Module orders updated successfully. {update_count} modules updated and {verified_count} verified.'
            })
            
        except Exception as e:
            app.logger.error(f"Database error during module reordering: {str(e)}")
            return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500
            
    except Exception as e:
        app.logger.error(f"Error in module reordering: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/admin/courses/<int:course_id>/delete', methods=['POST'])
@login_required
def admin_course_delete(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    # Delete course and related data
    # First, get all related modules
    modules_to_delete = [m.id for m in module_db.values() if m.course_id == course_id]
    
    # Delete quizzes and questions related to these modules
    for quiz in list(quiz_db.values()):
        if quiz.module_id in modules_to_delete:
            # Delete questions for this quiz
            for question_id in list(question_db.keys()):
                if question_db[question_id].quiz_id == quiz.id:
                    del question_db[question_id]
            # Delete the quiz
            del quiz_db[quiz.id]
    
    # Delete modules
    for module_id in modules_to_delete:
        if module_id in module_db:
            del module_db[module_id]
    
    # Delete enrollments
    for enrollment_id in list(enrollment_db.keys()):
        if enrollment_db[enrollment_id].course_id == course_id:
            del enrollment_db[enrollment_id]
    
    # Delete certificates
    for certificate_id in list(certificate_db.keys()):
        if certificate_db[certificate_id].course_id == course_id:
            del certificate_db[certificate_id]
    
    # Finally, delete the course
    del course_db[course_id]
    
    flash('Course and all related data deleted successfully', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/courses/<int:course_id>/modules/new', methods=['GET', 'POST'])
@login_required
def admin_module_new(course_id):
    app.logger.info(f"Creating new module for course {course_id}")
    
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get course from in-memory database first
    course = course_db.get(course_id)
    if not course:
        try:
            # Get from SQL database as fallback
            course = Course.query.get(course_id)
            if course:
                # Update in-memory course
                course_db[course_id] = course
                app.logger.info(f"Found course {course_id} in database and updated in-memory copy")
        except Exception as e:
            app.logger.error(f"Database error when fetching course: {str(e)}")
    
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    form = ModuleForm()
    if form.validate_on_submit():
        now = datetime.now()
        module_id = get_next_id(module_db)
        app.logger.info(f"Generated new module ID: {module_id}")
        
        # Handle video file upload
        video_file_path = None
        if form.video_file.data:
            video_filename = f'module_{module_id}_video_{secure_filename(form.video_file.data.filename)}'
            video_file_path = os.path.join('uploads/videos', video_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.join('static', 'uploads/videos'), exist_ok=True)
            form.video_file.data.save(os.path.join('static', video_file_path))
            app.logger.info(f"Saved video file: {video_file_path}")
        
        # Handle PDF file upload
        pdf_file_path = None
        if form.pdf_file.data:
            pdf_filename = f'module_{module_id}_pdf_{secure_filename(form.pdf_file.data.filename)}'
            pdf_file_path = os.path.join('uploads/pdfs', pdf_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.join('static', 'uploads/pdfs'), exist_ok=True)
            form.pdf_file.data.save(os.path.join('static', pdf_file_path))
            app.logger.info(f"Saved PDF file: {pdf_file_path}")
        
        # Create module in memory
        module = Module(
            id=module_id,
            course_id=course_id,
            title=form.title.data,
            content=form.content.data,
            order=form.order.data,
            video_url=form.video_url.data,
            pdf_url=form.pdf_url.data,
            video_file=video_file_path,
            pdf_file=pdf_file_path,
            created_at=now,
            updated_at=now
        )
        module_db[module_id] = module
        app.logger.info(f"Added module {module_id} to in-memory database")
        
        # Also add to SQL database
        try:
            db_module = Module(
                id=module_id,
                course_id=course_id,
                title=form.title.data,
                content=form.content.data,
                order=form.order.data,
                video_url=form.video_url.data,
                pdf_url=form.pdf_url.data,
                video_file=video_file_path,
                pdf_file=pdf_file_path,
                created_at=now,
                updated_at=now
            )
            db.session.add(db_module)
            db.session.commit()
            app.logger.info(f"Successfully added module {module_id} to SQL database")
            flash('Module created successfully', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error saving module to database: {str(e)}")
            flash(f'Module created in memory but failed to save to database: {str(e)}', 'warning')
        
        # Check if the request came from the course wizard
        referer = request.headers.get('Referer', '')
        app.logger.info(f"Referer: {referer}")
        if 'course-wizard/step2' in referer:
            return redirect(url_for('admin_course_wizard_step2', course_id=course_id))
        else:
            return redirect(url_for('admin_course_edit', course_id=course_id))
    
    # Set default order as the next one
    existing_modules = get_course_modules(course_id, module_db)
    form.order.data = len(existing_modules) + 1
    
    return render_template('admin/module_edit.html',
                          form=form,
                          course=course,
                          module=None,
                          edit_mode=False)

@app.route('/admin/modules/<int:module_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_module_edit(module_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get module from in-memory database
    module = module_db.get(module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
    
    course = course_db.get(module.course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    form = ModuleForm(obj=module)
    if form.validate_on_submit():
        # Update module in memory
        module.title = form.title.data
        module.content = form.content.data
        module.order = form.order.data
        module.video_url = form.video_url.data
        module.pdf_url = form.pdf_url.data
        module.updated_at = datetime.now()
        
        # Handle video file upload
        video_file_path = module.video_file
        if form.video_file.data:
            # Remove old file if exists
            if module.video_file:
                try:
                    old_path = os.path.join('static', module.video_file)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                        logging.info(f"Removed old video file: {old_path}")
                except Exception as e:
                    logging.error(f"Error removing old video file: {str(e)}")
            
            video_filename = f'module_{module_id}_video_{secure_filename(form.video_file.data.filename)}'
            video_file_path = os.path.join('uploads/videos', video_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.join('static', 'uploads/videos'), exist_ok=True)
            form.video_file.data.save(os.path.join('static', video_file_path))
            module.video_file = video_file_path
            logging.info(f"Saved new video file: {video_file_path}")
        
        # Handle PDF file upload
        pdf_file_path = module.pdf_file
        if form.pdf_file.data:
            # Remove old file if exists
            if module.pdf_file:
                try:
                    old_path = os.path.join('static', module.pdf_file)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                        logging.info(f"Removed old PDF file: {old_path}")
                except Exception as e:
                    logging.error(f"Error removing old PDF file: {str(e)}")
            
            pdf_filename = f'module_{module_id}_pdf_{secure_filename(form.pdf_file.data.filename)}'
            pdf_file_path = os.path.join('uploads/pdfs', pdf_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.join('static', 'uploads/pdfs'), exist_ok=True)
            form.pdf_file.data.save(os.path.join('static', pdf_file_path))
            module.pdf_file = pdf_file_path
            logging.info(f"Saved new PDF file: {pdf_file_path}")
        
        # Also update in the PostgreSQL database
        try:
            db_module = Module.query.get(module_id)
            if db_module:
                # Update existing module
                db_module.title = form.title.data
                db_module.content = form.content.data
                db_module.order = form.order.data
                db_module.video_url = form.video_url.data
                db_module.pdf_url = form.pdf_url.data
                db_module.video_file = video_file_path
                db_module.pdf_file = pdf_file_path
                db_module.updated_at = datetime.now()
                db.session.commit()
                app.logger.info(f"Updated module {module_id} in database")
            else:
                # Create new module in database
                db_module = Module(
                    id=module_id,
                    course_id=module.course_id,
                    title=form.title.data,
                    content=form.content.data,
                    order=form.order.data,
                    video_url=form.video_url.data,
                    pdf_url=form.pdf_url.data,
                    video_file=video_file_path,
                    pdf_file=pdf_file_path,
                    created_at=module.created_at,
                    updated_at=datetime.now()
                )
                db.session.add(db_module)
                db.session.commit()
                app.logger.info(f"Created new module {module_id} in database")
        except Exception as e:
            app.logger.error(f"Error updating module in database: {str(e)}")
            db.session.rollback()
            flash(f'Module updated in memory, but database update failed: {str(e)}', 'warning')
        else:
            flash('Module updated successfully in both memory and database', 'success')
        
        # Check if we are in wizard flow - if the referer has 'course-wizard' in the URL
        referer = request.referrer or ""
        if 'course-wizard' in referer:
            return redirect(url_for('admin_course_wizard_step2', course_id=course.id))
        else:
            return redirect(url_for('admin_course_edit', course_id=course.id))
    
    # Get quiz if exists
    quiz = next((q for q in quiz_db.values() if q.module_id == module_id), None)
    
    return render_template('admin/module_edit.html',
                          form=form,
                          course=course,
                          module=module,
                          quiz=quiz,
                          edit_mode=True)

@app.route('/admin/modules/<int:module_id>/delete', methods=['POST'])
@login_required
def admin_module_delete(module_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get module from in-memory database
    module = module_db.get(module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
    
    course_id = module.course_id
    app.logger.info(f"Deleting module {module_id} from course {course_id}")
    
    # Also delete from PostgreSQL database
    try:
        # First, find quizzes associated with this module
        db_module = Module.query.get(module_id)
        if db_module:
            # Find any quizzes for this module
            db_quiz = Quiz.query.filter_by(module_id=module_id).first()
            if db_quiz:
                # Delete questions for this quiz
                QuizQuestion.query.filter_by(quiz_id=db_quiz.id).delete()
                # Delete the quiz
                db.session.delete(db_quiz)
            
            # Now delete the module itself
            db.session.delete(db_module)
            db.session.commit()
            app.logger.info(f"Successfully deleted module {module_id} from database")
    except Exception as e:
        app.logger.error(f"Error deleting module from database: {str(e)}")
        db.session.rollback()
    
    # Delete uploaded files if they exist
    if module.video_file:
        try:
            file_path = os.path.join('static', module.video_file)
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Deleted video file: {file_path}")
        except Exception as e:
            logging.error(f"Error deleting video file: {str(e)}")
    
    if module.pdf_file:
        try:
            file_path = os.path.join('static', module.pdf_file)
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Deleted PDF file: {file_path}")
        except Exception as e:
            logging.error(f"Error deleting PDF file: {str(e)}")
    
    # Delete quizzes and questions related to this module in memory
    for quiz in list(quiz_db.values()):
        if quiz.module_id == module_id:
            # Delete questions for this quiz
            for question_id in list(question_db.keys()):
                if question_db[question_id].quiz_id == quiz.id:
                    del question_db[question_id]
            # Delete the quiz
            del quiz_db[quiz.id]
    
    # Delete the module from in-memory DB
    del module_db[module_id]
    
    flash('Module and related data deleted successfully', 'success')
    
    # Check if we are in wizard flow - if the referer has 'course-wizard' in the URL
    referer = request.referrer or ""
    if 'course-wizard' in referer:
        return redirect(url_for('admin_course_wizard_step2', course_id=course_id))
    else:
        return redirect(url_for('admin_course_edit', course_id=course_id))

@app.route('/admin/modules/<int:module_id>/quiz/new', methods=['GET', 'POST'])
@login_required
def admin_quiz_new(module_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    module = module_db.get(module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
    
    course = course_db.get(module.course_id)
    
    # Check if a quiz already exists for this module
    existing_quiz = next((q for q in quiz_db.values() if q.module_id == module_id), None)
    
    # If we're in POST method, we're handling a form submission
    if request.method == 'POST':
        app.logger.debug(f"Quiz form POST data: {request.form}")
        
        # Get form data directly from request.form
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        passing_score_str = request.form.get('passing_score', '70')
        
        # Basic validation
        if not title:
            flash('Quiz title is required', 'error')
            return redirect(url_for('admin_course_wizard_step3', course_id=course.id))
            
        if not description:
            flash('Quiz description is required', 'error')
            return redirect(url_for('admin_course_wizard_step3', course_id=course.id))
        
        try:
            passing_score = int(passing_score_str)
            if passing_score < 1 or passing_score > 100:
                flash('Passing score must be between 1 and 100', 'error')
                return redirect(url_for('admin_course_wizard_step3', course_id=course.id))
        except ValueError:
            passing_score = 70  # Default if conversion fails
            
        if existing_quiz:
            # Update existing quiz
            existing_quiz.title = title
            existing_quiz.description = description
            existing_quiz.passing_score = passing_score
            existing_quiz.updated_at = datetime.now()
            flash('Quiz updated successfully.', 'success')
            quiz_id = existing_quiz.id
        else:
            # Create new quiz
            quiz_id = get_next_id(quiz_db)
            quiz = Quiz(
                id=quiz_id,
                module_id=module_id,
                title=title,
                description=description,
                passing_score=passing_score,
                created_at=datetime.now()
            )
            quiz_db[quiz_id] = quiz
            flash('Quiz created successfully.', 'success')
        
        # Check if the request came from the course wizard
        referer = request.headers.get('Referer', '')
        if 'course-wizard/step3' in referer:
            return redirect(url_for('admin_course_wizard_step3', course_id=course.id))
        else:
            return redirect(url_for('admin_quiz_edit', quiz_id=quiz_id))
    
    # If we're in GET mode or the form submission failed, and this is not from the accordion
    if existing_quiz and 'course-wizard/step3' not in request.headers.get('Referer', ''):
        flash('A quiz already exists for this module', 'info')
        return redirect(url_for('admin_quiz_edit', quiz_id=existing_quiz.id))
    
    form = QuizForm()
    return render_template('admin/quiz_edit.html',
                          form=form,
                          module=module,
                          course=course,
                          quiz=None,
                          questions=[],
                          edit_mode=False)

@app.route('/admin/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_quiz_edit(quiz_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_courses'))
    
    module = module_db.get(quiz.module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
    
    course = course_db.get(module.course_id)
    
    form = QuizForm(obj=quiz)
    if form.validate_on_submit():
        quiz.title = form.title.data
        quiz.description = form.description.data
        quiz.passing_score = form.passing_score.data
        quiz.updated_at = datetime.now()
        
        flash('Quiz updated successfully', 'success')
        
        # Check if the request came from the course wizard
        referer = request.headers.get('Referer', '')
        if 'course-wizard/step3' in referer:
            return redirect(url_for('admin_course_wizard_step3', course_id=course.id))
        else:
            return redirect(url_for('admin_quiz_edit', quiz_id=quiz_id))
    
    # Get questions for this quiz
    questions = [q for q in question_db.values() if q.quiz_id == quiz_id]
    questions = sorted(questions, key=lambda q: q.order)
    
    return render_template('admin/quiz_edit.html',
                          form=form,
                          module=module,
                          course=course,
                          quiz=quiz,
                          questions=questions,
                          edit_mode=True)

@app.route('/admin/quiz/<int:quiz_id>/question/new', methods=['GET', 'POST'])
@login_required
def admin_question_new(quiz_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Add debug logging
    app.logger.debug(f"Creating a new question for quiz {quiz_id}")
    app.logger.debug(f"Question form data: {request.form}")
    
    quiz = quiz_db.get(int(quiz_id))
    if not quiz:
        app.logger.error(f"Quiz not found with ID: {quiz_id}")
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_courses'))
    
    form = QuestionForm()
    if request.method == 'POST':
        app.logger.debug("Processing POST request for question creation")
        
        # Get data directly from request.form to avoid validation issues
        question_text = request.form.get('question')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3', '')
        option4 = request.form.get('option4', '')
        correct_answer = request.form.get('correct_answer', '0')
        order = request.form.get('order', '1')
        
        # Validate essential fields
        if not question_text or not option1 or not option2:
            app.logger.error("Missing required fields for question")
            flash('Question text, Option 1, and Option 2 are required', 'error')
            # Get the module to redirect properly
            module = module_db.get(quiz.module_id)
            return redirect(url_for('admin_course_wizard_step3', course_id=module.course_id))
        
        # Create new question ID
        question_id = get_next_id(question_db)
        app.logger.debug(f"Generated new question ID: {question_id}")
        
        # Gather options
        options = [option1, option2]
        if option3:
            options.append(option3)
        if option4:
            options.append(option4)
        
        # Create the question object
        try:
            question = QuizQuestion(
                id=question_id,
                quiz_id=int(quiz_id),
                question=question_text,
                options=options,
                correct_answer=int(correct_answer),
                order=int(order),
                created_at=datetime.now()
            )
            
            # Save to in-memory DB
            question_db[question_id] = question
            
            # Also save to PostgreSQL
            db.session.add(question)
            db.session.commit()
            
            app.logger.debug(f"Question created with ID: {question_id} for quiz: {quiz_id}")
            flash('Question added successfully', 'success')
            
            # Re-populate in-memory DB to ensure consistency
            populate_in_memory_db()
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating question: {str(e)}")
            flash(f'Error creating question: {str(e)}', 'error')
        
        # Check if the request came from the course wizard
        referer = request.headers.get('Referer', '')
        if 'course-wizard/step3' in referer:
            # Get the course ID from the module
            module = module_db.get(quiz.module_id)
            if module:
                course = course_db.get(module.course_id)
                if course:
                    # Add success query param to indicate the question was added successfully
                    return redirect(url_for('admin_course_wizard_step3', course_id=course.id, question_added=True))
        
        return redirect(url_for('admin_quiz_edit', quiz_id=quiz_id))
    
    # Set default order as the next one
    existing_questions = [q for q in question_db.values() if q.quiz_id == quiz_id]
    form.order.data = len(existing_questions) + 1
    
    # Get module and course for breadcrumbs
    module = module_db.get(quiz.module_id)
    course = course_db.get(module.course_id) if module else None
    
    # Check if this is an AJAX request from the wizard or if the referer contains course-wizard/step3
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'course-wizard/step3' in request.headers.get('Referer', '')):
        return render_template('admin/question_form_ajax.html',
                             form=form,
                             quiz=quiz,
                             module=module,
                             course=course)
    
    return render_template('admin/question_edit.html',
                          form=form,
                          quiz=quiz,
                          module=module,
                          course=course,
                          question=None,
                          edit_mode=False)

@app.route('/admin/question/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_question_edit(question_id):
    """Redirect to the course wizard's edit question functionality"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    question = question_db.get(question_id)
    if not question:
        flash('Question not found', 'error')
        return redirect(url_for('admin_courses'))
    
    # Redirect to the course wizard's edit question functionality
    app.logger.debug(f"Redirecting question edit request from standalone to wizard for question {question_id}")
    return redirect(f'/admin/question/{question_id}/edit-wizard')

@app.route('/admin/question/<int:question_id>/delete', methods=['POST'])
@login_required
def admin_question_delete(question_id):
    """Delete a question from the quiz and redirect back to the question management page"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    question = question_db.get(question_id)
    if not question:
        flash('Question not found', 'error')
        return redirect(url_for('admin_courses'))
    
    quiz_id = question.quiz_id
    
    try:
        # Delete from database first
        with app.app_context():
            db_question = QuizQuestion.query.get(question_id)
            if db_question:
                app.logger.debug(f"Deleting question ID: {question_id} from database")
                db.session.delete(db_question)
                db.session.commit()
            
            # Delete the question from in-memory
            app.logger.debug(f"Deleting question ID: {question_id} from memory")
            if question_id in question_db:
                del question_db[question_id]
                
            flash('Question deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting question: {str(e)}")
        flash(f'Error deleting question: {str(e)}', 'error')
    
    # Redirect back to the question management page
    return redirect(f'/admin/quiz/{quiz_id}/questions')

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    users = list(user_db.values())
    
    # Get enrollment counts for each user
    enrollments = {}
    for user in users:
        enrollments[user.id] = sum(1 for e in enrollment_db.values() if e.user_id == user.id)
    
    return render_template('admin/users.html', 
                          users=users,
                          enrollments=enrollments)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_user_edit(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    user = user_db.get(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin_users'))
    
    form = UserForm(obj=user)
    if form.validate_on_submit():
        # Check if email is changed and already exists
        if form.email.data != user.email and find_user_by_email(form.email.data, user_db):
            flash('Email already registered', 'error')
            return redirect(url_for('admin_user_edit', user_id=user_id))
        
        # Check if username is changed and already exists
        if form.username.data != user.username and find_user_by_username(form.username.data, user_db):
            flash('Username already taken', 'error')
            return redirect(url_for('admin_user_edit', user_id=user_id))
        
        # Update user data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        
        flash('User updated successfully', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/user_edit.html', form=form, user=user)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_user_delete(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    if user_id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_users'))
    
    user = user_db.get(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin_users'))
    
    # Delete user's enrollments
    for enrollment_id in list(enrollment_db.keys()):
        if enrollment_db[enrollment_id].user_id == user_id:
            del enrollment_db[enrollment_id]
    
    # Delete user's certificates
    for certificate_id in list(certificate_db.keys()):
        if certificate_db[certificate_id].user_id == user_id:
            del certificate_db[certificate_id]
    
    # Delete the user
    del user_db[user_id]
    
    flash('User and related data deleted successfully', 'success')
    return redirect(url_for('admin_users'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500
