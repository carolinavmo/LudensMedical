from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, FloatField, IntegerField, BooleanField, HiddenField, RadioField, FieldList, FormField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, URL, ValidationError

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class SignupForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])

class CourseForm(FlaskForm):
    title = StringField('Course Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Category', validators=[DataRequired()], choices=[
        ('cardiology', 'Cardiology'),
        ('neurology', 'Neurology'),
        ('orthopedics', 'Orthopedics'),
        ('pediatrics', 'Pediatrics'),
        ('general_practice', 'General Practice'),
        ('surgery', 'Surgery'),
        ('radiology', 'Radiology'),
        ('psychiatry', 'Psychiatry'),
        ('emergency', 'Emergency Medicine')
    ])
    level = SelectField('Level', validators=[DataRequired()], choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced')
    ])
    price = FloatField('Price (USD)', validators=[DataRequired(), NumberRange(min=0)])
    image_url = StringField('Image URL', validators=[Optional(), URL()])

class ModuleForm(FlaskForm):
    title = StringField('Module Title', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Content', validators=[DataRequired()])
    order = IntegerField('Order', validators=[DataRequired(), NumberRange(min=1)])
    video_url = StringField('Video URL', validators=[Optional(), URL()])
    pdf_url = StringField('PDF URL', validators=[Optional(), URL()])

class QuizForm(FlaskForm):
    title = StringField('Quiz Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    passing_score = IntegerField('Passing Score (%)', validators=[
        DataRequired(), 
        NumberRange(min=1, max=100)
    ])

class QuestionForm(FlaskForm):
    question = StringField('Question', validators=[DataRequired()])
    option1 = StringField('Option 1', validators=[DataRequired()])
    option2 = StringField('Option 2', validators=[DataRequired()])
    option3 = StringField('Option 3', validators=[Optional()])
    option4 = StringField('Option 4', validators=[Optional()])
    correct_answer = SelectField('Correct Answer', validators=[DataRequired()], choices=[
        ('0', 'Option 1'),
        ('1', 'Option 2'),
        ('2', 'Option 3'),
        ('3', 'Option 4')
    ])
    order = IntegerField('Order', validators=[DataRequired(), NumberRange(min=1)])

class QuizSubmissionForm(FlaskForm):
    quiz_id = HiddenField('Quiz ID', validators=[DataRequired()])
    answers = FieldList(RadioField('Answer', choices=[]), min_entries=1)

class ProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    bio = TextAreaField('Biography', validators=[Optional(), Length(max=500)])

class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(), 
        EqualTo('new_password', message='Passwords must match')
    ])

class UserForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', validators=[DataRequired()], choices=[
        ('student', 'Student'),
        ('admin', 'Administrator')
    ])
