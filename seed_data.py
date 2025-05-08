import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

from app import app
from models import User, Course, Module, Quiz, QuizQuestion, db

def seed_data():
    print("Starting database seeding...")
    
    # Get next ID for courses
    max_course_id = db.session.query(db.func.max(Course.id)).scalar() or 0
    next_course_id = max_course_id + 1
    
    # Create additional users if needed
    existing_student_count = db.session.query(User).filter(User.role == 'student').count()
    
    if existing_student_count < 3:
        # Create more student users
        student2 = User(
            username="mjohnson",
            email="mary.johnson@example.com",
            password_hash=generate_password_hash("password123"),
            role="student",
            first_name="Mary",
            last_name="Johnson",
            bio="Experienced nurse practitioner",
            created_at=datetime.now()
        )
        
        student3 = User(
            username="rwilliams",
            email="robert.williams@example.com",
            password_hash=generate_password_hash("password123"),
            role="student",
            first_name="Robert",
            last_name="Williams",
            bio="Medical student interested in neuroscience",
            created_at=datetime.now()
        )
        
        db.session.add_all([student2, student3])
        db.session.flush()
        print("Added additional student users")
    
    # Create additional courses
    neurology_course = Course(
        id=next_course_id,
        title="Neurological Assessment Fundamentals",
        description="Learn the essential techniques for performing accurate neurological assessments. This course provides practical skills for healthcare professionals.",
        category="neurology",
        level="intermediate",
        price=149.99,
        instructor_id=1,  # Admin user ID
        image_url="https://images.unsplash.com/photo-1559757175-5700dde675bc",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    next_course_id += 1
    
    emergency_course = Course(
        id=next_course_id,
        title="Emergency Medicine: Critical Decisions",
        description="Enhance your critical thinking skills for emergency situations. This course uses case-based learning to improve decision-making under pressure.",
        category="emergency",
        level="advanced",
        price=179.99,
        instructor_id=1,  # Admin user ID
        image_url="https://images.unsplash.com/photo-1516574187841-cb9cc2ca948b",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    next_course_id += 1
    
    # Get the next module ID
    max_module_id = db.session.query(db.func.max(Module.id)).scalar() or 0
    next_module_id = max_module_id + 1
    
    # Create modules for existing Cardiology course
    cardio_course_id = 1  # We know this exists
    
    cardio_module2 = Module(
        id=next_module_id,
        course_id=cardio_course_id,
        title="Diagnostic Approaches for Cardiovascular Disease",
        content="<p>This module covers comprehensive approaches to diagnosing heart failure, including:</p><ul><li>Clinical evaluation and history-taking</li><li>Laboratory tests and biomarkers</li><li>Imaging techniques (Echocardiography, MRI, etc.)</li><li>Exercise testing and hemodynamic assessment</li></ul>",
        order=2,
        video_url="https://www.youtube.com/embed/Lp7E973zozc",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    next_module_id += 1
    
    cardio_module3 = Module(
        id=next_module_id,
        course_id=cardio_course_id,
        title="Pharmacological Interventions in Cardiology",
        content="<p>This module examines evidence-based pharmacological treatments for heart failure:</p><ul><li>ACE inhibitors and ARBs</li><li>Beta-blockers</li><li>Diuretics</li><li>Novel therapies and combination approaches</li></ul><p>We'll discuss dosing strategies, monitoring, and management of side effects.</p>",
        order=3,
        video_url="https://www.youtube.com/embed/C0DPdy98e4c",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    next_module_id += 1
    
    # Create modules for Neurology course
    db.session.add(neurology_course)
    db.session.flush()  # Get the ID
    
    neuro_module1 = Module(
        id=next_module_id,
        course_id=neurology_course.id,
        title="Neuroanatomy Foundations",
        content="<p>This module provides a solid foundation in neuroanatomy essential for performing assessments:</p><ul><li>Cerebral cortex and lobes</li><li>Brainstem and cranial nerves</li><li>Spinal cord pathways</li><li>Functional neuroanatomy</li></ul>",
        order=1,
        video_url="https://www.youtube.com/embed/tpiyEe_CqB4",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    next_module_id += 1
    
    neuro_module2 = Module(
        id=next_module_id,
        course_id=neurology_course.id,
        title="Cranial Nerve Examination",
        content="<p>This module provides detailed instruction on examining the 12 cranial nerves:</p><ul><li>Systematic examination techniques</li><li>Expected normal findings</li><li>Common abnormalities and their significance</li><li>Documentation best practices</li></ul>",
        order=2,
        video_url="https://www.youtube.com/embed/XZaUvRW7ijw",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    next_module_id += 1
    
    # Get next quiz ID
    max_quiz_id = db.session.query(db.func.max(Quiz.id)).scalar() or 0
    next_quiz_id = max_quiz_id + 1
    
    # Create a quiz for the cardiology module
    cardio_quiz = Quiz(
        id=next_quiz_id,
        module_id=cardio_module2.id,
        title="Cardiovascular Diagnostics Assessment",
        description="Test your understanding of diagnostic approaches for cardiovascular diseases.",
        passing_score=70,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Get next question ID
    max_question_id = db.session.query(db.func.max(QuizQuestion.id)).scalar() or 0
    next_question_id = max_question_id + 1
    
    # Create questions for the cardiology quiz
    question1 = QuizQuestion(
        id=next_question_id,
        quiz_id=next_quiz_id,
        question="Which biomarker is most specific for myocardial injury?",
        options=["CRP (C-Reactive Protein)", "Troponin", "BNP (Brain Natriuretic Peptide)", "D-dimer"],
        correct_answer=1,  # Second option (index 1) - Troponin
        order=1,
        created_at=datetime.now()
    )
    next_question_id += 1
    
    question2 = QuizQuestion(
        id=next_question_id,
        quiz_id=next_quiz_id,
        question="Which imaging modality is considered the gold standard for assessing cardiac anatomy and function?",
        options=["Chest X-ray", "Echocardiography", "Cardiac MRI", "Coronary angiography"],
        correct_answer=2,  # Third option (index 2) - Cardiac MRI
        order=2,
        created_at=datetime.now()
    )
    next_question_id += 1
    
    question3 = QuizQuestion(
        id=next_question_id,
        quiz_id=next_quiz_id,
        question="What is the primary purpose of a stress test in cardiac assessment?",
        options=["To evaluate resting heart function", "To detect coronary artery disease by inducing myocardial ischemia", "To visualize valve structure", "To measure chamber volumes"],
        correct_answer=1,  # Second option (index 1) - To detect CAD
        order=3,
        created_at=datetime.now()
    )
    
    # Add all objects to the session
    objects_to_add = [
        emergency_course,
        cardio_module2, cardio_module3,
        neuro_module1, neuro_module2,
        cardio_quiz,
        question1, question2, question3
    ]
    
    db.session.add_all(objects_to_add)
    
    # Commit the changes
    db.session.commit()
    
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    with app.app_context():
        seed_data()