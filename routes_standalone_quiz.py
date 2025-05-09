from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from datetime import datetime
from app import app, db
from models import Course, Module, Quiz, QuizQuestion, course_db, module_db, quiz_db, question_db
from utils import get_next_id, get_course_modules

@app.route('/admin/standalone-quiz-management/<int:course_id>', methods=['GET'])
@login_required
def admin_standalone_quiz_management(course_id):
    """Standalone version of quiz management that doesn't rely on template inheritance."""
    
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    modules = get_course_modules(course_id, module_db)
    
    # Get quizzes for this course's modules
    quizzes = [q for q in quiz_db.values() if any(m.id == q.module_id for m in modules)]
    
    # Get questions for these quizzes
    questions = [q for q in question_db.values() if any(quiz.id == q.quiz_id for quiz in quizzes)]
    
    app.logger.debug(f"Loading standalone quiz management for course {course_id}")
    app.logger.debug(f"Found {len(modules)} modules, {len(quizzes)} quizzes, {len(questions)} questions")
    
    return render_template(
        'admin/simple_quiz_management.html', 
        course=course, 
        modules=modules,
        quizzes=quizzes,
        questions=questions
    )

@app.route('/admin/standalone-quiz-management/<int:course_id>', methods=['POST'])
@login_required
def admin_standalone_quiz_create(course_id):
    """Create a quiz from the standalone management page."""
    
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    module_id = request.form.get('module_id')
    title = request.form.get('title')
    description = request.form.get('description')
    passing_score = request.form.get('passing_score')
    
    if not all([module_id, title, description, passing_score]):
        flash('All fields are required', 'error')
        return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
    try:
        module_id = int(module_id)
        passing_score = int(passing_score)
    except ValueError:
        flash('Invalid input data', 'error')
        return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
    # Check if module exists
    module = module_db.get(module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
    # Check if module belongs to this course
    if module.course_id != course_id:
        flash('Module does not belong to this course', 'error')
        return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
    # Check if module already has a quiz
    existing_quiz = next((q for q in quiz_db.values() if q.module_id == module_id), None)
    if existing_quiz:
        flash('This module already has a quiz. Edit the existing quiz or select a different module.', 'warning')
        return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
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
    
    flash('Quiz created successfully', 'success')
    return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))

@app.route('/admin/simple-quiz-edit/<int:quiz_id>', methods=['POST'])
@login_required
def admin_standalone_quiz_edit(quiz_id):
    """Edit a quiz from the standalone management page."""
    
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_courses'))
    
    module_id = request.form.get('module_id')
    title = request.form.get('title')
    description = request.form.get('description')
    passing_score = request.form.get('passing_score')
    course_id = request.form.get('course_id')
    
    if not all([module_id, title, description, passing_score, course_id]):
        flash('All fields are required', 'error')
        return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
    try:
        module_id = int(module_id)
        passing_score = int(passing_score)
        course_id = int(course_id)
    except ValueError:
        flash('Invalid input data', 'error')
        return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
    # Check if module exists
    module = module_db.get(module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
    # Check if module belongs to this course
    if module.course_id != course_id:
        flash('Module does not belong to this course', 'error')
        return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
    # If changing modules, check if target module already has a quiz
    if module_id != quiz.module_id:
        existing_quiz = next((q for q in quiz_db.values() if q.module_id == module_id and q.id != quiz_id), None)
        if existing_quiz:
            flash('The selected module already has a quiz. Please select a different module.', 'warning')
            return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
    # Update quiz
    quiz.module_id = module_id
    quiz.title = title
    quiz.description = description
    quiz.passing_score = passing_score
    quiz.updated_at = datetime.now()
    
    flash('Quiz updated successfully', 'success')
    return redirect(url_for('admin_standalone_quiz_management', course_id=course_id))
    
@app.route('/admin/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
def admin_quiz_delete(quiz_id):
    """Delete a quiz and its associated questions."""
    
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_courses'))
    
    # Find the module and course for this quiz
    module = module_db.get(quiz.module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
        
    course_id = module.course_id
    
    # Get all questions for this quiz
    questions_to_delete = [q for q in question_db.values() if q.quiz_id == quiz_id]
    
    # Delete all questions first
    for question in questions_to_delete:
        app.logger.debug(f"Deleting question ID: {question.id}")
        del question_db[question.id]
    
    # Delete the quiz
    app.logger.debug(f"Deleting quiz ID: {quiz_id}, Title: {quiz.title}")
    del quiz_db[quiz_id]
    
    flash('Quiz and its questions were deleted successfully', 'success')
    
    # Return to Step 3 of course wizard
    return redirect(url_for('admin_course_wizard_step3', course_id=course_id))