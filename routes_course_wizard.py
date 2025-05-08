from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from datetime import datetime
from app import app
from forms import CourseForm
from models import Course, db, course_db, module_db, quiz_db, question_db
from utils import get_next_id, get_course_modules

# Course Wizard Step 1 - Course Details
@app.route('/admin/course-wizard/step1', methods=['GET', 'POST'])
@app.route('/admin/course-wizard/step1/<int:course_id>', methods=['GET', 'POST'])
@login_required
def admin_course_wizard_step1(course_id=None):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    edit_mode = course_id is not None
    course = None
    
    if edit_mode:
        course = course_db.get(course_id)
        if not course:
            flash('Course not found', 'error')
            return redirect(url_for('admin_courses'))
    
    form = CourseForm(obj=course if edit_mode else None)
    
    if form.validate_on_submit():
        if edit_mode:
            # Update existing course
            course.title = form.title.data
            course.description = form.description.data
            course.category = form.category.data
            course.level = form.level.data
            course.price = form.price.data
            course.image_url = form.image_url.data
            course.updated_at = datetime.now()
            
            flash('Course updated successfully', 'success')
        else:
            # Create new course
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
        
        # Redirect to step 2
        return redirect(url_for('admin_course_wizard_step2', course_id=course_id))
    
    return render_template('admin/course_wizard_step1.html',
                          form=form,
                          course=course,
                          edit_mode=edit_mode,
                          wizard_title='Course Setup - Step 1: Course Details',
                          step=1,
                          progress_percentage=25)

# Course Wizard Step 2 - Modules
@app.route('/admin/course-wizard/step2/<int:course_id>', methods=['GET'])
@login_required
def admin_course_wizard_step2(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    modules = get_course_modules(course_id, module_db)
    
    # Get all quizzes for checking if modules have quizzes
    quizzes = []
    try:
        quizzes = list(quiz_db.values())
    except Exception as e:
        app.logger.error(f"Error fetching quizzes: {str(e)}")
    
    return render_template('admin/course_wizard_step2.html',
                          course=course,
                          modules=modules,
                          quizzes=quizzes,
                          edit_mode=True,
                          wizard_title='Course Setup - Step 2: Add Modules',
                          step=2,
                          progress_percentage=50)

# Course Wizard Step 2 - Proceed to next step
@app.route('/admin/course-wizard/step2/<int:course_id>/next', methods=['POST'])
@login_required
def admin_course_wizard_step2_next(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    modules = get_course_modules(course_id, module_db)
    if not modules:
        flash('Please add at least one module before proceeding', 'warning')
        return redirect(url_for('admin_course_wizard_step2', course_id=course_id))
    
    return redirect(url_for('admin_course_wizard_step3', course_id=course_id))

# Course Wizard Step 3 - Quizzes
@app.route('/admin/course-wizard/step3/<int:course_id>', methods=['GET'])
@login_required
def admin_course_wizard_step3(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    modules = get_course_modules(course_id, module_db)
    quizzes = list(quiz_db.values())
    questions = list(question_db.values())
    
    return render_template('admin/course_wizard_step3.html',
                          course=course,
                          modules=modules,
                          quizzes=quizzes,
                          questions=questions,
                          edit_mode=True,
                          wizard_title='Course Setup - Step 3: Create Quizzes',
                          step=3,
                          progress_percentage=75)

# Course Wizard Step 3 - Proceed to next step
@app.route('/admin/course-wizard/step3/<int:course_id>/next', methods=['POST'])
@login_required
def admin_course_wizard_step3_next(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    return redirect(url_for('admin_course_wizard_step4', course_id=course_id))

# Course Wizard Step 4 - Certificate
@app.route('/admin/course-wizard/step4/<int:course_id>', methods=['GET'])
@login_required
def admin_course_wizard_step4(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    return render_template('admin/course_wizard_step4.html',
                          course=course,
                          edit_mode=True,
                          wizard_title='Course Setup - Step 4: Certificate',
                          step=4,
                          progress_percentage=100)

# Course Wizard Step 4 - Complete
@app.route('/admin/course-wizard/step4/<int:course_id>/complete', methods=['POST'])
@login_required
def admin_course_wizard_step4_complete(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    # Store certificate settings in session for now
    # In a real app, you would store these in the database
    session['certificate_settings'] = {
        'course_id': course_id,
        'certificate_title': request.form.get('certificate_title', 'Certificate of Completion'),
        'custom_message': request.form.get('custom_message', ''),
        'include_date': 'include_date' in request.form,
        'include_signatures': 'include_signatures' in request.form,
        'include_logo': 'include_logo' in request.form,
        'completion_threshold': request.form.get('completion_threshold', 100),
        'require_quiz_passing': 'require_quiz_passing' in request.form
    }
    
    flash('Course setup completed successfully!', 'success')
    return redirect(url_for('admin_course_edit', course_id=course_id))