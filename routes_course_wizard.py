from flask import render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import os
import json
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
    
    try:
        # Fetch fresh data directly from the database to avoid detached instances
        with app.app_context():
            # Get course from database
            course = Course.query.get(course_id)
            if not course:
                flash('Course not found', 'error')
                return redirect(url_for('admin_courses'))
            
            # Update in-memory course
            course_db[course_id] = course
            
            # Get modules from database
            db_modules = list(Module.query.filter_by(course_id=course_id).order_by(Module.order).all())
            
            # Update in-memory modules
            for module in db_modules:
                module_db[module.id] = module
            
            # Get module IDs for quiz lookup
            module_ids = [m.id for m in db_modules]
            
            # Get quizzes for these modules
            db_quizzes = list(Quiz.query.filter(Quiz.module_id.in_(module_ids)).all()) if module_ids else []
            
            # Update in-memory quizzes
            for quiz in db_quizzes:
                quiz_db[quiz.id] = quiz
                
            # Get questions for these quizzes
            quiz_ids = [q.id for q in db_quizzes]
            if quiz_ids:
                db_questions = list(QuizQuestion.query.filter(QuizQuestion.quiz_id.in_(quiz_ids)).all())
                for question in db_questions:
                    question_db[question.id] = question
            
            # Use the updated in-memory data
            modules = db_modules
            quizzes = db_quizzes
            
            app.logger.debug(f"Refreshed data for course {course_id}: {len(modules)} modules, {len(quizzes)} quizzes")
    
    except Exception as e:
        app.logger.error(f"Error refreshing data: {str(e)}")
        # Fallback to in-memory data if refresh fails
        course = course_db.get(course_id)
        if not course:
            flash('Course not found', 'error')
            return redirect(url_for('admin_courses'))
        
        modules = get_course_modules(course_id, module_db)
        quizzes = list(quiz_db.values())
    
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
@app.route('/admin/course-wizard/step3/<int:course_id>', methods=['GET', 'POST'])
@login_required
def admin_course_wizard_step3(course_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if question_added parameter is passed
    question_added = request.args.get('question_added', False)
    quiz_added = request.args.get('quiz_added', False)
    
    try:
        # Fetch fresh data directly from the database to avoid detached instances
        with app.app_context():
            # Get course from database
            course = Course.query.get(course_id)
            if not course:
                flash('Course not found', 'error')
                return redirect(url_for('admin_courses'))
            
            # Update in-memory course
            course_db[course_id] = course
            
            # Get modules from database
            db_modules = list(Module.query.filter_by(course_id=course_id).order_by(Module.order).all())
            
            # Update in-memory modules
            for module in db_modules:
                module_db[module.id] = module
            
            # Get module IDs for quiz lookup
            module_ids = [m.id for m in db_modules]
            
            # Get quizzes for these modules
            db_quizzes = list(Quiz.query.filter(Quiz.module_id.in_(module_ids)).all()) if module_ids else []
            
            # Update in-memory quizzes
            for quiz in db_quizzes:
                quiz_db[quiz.id] = quiz
                
            # Get quiz IDs for question lookup
            quiz_ids = [q.id for q in db_quizzes]
            
            # Get questions for these quizzes
            db_questions = list(QuizQuestion.query.filter(QuizQuestion.quiz_id.in_(quiz_ids)).all()) if quiz_ids else []
            
            # Update in-memory questions
            for question in db_questions:
                question_db[question.id] = question
            
            # Use the refreshed data
            modules = db_modules
            quizzes = db_quizzes
            questions = db_questions
            
            # Add debug logging
            app.logger.debug(f"Loading course wizard step 3 for course {course_id}")
            app.logger.debug(f"Found {len(modules)} modules, {len(quizzes)} quizzes, {len(questions)} questions")
            
    except Exception as e:
        app.logger.error(f"Error refreshing data: {str(e)}")
        # Fallback to in-memory data if refresh fails
        course = course_db.get(course_id)
        if not course:
            flash('Course not found', 'error')
            return redirect(url_for('admin_courses'))
        
        modules = get_course_modules(course_id, module_db)
        quizzes = list(quiz_db.values())
        questions = list(question_db.values())
    
    # Handle POST request to create new quiz
    if request.method == 'POST':
        module_id = request.form.get('module_id')
        title = request.form.get('title')
        description = request.form.get('description')
        passing_score = request.form.get('passing_score')
        
        # Validate required fields
        if not module_id or not title or not description or not passing_score:
            flash('All fields are required', 'error')
            return redirect(url_for('admin_course_wizard_step3', course_id=course_id))
        
        try:
            module_id = int(module_id)
            passing_score = int(passing_score)
        except ValueError:
            flash('Invalid module ID or passing score', 'error')
            return redirect(url_for('admin_course_wizard_step3', course_id=course_id))
        
        # Validate module
        module = module_db.get(module_id)
        if not module or module.course_id != course_id:
            flash('Invalid module selected', 'error')
            return redirect(url_for('admin_course_wizard_step3', course_id=course_id))
        
        try:
            # Work within a session context to avoid detached instance errors
            with app.app_context():
                # Check if module already has a quiz - use the database directly
                existing_quiz = Quiz.query.filter_by(module_id=module_id).first()
                    
                if existing_quiz:
                    # Update existing quiz in the database
                    existing_quiz.title = title
                    existing_quiz.description = description
                    existing_quiz.passing_score = passing_score
                    existing_quiz.updated_at = datetime.now()
                    
                    # Also update in-memory
                    memory_quiz = quiz_db.get(existing_quiz.id)
                    if memory_quiz:
                        memory_quiz.title = title
                        memory_quiz.description = description
                        memory_quiz.passing_score = passing_score
                        memory_quiz.updated_at = datetime.now()
                    
                    flash('Existing quiz updated successfully', 'success')
                else:
                    # Create new quiz in the database
                    new_quiz = Quiz(
                        module_id=module_id,
                        title=title,
                        description=description,
                        passing_score=passing_score,
                        created_at=datetime.now()
                    )
                    db.session.add(new_quiz)
                    db.session.flush()  # Get the ID without committing
                    
                    # Also create in in-memory DB
                    quiz_db[new_quiz.id] = new_quiz
                    flash('Quiz created successfully', 'success')
                
                db.session.commit()
                
            # After the transaction is complete, fetch fresh data for the view
            return redirect(url_for('admin_course_wizard_step3', course_id=course_id, quiz_added=True))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating quiz: {str(e)}")
            flash(f'Error creating quiz: {str(e)}', 'error')
    
    # Use our newly created course_wizard_step3.html template with working accordion
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
    
    try:
        # Work within the app context to avoid detached instance errors
        with app.app_context():
            if edit_mode:
                # Get fresh quiz data from database
                quiz = Quiz.query.get(quiz_id)
                if not quiz:
                    flash('Quiz not found', 'error')
                    return redirect(url_for('admin_courses'))
                
                # Update in-memory quiz
                quiz_db[quiz.id] = quiz
                
                module_id = quiz.module_id
                # Get fresh module data
                module = Module.query.get(module_id)
                if module:
                    module_db[module.id] = module
            else:
                # Get fresh module data
                module = Module.query.get(module_id)
                if not module:
                    flash('Module not found', 'error')
                    return redirect(url_for('admin_courses'))
                
                # Update in-memory module
                module_db[module.id] = module
                
                # Check if a quiz already exists for this module - use database
                existing_quiz = Quiz.query.filter_by(module_id=module_id).first()
                if existing_quiz:
                    # Update in-memory
                    quiz_db[existing_quiz.id] = existing_quiz
                    flash('A quiz already exists for this module', 'info')
                    return redirect(url_for('admin_quiz_wizard', quiz_id=existing_quiz.id))
            
            # Get fresh course data
            course = Course.query.get(module.course_id)
            if not course:
                flash('Course not found', 'error')
                return redirect(url_for('admin_courses'))
            
            # Update in-memory course
            course_db[course.id] = course
            
            # Get questions for this quiz - from database
            questions = []
            if edit_mode:
                questions = list(QuizQuestion.query.filter_by(quiz_id=quiz_id).order_by(QuizQuestion.order).all())
                
                # Update in-memory questions
                for question in questions:
                    question_db[question.id] = question
            
    except Exception as e:
        app.logger.error(f"Error getting fresh data: {str(e)}")
        # Fallback to in-memory data
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
    
# New Quiz Management Endpoints

# Delete a quiz and its associated questions
@app.route('/admin/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
def admin_quiz_delete(quiz_id):
    """Delete a quiz and all its associated questions"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_courses'))
    
    # Get module and course info for redirecting back to step 3
    module = module_db.get(quiz.module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
    
    course_id = module.course_id
    
    # First, delete all questions associated with this quiz
    questions_to_delete = [q_id for q_id, q in question_db.items() if q.quiz_id == quiz_id]
    
    try:
        # Delete from database first
        with app.app_context():
            # Delete associated questions
            for question_id in questions_to_delete:
                db_question = QuizQuestion.query.get(question_id)
                if db_question:
                    app.logger.debug(f"Deleting question ID: {question_id} from database")
                    db.session.delete(db_question)
            
            # Delete the quiz
            db_quiz = Quiz.query.get(quiz_id)
            if db_quiz:
                app.logger.debug(f"Deleting quiz ID: {quiz_id} from database")
                db.session.delete(db_quiz)
                
            # Commit all changes
            db.session.commit()
            
            # Delete from in-memory databases
            for question_id in questions_to_delete:
                if question_id in question_db:
                    app.logger.debug(f"Deleting question ID: {question_id} from memory")
                    del question_db[question_id]
            
            if quiz_id in quiz_db:
                app.logger.debug(f"Deleting quiz ID: {quiz_id} from memory")
                del quiz_db[quiz_id]
                
            flash('Quiz and associated questions deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting quiz: {str(e)}")
        flash(f'Error deleting quiz: {str(e)}', 'error')
    
    # Redirect back to the course wizard step 3
    return redirect(url_for('admin_course_wizard_step3', course_id=course_id))

# Get questions for a quiz in JSON format
# Direct edit quiz route from accordion
@app.route('/admin/quiz/<int:quiz_id>/edit', methods=['POST'])
@login_required
def admin_quiz_edit_direct(quiz_id):
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Get course ID from form
    course_id = request.form.get('course_id', None)
    if not course_id:
        flash('Course ID is required', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Convert course_id to integer
    try:
        course_id = int(course_id)
    except ValueError:
        flash('Invalid course ID', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Check if the course exists
    course = course_db.get(course_id)
    if not course:
        flash('Course not found', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Get form data
    module_id = request.form.get('module_id')
    title = request.form.get('title')
    description = request.form.get('description')
    passing_score = request.form.get('passing_score')
    
    # Validate form data
    if not all([module_id, title, description, passing_score]):
        flash('All fields are required', 'error')
        return redirect(url_for('admin_course_wizard_step3', course_id=course_id))
    
    # Convert module_id and passing_score to appropriate types
    try:
        module_id = int(module_id)
        passing_score = int(passing_score)
    except ValueError:
        flash('Invalid module ID or passing score', 'error')
        return redirect(url_for('admin_course_wizard_step3', course_id=course_id))
    
    # Check if module exists and belongs to the course
    module = None
    for m in module_db.values():
        if m.id == module_id and m.course_id == course_id:
            module = m
            break
    
    if not module:
        flash('Module not found or does not belong to this course', 'error')
        return redirect(url_for('admin_course_wizard_step3', course_id=course_id))
    
    # Check if switching to a module that already has a quiz (other than this one)
    if module_id != quiz.module_id:
        for q in quiz_db.values():
            if q.module_id == module_id and q.id != quiz_id:
                flash(f'Module already has a quiz. Please choose a different module or edit that quiz instead.', 'warning')
                return redirect(url_for('admin_course_wizard_step3', course_id=course_id))
    
    # Update quiz
    quiz.module_id = module_id
    quiz.title = title
    quiz.description = description
    quiz.passing_score = passing_score
    quiz.updated_at = datetime.now()
    
    flash('Quiz updated successfully', 'success')
    return redirect(url_for('admin_course_wizard_step3', course_id=course_id))

@app.route('/admin/quiz/<int:quiz_id>/questions-json', methods=['GET'])
@login_required
def admin_quiz_questions_json(quiz_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    # Get all questions for this quiz
    questions = [q for q in question_db.values() if q.quiz_id == quiz_id]
    questions.sort(key=lambda q: q.order)
    
    # Convert to JSON
    questions_json = []
    for q in questions:
        questions_json.append({
            'id': q.id,
            'quiz_id': q.quiz_id,
            'question': q.question,
            'options': q.get_options(),
            'correct_answer': q.correct_answer,
            'order': q.order
        })
    
    return jsonify({
        'success': True,
        'quiz_id': quiz_id,
        'questions': questions_json
    })

# Create new quiz
@app.route('/admin/quiz/new-json', methods=['POST'])
@login_required
def admin_quiz_new_json():
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    # Get form data
    module_id = request.form.get('module_id')
    course_id = request.form.get('course_id')
    
    if not module_id or not module_id.isdigit():
        return jsonify({'error': 'Invalid module ID'}), 400
    
    module_id = int(module_id)
    module = module_db.get(module_id)
    
    if not module:
        return jsonify({'error': 'Module not found'}), 404
    
    # Check if this module already has a quiz
    existing_quiz = None
    for q in quiz_db.values():
        if q.module_id == module_id:
            existing_quiz = q
            break
    
    if existing_quiz:
        # If there's an existing quiz, we'll just update it
        quiz_id = existing_quiz.id
        quiz = existing_quiz
        quiz.title = request.form.get('title')
        quiz.description = request.form.get('description')
        quiz.passing_score = int(request.form.get('passing_score', 70))
        quiz.updated_at = datetime.now()
    else:
        # Create new quiz
        quiz_id = get_next_id(quiz_db)
        quiz = Quiz(
            id=quiz_id,
            module_id=module_id,
            title=request.form.get('title'),
            description=request.form.get('description'),
            passing_score=int(request.form.get('passing_score', 70)),
            created_at=datetime.now()
        )
        quiz_db[quiz_id] = quiz
        
        # Add to database
        db.session.add(quiz)
    
    try:
        db.session.commit()
        
        # Refresh quiz data
        from models import refresh_quizzes
        refresh_quizzes()
        
        return jsonify({
            'success': True,
            'message': 'Quiz saved successfully',
            'quiz_id': quiz_id,
            'is_new': not existing_quiz,
            'module_id': module_id,
            'course_id': course_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Error saving quiz: {str(e)}'
        }), 500

# Edit existing quiz
@app.route('/admin/quiz/<int:quiz_id>/edit-json', methods=['POST'])
@login_required
def admin_quiz_edit_json(quiz_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    # Get module and course
    module = module_db.get(quiz.module_id)
    if not module:
        return jsonify({'error': 'Module not found'}), 404
    
    course = course_db.get(module.course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Update quiz
    quiz.title = request.form.get('title')
    quiz.description = request.form.get('description')
    quiz.passing_score = int(request.form.get('passing_score', 70))
    quiz.updated_at = datetime.now()
    
    try:
        db.session.commit()
        
        # Refresh quiz data
        from models import refresh_quizzes
        refresh_quizzes()
        
        return jsonify({
            'success': True,
            'message': 'Quiz updated successfully',
            'quiz_id': quiz_id,
            'module_id': quiz.module_id,
            'course_id': module.course_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Error updating quiz: {str(e)}'
        }), 500

# Question Management Page with Return to Step 3
@app.route('/admin/quiz/<int:quiz_id>/questions', methods=['GET'])
@login_required
def admin_manage_questions(quiz_id):
    """Dedicated page for managing quiz questions with return to step 3."""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_courses'))
    
    # Get module and course for navigation
    module = module_db.get(quiz.module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
    
    course_id = module.course_id
    course = course_db.get(course_id)
    
    # Get questions for this quiz, sorted by order
    questions = [q for q in question_db.values() if q.quiz_id == quiz_id]
    questions.sort(key=lambda x: x.order)
    
    # Add a debug panel to verify data
    app.logger.debug(f"Quiz ID: {quiz_id}, Title: {quiz.title}")
    app.logger.debug(f"Found {len(questions)} questions")
    
    return render_template(
        'admin/question_management.html',
        quiz=quiz,
        module=module,
        course=course,
        questions=questions
    )

# Add question to quiz
@app.route('/admin/quiz/<int:quiz_id>/question/add', methods=['GET', 'POST'])
@login_required
def admin_add_question(quiz_id):
    """Add a question to a quiz with redirect back to question management page."""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_courses'))
    
    # Get module and course for navigation
    module = module_db.get(quiz.module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
    
    course_id = module.course_id
    
    # Determine the next order for this quiz
    existing_questions = [q for q in question_db.values() if q.quiz_id == quiz_id]
    next_order = 1
    if existing_questions:
        next_order = max([q.order for q in existing_questions]) + 1
    
    app.logger.debug(f"Next order number for quiz {quiz_id}: {next_order}")
    
    if request.method == 'POST':
        app.logger.debug(f"Processing POST request to add question to quiz {quiz_id}")
        app.logger.debug(f"Form data: {request.form.to_dict()}")
        
        # Explicitly get form data
        question_text = request.form.get('question')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        correct_answer = int(request.form.get('correct_answer', 0))
        order = int(request.form.get('order', next_order))
        
        app.logger.debug(f"Extracted data - question: {question_text}, options: [{option1}, {option2}, {option3}, {option4}], correct: {correct_answer}, order: {order}")
        
        # Create the question
        options = [option1, option2]
        if option3 and option3.strip():
            options.append(option3)
        if option4 and option4.strip():
            options.append(option4)
        
        # Generate new ID for question
        question_id = get_next_id(question_db)
        app.logger.debug(f"Generated new question ID: {question_id}")
        
        try:
            # Create and add to database first
            with app.app_context():
                db_question = QuizQuestion(
                    id=question_id,
                    quiz_id=quiz_id,
                    question=question_text,
                    options=json.dumps(options),
                    correct_answer=correct_answer,
                    order=order,
                    created_at=datetime.now()
                )
                db.session.add(db_question)
                db.session.commit()
                app.logger.debug(f"Question {question_id} added to database")
            
            # Then add to in-memory dictionary
            question_db[question_id] = db_question
            app.logger.debug(f"Question {question_id} added to in-memory dictionary")
            
            flash('Question added successfully', 'success')
            
            # Use absolute URL for redirection
            redirect_url = f"/admin/quiz/{quiz_id}/questions"
            app.logger.debug(f"Redirecting to: {redirect_url}")
            return redirect(redirect_url)
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding question: {str(e)}")
            flash(f'Error adding question: {str(e)}', 'error')
    
    return render_template(
        'admin/add_question.html',
        quiz=quiz,
        module=module,
        course_id=course_id,
        next_order=next_order
    )

# Edit question
@app.route('/admin/question/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_question(question_id):
    """Edit a question with redirect back to question management page."""
    app.logger.debug(f"🔴 EDIT QUESTION HANDLER CALLED with question_id={question_id}, method={request.method}, referrer={request.referrer}")
    app.logger.debug(f"🔴 Request headers: {dict(request.headers)}")
    
    if request.method == 'POST':
        app.logger.debug(f"🔴 POST request received with data: {request.form.to_dict()}")
    
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    app.logger.debug(f"Editing question ID: {question_id}")
    
    # Try to get fresh data from database first, then fall back to in-memory if needed
    try:
        with app.app_context():
            # Get the question from the database
            db_question = QuizQuestion.query.get(question_id)
            if db_question:
                # Update in-memory
                question_db[question_id] = db_question
                question = db_question
                app.logger.debug(f"Retrieved question from database: {question.question}")
            else:
                # Fall back to in-memory
                question = question_db.get(question_id)
                app.logger.debug(f"Using in-memory question: {question.question if question else 'Not found'}")
    except Exception as e:
        app.logger.error(f"Error getting fresh question data: {str(e)}")
        # Fall back to in-memory
        question = question_db.get(question_id)
        app.logger.debug(f"Exception - Using in-memory question: {question.question if question else 'Not found'}")
    
    if not question:
        flash('Question not found', 'error')
        return redirect(url_for('admin_courses'))
    
    quiz_id = question.quiz_id
    app.logger.debug(f"Question belongs to quiz ID: {quiz_id}")
    
    # Try to get fresh quiz data
    try:
        with app.app_context():
            db_quiz = Quiz.query.get(quiz_id)
            if db_quiz:
                # Update in-memory
                quiz_db[quiz_id] = db_quiz
                quiz = db_quiz
                app.logger.debug(f"Retrieved quiz from database: {quiz.title}")
            else:
                # Fall back to in-memory
                quiz = quiz_db.get(quiz_id)
                app.logger.debug(f"Using in-memory quiz: {quiz.title if quiz else 'Not found'}")
    except Exception as e:
        app.logger.error(f"Error getting fresh quiz data: {str(e)}")
        # Fall back to in-memory
        quiz = quiz_db.get(quiz_id)
        app.logger.debug(f"Exception - Using in-memory quiz: {quiz.title if quiz else 'Not found'}")
    
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_courses'))
    
    # Get module and course for navigation
    module_id = quiz.module_id
    app.logger.debug(f"Quiz belongs to module ID: {module_id}")
    
    # Try to get fresh module data
    try:
        with app.app_context():
            db_module = Module.query.get(module_id)
            if db_module:
                # Update in-memory
                module_db[module_id] = db_module
                module = db_module
                app.logger.debug(f"Retrieved module from database: {module.title}")
            else:
                # Fall back to in-memory
                module = module_db.get(module_id)
                app.logger.debug(f"Using in-memory module: {module.title if module else 'Not found'}")
    except Exception as e:
        app.logger.error(f"Error getting fresh module data: {str(e)}")
        # Fall back to in-memory
        module = module_db.get(module_id)
        app.logger.debug(f"Exception - Using in-memory module: {module.title if module else 'Not found'}")
    
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
    
    course_id = module.course_id
    app.logger.debug(f"Module belongs to course ID: {course_id}")
    
    # Get the options directly from database to ensure we have the latest
    try:
        with app.app_context():
            db_question = QuizQuestion.query.get(question_id)
            if db_question and db_question.options:
                try:
                    options = json.loads(db_question.options)
                    app.logger.debug(f"Retrieved options from database: {options}")
                except Exception as json_error:
                    app.logger.error(f"Error parsing options JSON: {str(json_error)}")
                    options = question.get_options()
                    app.logger.debug(f"Fallback to in-memory options after JSON error: {options}")
            else:
                options = question.get_options()
                app.logger.debug(f"Using in-memory options: {options}")
    except Exception as e:
        app.logger.error(f"Error getting options from database: {str(e)}")
        options = question.get_options()
        app.logger.debug(f"Exception - Using in-memory options: {options}")
    
    app.logger.debug(f"Options for question: {options}")
    app.logger.debug(f"🟢 OPTIONS DATA TYPE: {type(options)}")
    app.logger.debug(f"🟢 OPTIONS CONTENT: {options}")
    
    if request.method == 'POST':
        app.logger.debug(f"Received POST data: {request.form.to_dict()}")
        
        # Explicitly get form data
        question_text = request.form.get('question')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        correct_answer = int(request.form.get('correct_answer', 0))
        quiz_id = int(request.form.get('quiz_id', quiz_id))
        order = int(request.form.get('order', 1))  # Use the order from the form, default to 1
        
        app.logger.debug(f"POST data - question: {question_text}, options: {option1}, {option2}, {option3}, {option4}, correct: {correct_answer}, quiz_id: {quiz_id}")
        
        # Create new options list - make sure we handle empty strings properly
        new_options = [option1, option2]
        if option3 and option3.strip():
            new_options.append(option3)
        if option4 and option4.strip():
            new_options.append(option4)
        
        app.logger.debug(f"New options list: {new_options}")
        
        # Track update success
        update_success = False
        
        try:
            # Update database first
            db_question = None
            with app.app_context():
                # Force a session refresh to avoid detached instance errors
                db.session.expire_all()
                
                db_question = QuizQuestion.query.get(question_id)
                app.logger.debug(f"Retrieved question from DB for update: {db_question.question if db_question else 'Not found'}")
                
                if db_question:
                    # Update the database object
                    db_question.question = question_text
                    db_question.correct_answer = correct_answer
                    db_question.options = json.dumps(new_options)
                    db_question.order = order  # Update the order field
                    
                    # Commit the changes
                    db.session.commit()
                    app.logger.debug(f"Question {question_id} updated in database")
                    update_success = True
                else:
                    app.logger.warning(f"Question {question_id} not found in database for update")
                    
                    # Try to create it if not found
                    try:
                        app.logger.debug(f"Attempting to create question {question_id} as it was not found")
                        new_question = QuizQuestion(
                            id=question_id,
                            quiz_id=quiz_id,
                            question=question_text,
                            correct_answer=correct_answer,
                            options=json.dumps(new_options),
                            order=order,  # Use the provided order
                            created_at=datetime.now()
                        )
                        db.session.add(new_question)
                        db.session.commit()
                        app.logger.debug(f"Created new question {question_id} in database")
                        update_success = True
                    except Exception as create_error:
                        app.logger.error(f"Error creating question: {str(create_error)}")
                        db.session.rollback()
            
            # Update in-memory after successful database update
            if update_success:
                # Get a fresh copy from the database
                with app.app_context():
                    db_question = QuizQuestion.query.get(question_id)
                    if db_question:
                        # Update in-memory
                        question_db[question_id] = db_question
                        app.logger.debug(f"Updated in-memory question with DB data")
                    else:
                        # Fallback to direct update if DB query fails
                        if question_id in question_db:
                            question = question_db[question_id]
                            question.question = question_text
                            question.correct_answer = correct_answer
                            question.order = order  # Update order in memory
                            question.set_options(new_options)
                            app.logger.debug(f"Question {question_id} updated in memory directly")
                
                flash('Question updated successfully', 'success')
            else:
                flash('Warning: Question not updated in database. Please retry.', 'warning')
                
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating question: {str(e)}")
            flash(f'Error updating question: {str(e)}', 'error')
        
        # Redirect to the question management page for this quiz
        # Use absolute URL to avoid issues with relative redirection
        redirect_url = f"/admin/quiz/{quiz_id}/questions"
        app.logger.debug(f"Redirecting to: {redirect_url}")
        return redirect(redirect_url)
    
    app.logger.debug(f"Rendering edit_question.html with question={question_id}, quiz={quiz_id}, options={options}")
    
    # Create a form instance for CSRF token
    form = QuestionForm()
    
    return render_template(
        'admin/edit_question.html',
        form=form,
        question=question,
        quiz=quiz,
        module=module,
        course_id=course_id,
        options=options
    )

# Delete question with redirect
@app.route('/admin/question/<int:question_id>/delete', methods=['POST'])
@login_required
def admin_delete_question(question_id):
    """Delete a question with redirect back to question management page."""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    question = question_db.get(question_id)
    if not question:
        flash('Question not found', 'error')
        return redirect(url_for('admin_courses'))
    
    quiz_id = question.quiz_id
    
    # Get module and course info for redirecting back to step 3
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_courses'))
    
    module = module_db.get(quiz.module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
    
    course_id = module.course_id
    
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
    
    # Use absolute URL for redirection
    redirect_url = f"/admin/quiz/{quiz_id}/questions"
    app.logger.debug(f"Redirecting to: {redirect_url}")
    return redirect(redirect_url)

# Add new question to quiz
@app.route('/admin/quiz/<int:quiz_id>/question/new-json', methods=['POST'])
@login_required
def admin_question_new_json(quiz_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        return jsonify({'error': 'Quiz not found'}), 404
    
    # Get form data
    form = QuestionForm(request.form)
    
    if form.validate():
        # Create new question
        question_id = get_next_id(question_db)
        
        # Extract options, only include non-empty ones
        options = []
        if form.option1.data:
            options.append(form.option1.data)
        if form.option2.data:
            options.append(form.option2.data)
        if form.option3.data and form.option3.data.strip():
            options.append(form.option3.data)
        if form.option4.data and form.option4.data.strip():
            options.append(form.option4.data)
        
        # Create question instance
        question = QuizQuestion(
            id=question_id,
            quiz_id=quiz_id,
            question=form.question.data,
            correct_answer=int(form.correct_answer.data),
            order=form.order.data
        )
        
        # Set options
        question.set_options(options)
        
        # Add to in-memory dictionary
        question_db[question_id] = question
        
        # Add to database
        db.session.add(question)
        
        try:
            db.session.commit()
            
            # Get the next order number for a new question
            next_order = max([q.order for q in question_db.values() if q.quiz_id == quiz_id], default=0) + 1
            
            # Return success response with the created question
            return jsonify({
                'success': True,
                'message': 'Question added successfully',
                'question': {
                    'id': question_id,
                    'quiz_id': quiz_id,
                    'question': question.question,
                    'options': question.get_options(),
                    'correct_answer': question.correct_answer,
                    'order': question.order
                },
                'next_order': next_order
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'error': f'Error adding question: {str(e)}'
            }), 500
    else:
        return jsonify({
            'error': 'Invalid form data',
            'form_errors': form.errors
        }), 400

# Special route for redirected standard question edit
@app.route('/admin/question/<int:question_id>/edit-wizard', methods=['GET', 'POST'])
@login_required
def admin_question_edit_wizard(question_id):
    """Handle redirects from the old standalone question editor to the wizard version."""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    app.logger.debug(f"Processing edit-wizard request for question {question_id}")
    
    question = question_db.get(question_id)
    if not question:
        flash('Question not found', 'error')
        return redirect(url_for('admin_courses'))
    
    quiz_id = question.quiz_id
    
    # Get module and course info for redirecting back to step 3
    quiz = quiz_db.get(quiz_id)
    if not quiz:
        flash('Quiz not found', 'error')
        return redirect(url_for('admin_courses'))
    
    module = module_db.get(quiz.module_id)
    if not module:
        flash('Module not found', 'error')
        return redirect(url_for('admin_courses'))
    
    course_id = module.course_id
    
    app.logger.debug(f"Retrieving options for question {question_id}")
    
    # Get the options directly from database to ensure we have the latest
    try:
        with app.app_context():
            db_question = QuizQuestion.query.get(question_id)
            if db_question and db_question.options:
                try:
                    options = json.loads(db_question.options)
                    app.logger.debug(f"Retrieved options from database: {options}")
                except Exception as json_error:
                    app.logger.error(f"Error parsing options JSON: {str(json_error)}")
                    options = question.get_options()
                    app.logger.debug(f"Fallback to in-memory options after JSON error: {options}")
            else:
                options = question.get_options()
                app.logger.debug(f"Using in-memory options: {options}")
    except Exception as e:
        app.logger.error(f"Error getting options from database: {str(e)}")
        options = question.get_options()
        app.logger.debug(f"Exception - Using in-memory options: {options}")
    
    app.logger.debug(f"Options for question: {options}")
    app.logger.debug(f"🟢 OPTIONS DATA TYPE: {type(options)}")
    app.logger.debug(f"🟢 OPTIONS CONTENT: {options}")
    
    # Create a form instance for CSRF token
    form = QuestionForm()
    
    # Process form submission
    if request.method == 'POST':
        app.logger.debug(f"Received POST data: {request.form.to_dict()}")
        
        # Explicitly get form data
        question_text = request.form.get('question')
        option1 = request.form.get('option1')
        option2 = request.form.get('option2')
        option3 = request.form.get('option3')
        option4 = request.form.get('option4')
        correct_answer = int(request.form.get('correct_answer', 0))
        quiz_id = int(request.form.get('quiz_id', quiz_id))
        order = int(request.form.get('order', 1))  # Use the order from the form, default to 1
        
        app.logger.debug(f"POST data - question: {question_text}, options: {option1}, {option2}, {option3}, {option4}, correct: {correct_answer}, quiz_id: {quiz_id}")
        
        # Create new options list - make sure we handle empty strings properly
        new_options = [option1, option2]
        if option3 and option3.strip():
            new_options.append(option3)
        if option4 and option4.strip():
            new_options.append(option4)
        
        app.logger.debug(f"New options list: {new_options}")
        
        # Track update success
        update_success = False
        
        try:
            # Update database first
            db_question = None
            with app.app_context():
                # Force a session refresh to avoid detached instance errors
                db.session.expire_all()
                
                db_question = QuizQuestion.query.get(question_id)
                app.logger.debug(f"Retrieved question from DB for update: {db_question.question if db_question else 'Not found'}")
                
                if db_question:
                    # Update the database object
                    db_question.question = question_text
                    db_question.correct_answer = correct_answer
                    db_question.options = json.dumps(new_options)
                    db_question.order = order  # Update the order field
                    
                    # Commit the changes
                    db.session.commit()
                    app.logger.debug(f"Question {question_id} updated in database")
                    update_success = True
                else:
                    app.logger.warning(f"Question {question_id} not found in database for update")
                    
                    # Try to create it if not found
                    try:
                        app.logger.debug(f"Attempting to create question {question_id} as it was not found")
                        new_question = QuizQuestion(
                            id=question_id,
                            quiz_id=quiz_id,
                            question=question_text,
                            correct_answer=correct_answer,
                            options=json.dumps(new_options),
                            order=order,  # Use the provided order
                            created_at=datetime.now()
                        )
                        db.session.add(new_question)
                        db.session.commit()
                        app.logger.debug(f"Created new question {question_id} in database")
                        update_success = True
                    except Exception as create_error:
                        app.logger.error(f"Error creating question: {str(create_error)}")
                        db.session.rollback()
            
            # Update in-memory after successful database update
            if update_success:
                # Get a fresh copy from the database
                with app.app_context():
                    db_question = QuizQuestion.query.get(question_id)
                    if db_question:
                        # Update in-memory
                        question_db[question_id] = db_question
                        app.logger.debug(f"Updated in-memory question with DB data")
                    else:
                        # Fallback to direct update if DB query fails
                        if question_id in question_db:
                            question = question_db[question_id]
                            question.question = question_text
                            question.correct_answer = correct_answer
                            question.order = order  # Update order in memory
                            question.set_options(new_options)
                            app.logger.debug(f"Question {question_id} updated in memory directly")
                
                flash('Question updated successfully', 'success')
                # Redirect to the question management page for this quiz
                return redirect(f"/admin/quiz/{quiz_id}/questions")
            else:
                flash('Warning: Question not updated in database. Please retry.', 'warning')
                
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating question: {str(e)}")
            flash(f'Error updating question: {str(e)}', 'error')
    
    app.logger.debug(f"Rendering edit_question.html directly from edit-wizard route")
    
    return render_template(
        'admin/edit_question.html',
        form=form,
        question=question,
        quiz=quiz,
        module=module,
        course_id=course_id,
        options=options
    )

# Delete a question via AJAX
@app.route('/admin/question/<int:question_id>/delete-ajax', methods=['POST'])
@login_required
def admin_question_delete_ajax(question_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    question = question_db.get(question_id)
    if not question:
        return jsonify({'error': 'Question not found'}), 404
    
    # Remove from in-memory dictionary
    quiz_id = question.quiz_id
    del question_db[question_id]
    
    # Remove from database
    db_question = QuizQuestion.query.get(question_id)
    if db_question:
        db.session.delete(db_question)
        
        try:
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Question deleted successfully',
                'quiz_id': quiz_id
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'error': f'Error deleting question: {str(e)}'
            }), 500
    else:
        return jsonify({
            'error': 'Question not found in database'
        }), 404