from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# إنشاء كائن db جديد هنا بدلاً من استيراده
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    avatar = db.Column(db.String(200))
    bio = db.Column(db.Text)
    affiliation = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_reviewer(self):
        return self.role == 'reviewer'
    
    def __repr__(self):
        return f'<User {self.username}>'

class Paper(db.Model):
    __tablename__ = 'papers'
    
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    title_ar = db.Column(db.String(300))
    abstract = db.Column(db.Text, nullable=False)
    abstract_ar = db.Column(db.Text)
    keywords = db.Column(db.String(200))
    file_path = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(20), default='pending')
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    main_author_name = db.Column(db.String(100), nullable=False)
    main_author_email = db.Column(db.String(120), nullable=False)
    main_author_phone = db.Column(db.String(20))
    main_author_affiliation = db.Column(db.String(200))
    co_authors = db.Column(db.Text)
    
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewer_notes = db.Column(db.Text)
    reviewer_rating = db.Column(db.Integer)
    track = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<Paper {self.tracking_id}>'

class Speaker(db.Model):
    __tablename__ = 'speakers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100))  # تم التعديل: name_ar -> name_en
    title = db.Column(db.String(200))
    title_en = db.Column(db.String(200))  # تم التعديل: title_ar -> title_en
    affiliation = db.Column(db.String(200))
    bio = db.Column(db.Text)
    bio_en = db.Column(db.Text)  # تم التعديل: bio_ar -> bio_en
    photo = db.Column(db.String(200))
    email = db.Column(db.String(120))
    linkedin = db.Column(db.String(200))
    twitter = db.Column(db.String(200))
    order = db.Column(db.Integer, default=0)
    is_keynote = db.Column(db.Boolean, default=False)
    session_title = db.Column(db.String(200))
    session_time = db.Column(db.String(50))
    committee = db.Column(db.String(100))  # تم الإضافة: لتحديد اللجنة
    
    def __repr__(self):
        return f'<Speaker {self.name}>'

class Sponsor(db.Model):
    __tablename__ = 'sponsors'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    logo = db.Column(db.String(200), nullable=False)
    website = db.Column(db.String(200))
    description = db.Column(db.Text)
    tier = db.Column(db.String(50))
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Sponsor {self.name}>'

class News(db.Model):
    __tablename__ = 'news'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200))  # تم التعديل: title_ar -> title_en
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    content_en = db.Column(db.Text)  # تم التعديل: content_ar -> content_en
    excerpt = db.Column(db.String(300))
    image = db.Column(db.String(200))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    views = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    author = db.relationship('User', backref='news')
    
    def __repr__(self):
        return f'<News {self.title}>'

class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200))  # تم التعديل: title_ar -> title_en
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    speaker_id = db.Column(db.Integer, db.ForeignKey('speakers.id'))
    event_type = db.Column(db.String(50))
    order = db.Column(db.Integer, default=0)
    
    speaker = db.relationship('Speaker', backref='events')
    
    def __repr__(self):
        return f'<Event {self.title}>'

class ContactMessage(db.Model):
    __tablename__ = 'contacts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    replied = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Contact from {self.name}>'

class Gallery(db.Model):
    __tablename__ = 'gallery'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    image = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    order = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Gallery {self.title}>'

class Setting(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(200))
    site_description = db.Column(db.Text)
    site_logo = db.Column(db.String(200))
    site_favicon = db.Column(db.String(200))
    
    conference_dates = db.Column(db.String(100))
    conference_venue = db.Column(db.String(200))
    registration_deadline = db.Column(db.String(50))
    submission_deadline = db.Column(db.String(50))
    early_bird_deadline = db.Column(db.String(50))
    
    registration_open = db.Column(db.Boolean, default=True)
    submission_open = db.Column(db.Boolean, default=True)
    conference_active = db.Column(db.Boolean, default=True)
    
    dark_mode_default = db.Column(db.Boolean, default=False)
    rtl_default = db.Column(db.Boolean, default=True)
    primary_color = db.Column(db.String(20), default='#0d6efd')
    
    facebook_url = db.Column(db.String(200))
    twitter_url = db.Column(db.String(200))
    linkedin_url = db.Column(db.String(200))
    youtube_url = db.Column(db.String(200))
    
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    whatsapp_number = db.Column(db.String(20))
    address = db.Column(db.Text)
    
    google_analytics_id = db.Column(db.String(50))
    meta_keywords = db.Column(db.String(500))
    
    def __repr__(self):
        return f'<Setting {self.site_name}>'

class Track(db.Model):
    __tablename__ = 'tracks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    name_en = db.Column(db.String(200))  # تم التعديل: name_ar -> name_en
    description = db.Column(db.Text)
    description_en = db.Column(db.Text)  # تم التعديل: description_ar -> description_en
    icon = db.Column(db.String(50))
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Track {self.name}>'

class FAQ(db.Model):
    __tablename__ = 'faqs'
    
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(300), nullable=False)
    question_en = db.Column(db.String(300))  # تم التعديل: question_ar -> question_en
    answer = db.Column(db.Text, nullable=False)
    answer_en = db.Column(db.Text)  # تم التعديل: answer_ar -> answer_en
    category = db.Column(db.String(50))
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<FAQ {self.question[:50]}>'


# ========================================
# Paper Submission with Google Drive
# ========================================

class PaperSubmission(db.Model):
    """نموذج متكامل لتقديم الأبحاث مع Google Drive"""
    __tablename__ = 'paper_submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Paper Information
    title = db.Column(db.String(300), nullable=False)
    title_en = db.Column(db.String(300))  # تم التعديل: title_ar -> title_en
    abstract = db.Column(db.Text, nullable=False)
    abstract_en = db.Column(db.Text)  # تم التعديل: abstract_ar -> abstract_en
    keywords = db.Column(db.String(200))
    submission_type = db.Column(db.String(50), default='paper')
    track = db.Column(db.String(100), nullable=False)
    
    # Author Information
    main_author_name = db.Column(db.String(100), nullable=False)
    main_author_email = db.Column(db.String(120), nullable=False)
    main_author_phone = db.Column(db.String(20), nullable=False)
    main_author_affiliation = db.Column(db.String(200), nullable=False)
    co_authors = db.Column(db.Text)
    
    # Google Drive Information
    gdrive_file_id = db.Column(db.String(100), nullable=False)
    gdrive_view_link = db.Column(db.String(500), nullable=False)
    gdrive_download_link = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(200))
    
    # Review Information
    assigned_reviewer_email = db.Column(db.String(120))
    reviewer_assigned_at = db.Column(db.DateTime)
    reviewer_notes = db.Column(db.Text)
    reviewer_rating = db.Column(db.Integer)
    
    # Status
    status = db.Column(db.String(50), default='pending')
    email_sent_status = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    
    # Timestamps
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref='submissions')
    
    def __repr__(self):
        return f'<PaperSubmission {self.tracking_id}>'


class ConferenceRegistration(db.Model):
    __tablename__ = 'conference_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    affiliation = db.Column(db.String(200))
    position = db.Column(db.String(100))
    registration_type = db.Column(db.String(50), default='attendee')
    selected_track = db.Column(db.String(100))
    presentation_title = db.Column(db.String(300))
    payment_status = db.Column(db.Boolean, default=False)
    payment_amount = db.Column(db.Float)
    payment_date = db.Column(db.DateTime)
    dietary_requirements = db.Column(db.Text)
    special_needs = db.Column(db.Text)
    is_confirmed = db.Column(db.Boolean, default=False)
    confirmed_at = db.Column(db.DateTime)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', backref='registrations')
    
    def __repr__(self):
        return f'<ConferenceRegistration {self.email}>'


class AttendanceRegistration(db.Model):
    __tablename__ = 'attendance_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    affiliation = db.Column(db.String(200))
    attendance_days = db.Column(db.String(100))
    attendance_type = db.Column(db.String(50), default='in_person')
    is_attended = db.Column(db.Boolean, default=False)
    certificate_sent = db.Column(db.Boolean, default=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AttendanceRegistration {self.email}>'


class ReviewerAssignment(db.Model):
    __tablename__ = 'reviewer_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper_submissions.id'), nullable=False)
    paper = db.relationship('PaperSubmission', backref='reviewer_assignments')
    reviewer_email = db.Column(db.String(120), nullable=False)
    reviewer_name = db.Column(db.String(100))
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    response_at = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='pending')
    review_completed_at = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    rating = db.Column(db.Integer)
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    reminder_sent = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<ReviewerAssignment Paper:{self.paper_id} Reviewer:{self.reviewer_email}>'


class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(120), nullable=False)
    recipient_name = db.Column(db.String(100))
    subject = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper_submissions.id'), nullable=True)
    paper = db.relationship('PaperSubmission', backref='email_logs')
    email_type = db.Column(db.String(50))
    status = db.Column(db.String(50), default='pending')
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<EmailLog to:{self.recipient} type:{self.email_type}>'


# ========================================
# Reviewer Model (منفصل عن Users)
# ========================================

class Reviewer(db.Model):
    __tablename__ = 'reviewers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    degree = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    specialties = db.Column(db.Text, nullable=False)
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Reviewer {self.name}>'