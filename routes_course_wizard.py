from flask import render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from app import app, db
from forms import CourseForm, ModuleForm, QuizForm, QuestionForm
from models import Course, Module, Quiz, QuizQuestion, course_db, module_db, quiz_db, question_db, populate_in_memory_db
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
            
        # Store in session that we're editing a course
        session['editing_course'] = True
    
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
    
    # Check if question_added parameter is passed
    question_added = request.args.get('question_added', False)
    quiz_added = request.args.get('quiz_added', False)
    
    # Add debug logging
    app.logger.debug(f"Loading course wizard step 3 for course {course_id}")
    app.logger.debug(f"Found {len(modules)} modules, {len(quizzes)} quizzes, {len(questions)} questions")
    
    return render_template('admin/course_wizard_step3.html',
                          course=course,
                          modules=modules,
                          quizzes=quizzes,
                          questions=questions,
                          edit_mode=True,
                          question_added=question_added,
                          quiz_added=quiz_added,
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

# Module Wizard - Create/Edit Module within Wizard
@app.route('/admin/course-wizard/<int:course_id>/module', methods=['GET', 'POST'])
@app.route('/admin/course-wizard/<int:course_id>/module/<int:module_id>', methods=['GET', 'POST'])
@login_required
def admin_module_wizard(course_id, module_id=None):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get course
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    # Determine if we're editing an existing module
    edit_mode = module_id is not None
    module = None
    if edit_mode:
        module = module_db.get(module_id)
        if not module:
            flash('Module not found', 'error')
            return redirect(url_for('admin_course_wizard_step2', course_id=course_id))
        
        # Make sure the module belongs to this course
        if module.course_id != course_id:
            flash('Module does not belong to this course', 'error')
            return redirect(url_for('admin_course_wizard_step2', course_id=course_id))
    
    # Create form
    form = ModuleForm(obj=module if edit_mode else None)
    
    # Set default order for new modules
    if not edit_mode and not form.order.data:
        modules = get_course_modules(course_id, module_db)
        form.order.data = len(modules) + 1
    
    if form.validate_on_submit():
        # Handle file uploads
        video_filename = None
        pdf_filename = None
        
        # Process video file if uploaded
        if form.video_file.data:
            # Create directories if they don't exist
            os.makedirs('uploads/videos', exist_ok=True)
            
            # Generate unique filename
            video_filename = f'module_{module_id if edit_mode else "new"}_{secure_filename(form.video_file.data.filename)}'
            video_path = os.path.join('uploads/videos', video_filename)
            
            # Save file
            form.video_file.data.save(video_path)
            app.logger.info(f"Saved video file: {video_path}")
        
        # Process PDF file if uploaded
        if form.pdf_file.data:
            # Create directories if they don't exist
            os.makedirs('uploads/pdfs', exist_ok=True)
            
            # Generate unique filename
            pdf_filename = f'module_{module_id if edit_mode else "new"}_{secure_filename(form.pdf_file.data.filename)}'
            pdf_path = os.path.join('uploads/pdfs', pdf_filename)
            
            # Save file
            form.pdf_file.data.save(pdf_path)
            app.logger.info(f"Saved PDF file: {pdf_path}")
        
        if edit_mode:
            # Update existing module
            module.title = form.title.data
            module.content = form.content.data
            module.order = form.order.data
            module.video_url = form.video_url.data
            module.pdf_url = form.pdf_url.data
            
            # Only update file paths if new files were uploaded
            if video_filename:
                module.video_file = os.path.join('uploads/videos', video_filename)
            
            if pdf_filename:
                module.pdf_file = os.path.join('uploads/pdfs', pdf_filename)
            
            module.updated_at = datetime.now()
            flash('Module updated successfully', 'success')
        else:
            # Create new module
            module_id = get_next_id(module_db)
            module = Module(
                id=module_id,
                course_id=course_id,
                title=form.title.data,
                content=form.content.data,
                order=form.order.data,
                video_url=form.video_url.data,
                pdf_url=form.pdf_url.data,
                video_file=os.path.join('uploads/videos', video_filename) if video_filename else None,
                pdf_file=os.path.join('uploads/pdfs', pdf_filename) if pdf_filename else None,
                created_at=datetime.now()
            )
            module_db[module_id] = module
            flash('Module created successfully', 'success')
        
        return redirect(url_for('admin_course_wizard_step2', course_id=course_id))
    
    return render_template('admin/module_wizard.html',
                          form=form,
                          course=course,
                          module=module,
                          edit_mode=edit_mode,
                          wizard_title=f'{"Edit" if edit_mode else "Add"} Module',
                          step=2,
                          progress_percentage=50)

# Quiz Wizard - Create/Edit Quiz within Wizard
@app.route('/admin/course-wizard/module/<int:module_id>/quiz', methods=['GET', 'POST'])
@app.route('/admin/course-wizard/quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def admin_quiz_wizard(module_id=None, quiz_id=None):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Determine if we're editing an existing quiz
    edit_mode = quiz_id is not None
    quiz = None
    module = None
    course = None
    
    if edit_mode:
        quiz = quiz_db.get(quiz_id)
        if not quiz:
            flash('Quiz not found', 'error')
            return redirect(url_for('admin_courses'))
        
        module_id = quiz.module_id
        module = module_db.get(module_id)
    else:
        module = module_db.get(module_id)
        if not module:
            flash('Module not found', 'error')
            return redirect(url_for('admin_courses'))
            
        # Check if a quiz already exists for this module
        existing_quiz = next((q for q in quiz_db.values() if q.module_id == module_id), None)
        if existing_quiz:
            flash('A quiz already exists for this module', 'info')
            return redirect(url_for('admin_quiz_wizard', quiz_id=existing_quiz.id))
    
    # Get course
    course = course_db.get(module.course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_courses'))
    
    # Get questions for this quiz
    questions = []
    if edit_mode:
        questions = [q for q in question_db.values() if q.quiz_id == quiz_id]
        questions.sort(key=lambda q: q.order)
    
    # Create form
    form = QuizForm(obj=quiz if edit_mode else None)
    
    # Add extra debugging for quiz creation
    app.logger.debug(f"Quiz wizard: edit_mode={edit_mode}, module_id={module_id}, quiz_id={quiz_id}")
    app.logger.debug(f"Form data: {request.form}")
    
    if form.validate_on_submit():
        app.logger.debug(f"Quiz form is valid, creating/updating quiz")
        if edit_mode:
            # Update existing quiz
            quiz.title = form.title.data
            quiz.description = form.description.data
            quiz.passing_score = form.passing_score.data
            quiz.updated_at = datetime.now()
            flash('Quiz updated successfully', 'success')
        else:
            # Check if this module already has a quiz
            existing_quiz = None
            for q in quiz_db.values():
                if q.module_id == module_id:
                    existing_quiz = q
                    break
                    
            if existing_quiz:
                app.logger.warning(f"Module {module_id} already has quiz {existing_quiz.id}: '{existing_quiz.title}'")
                flash(f'This module already has a quiz: "{existing_quiz.title}". Please edit the existing quiz.', 'warning')
                return redirect(url_for('admin_quiz_wizard', module_id=module_id, quiz_id=existing_quiz.id))
            
            # Create new quiz
            quiz_id = get_next_id(quiz_db)
            app.logger.debug(f"Creating new quiz with ID: {quiz_id} for module: {module_id}")
            
            # Create the quiz object
            new_quiz = Quiz(
                id=quiz_id,
                module_id=module_id,
                title=form.title.data,
                description=form.description.data,
                passing_score=form.passing_score.data,
                created_at=datetime.now()
            )
            
            # Add to both in-memory DB and PostgreSQL
            quiz_db[quiz_id] = new_quiz
            
            # Add to the SQLAlchemy session and commit
            try:
                db.session.add(new_quiz)
                db.session.commit()
                app.logger.debug(f"Quiz created with ID: {quiz_id} and saved to database")
                
                # Add debug info before re-populating in-memory DB
                app.logger.debug(f"Before refresh: quiz_db has {len(quiz_db)} quizzes")
                for qid, q in quiz_db.items():
                    app.logger.debug(f"Quiz ID {qid}, module_id {q.module_id}, title: {q.title}")
                
                # Use the new dedicated refresh function for quizzes
                try:
                    # Ensure the transaction is fully committed
                    db.session.commit()
                    
                    # Refresh the quiz data using the new function
                    from models import refresh_quizzes
                    
                    # Log before refresh
                    app.logger.debug(f"Before refresh: quiz_db has {len(quiz_db)} quizzes")
                    for qid, q in quiz_db.items():
                        app.logger.debug(f"Before: Quiz ID {qid}, module_id {q.module_id}, title: {q.title}")
                    
                    # Perform the refresh
                    refresh_result = refresh_quizzes()
                    
                    # Log after refresh
                    app.logger.debug(f"Refresh result: {refresh_result}")
                    app.logger.debug(f"After refresh: quiz_db has {len(quiz_db)} quizzes")
                    for qid, q in quiz_db.items():
                        app.logger.debug(f"After: Quiz ID {qid}, module_id {q.module_id}, title: {q.title}")
                        
                    # Ensure the new quiz exists in the in-memory DB
                    if quiz_id not in quiz_db:
                        app.logger.warning(f"Quiz ID {quiz_id} not found in quiz_db after refresh. Adding it manually.")
                        quiz_db[quiz_id] = new_quiz
                except Exception as e:
                    app.logger.error(f"Error refreshing in-memory DB: {str(e)}")
                    # Ensure the new quiz is in memory even if refresh failed
                    quiz_db[quiz_id] = new_quiz
                
                flash('Quiz created successfully', 'success')
            except Exception as e:
                db.session.rollback()
                # Try to keep the in-memory DB consistent with what we intended
                if quiz_id in quiz_db:
                    app.logger.warning(f"Removing quiz with ID {quiz_id} from in-memory DB after database error")
                    del quiz_db[quiz_id]
                
                app.logger.error(f"Error creating quiz: {str(e)}")
                flash(f'Error creating quiz: {str(e)}', 'error')
        
        # Check if this is an AJAX request
        is_ajax_request = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax_request:
            # Return JSON response for AJAX requests
            return jsonify({
                'success': True,
                'message': 'Quiz created successfully',
                'quiz_id': quiz_id,
                'module_id': module_id
            })
        else:
            # For regular form submissions, redirect to the same page
            app.logger.debug(f"Redirecting after quiz creation with module_id={module_id} for course_id={course.id}")
            return redirect(url_for('admin_course_wizard_step3', course_id=course.id, module_id=module_id))
    
    return render_template('admin/quiz_wizard.html',
                          form=form,
                          module=module,
                          course=course,
                          quiz=quiz,
                          questions=questions,
                          edit_mode=edit_mode,
                          wizard_title=f'{"Edit" if edit_mode else "New"} Quiz',
                          step=3,
                          progress_percentage=75)

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