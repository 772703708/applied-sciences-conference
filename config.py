import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(BASEDIR, "instance", "conference.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads (محلي - سيتم استبداله بـ Google Drive)
    UPLOAD_FOLDER = os.path.join(BASEDIR, 'uploads')
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
    ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Session
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    USE_GOOGLE_DRIVE = True
    
    # Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Conference Info
    CONFERENCE_NAME = "المؤتمر العلمي الدولي الأول - آفاق العلوم التطبيقية"
    CONFERENCE_DATES = "27-29 يوليو 2026"
    CONFERENCE_VENUE = "كلية العلوم التطبيقية - جامعة ذمار"
    CONFERENCE_EMAIL = "info@applied-science-conf.com"
    CONFERENCE_PHONE = "+967 774 553 051"
    WHATSAPP_NUMBER = "967774553051"
    
    # ========================================
    # Google Drive OAuth Configuration
    # ========================================
    # تم إزالة GOOGLE_APPLICATION_CREDENTIALS لأننا نستخدم OAuth الآن
    # سيتم استخدام client_secret.json و token.json بدلاً من ذلك
    
    # Google Drive Folder IDs (نفسها بدون تغيير)
    DRIVE_FOLDER_IDS = {
        'root': os.environ.get('DRIVE_ROOT_ID', '1P9PuMaHKg1h_kLj9y1dupCzcTApLESg4'),
        'papers_root': os.environ.get('DRIVE_PAPERS_ROOT', '19FyF9giN_4SBeKeWIn5NlT29ABtkUFro'),
        'energy': os.environ.get('DRIVE_ENERGY', '1paOu3NnQGSuuGZLlScLJYgIU8H8kJvU-'),
        'nanotechnology': os.environ.get('DRIVE_NANOTECH', '1D99Ail3o9zGvW58N-w_cVyAVXciaabRX'),
        'biology': os.environ.get('DRIVE_BIOLOGY', '1-ol5ao-XXDui_kgdJcEg8VFLJPfJcrxW'),
        'geology': os.environ.get('DRIVE_GEOLOGY', '1i0Br5bI_9qiyoClYCUXeRnfRS0dWjtSV'),
        'statistics': os.environ.get('DRIVE_STATISTICS', '1yENeHQN2kz-NdzN_SKKg0DX8pf_7_QKO'),
        'chemistry': os.environ.get('DRIVE_CHEMISTRY', '1JifmU0KN3lwZ12n1siEvZyyrMihGmiY5'),
        'registrations': os.environ.get('DRIVE_REGISTRATIONS', '10GKLGt9prQfnuDbI489C4lyzKQsDO9Iv'),
        'attendance': os.environ.get('DRIVE_ATTENDANCE', '1yop235HApG5QzO8tbOeSYl3lQkFDOPTX'),
        'reports': os.environ.get('DRIVE_REPORTS', '1yUUJdvVqiHMQvK4YPQAs1zLoS2bBRo2E'),
    }
    
    # Track to Folder ID mapping
    TRACK_FOLDER_MAPPING = {
        'energy': DRIVE_FOLDER_IDS['energy'],
        'nanotechnology': DRIVE_FOLDER_IDS['nanotechnology'],
        'biology': DRIVE_FOLDER_IDS['biology'],
        'geology': DRIVE_FOLDER_IDS['geology'],
        'statistics': DRIVE_FOLDER_IDS['statistics'],
        'chemistry': DRIVE_FOLDER_IDS['chemistry'],
    }
    
    # Available tracks for submission
    TRACK_CHOICES = [
        ('energy', 'الطاقة المستدامة والطاقة المتجددة'),
        ('nanotechnology', 'علم المواد المتقدمة وتكنولوجيا النانو'),
        ('biology', 'العلوم البيولوجية والتكنولوجيا الحيوية'),
        ('geology', 'الجيولوجيا والبيئة والموارد المائية'),
        ('statistics', 'الإحصاء والنمذجة الرياضية'),
        ('chemistry', 'الكيمياء وتطبيقاتها التكنولوجية'),
    ]
    
    # Submission types
    SUBMISSION_TYPE_CHOICES = [
        ('paper', 'بحث علمي كامل'),
        ('poster', 'ملصق علمي'),
        ('workshop', 'ورشة عمل'),
    ]