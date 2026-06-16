from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, PasswordField, EmailField, TelField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, Regexp
from config import Config

class LoginForm(FlaskForm):
    email = EmailField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired(), Length(min=6)])
    remember = BooleanField('تذكرني')
    
class AdminLoginForm(FlaskForm):
    email = EmailField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    remember = BooleanField('تذكرني')

class PaperSubmissionForm(FlaskForm):
    title = StringField('عنوان البحث (بالعربية)', validators=[DataRequired(), Length(max=300)])
    title_en = StringField('عنوان البحث (بالإنجليزية)', validators=[DataRequired(), Length(max=300)])  # تم التعديل: title_ar -> title_en
    abstract = TextAreaField('الملخص (بالعربية)', validators=[DataRequired(), Length(min=50, max=5000)])
    abstract_en = TextAreaField('الملخص (بالإنجليزية)', validators=[Length(max=5000)])  # تم التعديل: abstract_ar -> abstract_en
    keywords = StringField('الكلمات المفتاحية', validators=[DataRequired(), Length(max=200)])
    
    # Main author
    main_author_name = StringField('الاسم الكامل', validators=[DataRequired(), Length(max=100)])
    main_author_email = EmailField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    main_author_phone = TelField('رقم الجوال', validators=[DataRequired(), Length(max=20)])
    main_author_affiliation = StringField('الجهة التابع لها', validators=[DataRequired(), Length(max=200)])
    
    # Co-authors (JSON format)
    co_authors = TextAreaField('المؤلفون المشاركون (اسم - بريد إلكتروني - جهة، كل سطر شخص)', 
                               validators=[Optional()])
    
    # Conference track
    track = SelectField('المحور العلمي الرئيسي', choices=[
        ('energy', 'الطاقة المستدامة والطاقة المتجددة'),
        ('nanotechnology', 'علم المواد المتقدمة وتكنولوجيا النانو'),
        ('biology', 'العلوم البيولوجية والتكنولوجيا الحيوية'),
        ('geology', 'الجيولوجيا والبيئة والموارد المائية'),
        ('statistics', 'الإحصاء والنمذجة الرياضية'),
        ('chemistry', 'الكيمياء وتطبيقاتها التكنولوجية'),
    ], validators=[DataRequired()])
    
    # Submission type
    submission_type = SelectField('نوع المشاركة', choices=[
        ('paper', 'بحث علمي كامل'),
        ('poster', 'ملصق علمي (Poster)'),
        ('workshop', 'ورشة عمل'),
    ], validators=[DataRequired()])
    
    # File upload - دعم PDF و Word
    paper_file = FileField('الورقة العلمية', validators=[
        FileRequired(),
        FileAllowed(['pdf', 'doc', 'docx'], 'PDF أو Word فقط!')
    ])
    
    agree_terms = BooleanField('أوافق على شروط النشر وسياسة الخصوصية', 
                               validators=[DataRequired()])

class PaperTrackingForm(FlaskForm):
    tracking_id = StringField('رقم التتبع', validators=[
        DataRequired(),
        Regexp(r'^[A-Z0-9]{8,12}$', message='رقم التتبع غير صالح')
    ])
    email = EmailField('البريد الإلكتروني', validators=[DataRequired(), Email()])

class ContactForm(FlaskForm):
    name = StringField('الاسم', validators=[DataRequired(), Length(max=100)])
    email = EmailField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    phone = TelField('رقم الجوال', validators=[Optional(), Length(max=20)])
    subject = StringField('الموضوع', validators=[DataRequired(), Length(max=200)])
    message = TextAreaField('الرسالة', validators=[DataRequired(), Length(min=10, max=5000)])

class RegistrationForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=3, max=80)])
    email = EmailField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('تأكيد كلمة المرور', 
                                     validators=[DataRequired(), EqualTo('password')])
    affiliation = StringField('الجهة التابع لها', validators=[DataRequired(), Length(max=200)])
    phone = TelField('رقم الجوال', validators=[Optional()])

class ConferenceRegistrationForm(FlaskForm):
    """نموذج تسجيل المشاركين في المؤتمر"""
    full_name = StringField('الاسم الكامل', validators=[DataRequired(), Length(max=150)])
    email = EmailField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    phone = TelField('رقم الجوال', validators=[DataRequired(), Length(max=20)])
    affiliation = StringField('الجهة التابع لها', validators=[Length(max=200)])
    position = StringField('المنصب / الوظيفة', validators=[Length(max=100)])
    
    registration_type = SelectField('نوع التسجيل', choices=[
        ('presenter', 'باحث / مقدم ورقة علمية'),
        ('attendee', 'حضور فقط'),
        ('student', 'طالب'),
    ], validators=[DataRequired()])
    
    selected_track = SelectField('التخصص العلمي (للباحثين)', choices=[
        ('', '--- اختر التخصص ---'),
        ('energy', 'الطاقة المستدامة والطاقة المتجددة'),
        ('nanotechnology', 'علم المواد المتقدمة وتكنولوجيا النانو'),
        ('biology', 'العلوم البيولوجية والتكنولوجيا الحيوية'),
        ('geology', 'الجيولوجيا والبيئة والموارد المائية'),
        ('statistics', 'الإحصاء والنمذجة الرياضية'),
        ('chemistry', 'الكيمياء وتطبيقاتها التكنولوجية'),
    ], validators=[Optional()])
    
    presentation_title = StringField('عنوان الورقة العلمية (للباحثين)', validators=[Length(max=300)])
    dietary_requirements = TextAreaField('احتياجات غذائية خاصة', validators=[Optional()])
    special_needs = TextAreaField('احتياجات خاصة', validators=[Optional()])

class AttendanceRegistrationForm(FlaskForm):
    """نموذج تسجيل الحضور"""
    full_name = StringField('الاسم الكامل', validators=[DataRequired(), Length(max=150)])
    email = EmailField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    phone = TelField('رقم الجوال', validators=[DataRequired(), Length(max=20)])
    affiliation = StringField('الجهة التابع لها', validators=[Length(max=200)])
    
    attendance_days = SelectField('أيام الحضور', choices=[
        ('1', 'اليوم الأول فقط (27 يوليو 2026)'),
        ('2', 'اليوم الثاني فقط (28 يوليو 2026)'),
        ('3', 'اليوم الثالث فقط (29 يوليو 2026)'),
        ('all', 'جميع أيام المؤتمر (3 أيام)'),
    ], validators=[DataRequired()])
    
    attendance_type = SelectField('نوع الحضور', choices=[
        ('in_person', 'حضور شخصي'),
        ('online', 'حضور عن بُعد'),
    ], validators=[DataRequired()])

# Admin Forms
class NewsForm(FlaskForm):
    title = StringField('العنوان (بالعربية)', validators=[DataRequired(), Length(max=200)])
    title_en = StringField('العنوان (بالإنجليزية)', validators=[Length(max=200)])  # تم التعديل: title_ar -> title_en
    slug = StringField('الرابط المختصر', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('المحتوى (بالعربية)', validators=[DataRequired()])
    content_en = TextAreaField('المحتوى (بالإنجليزية)')  # تم التعديل: content_ar -> content_en
    excerpt = StringField('ملخص', validators=[Length(max=300)])
    image = FileField('الصورة', validators=[FileAllowed(['jpg','png','jpeg','webp'])])
    is_published = BooleanField('منشور')

class SpeakerForm(FlaskForm):
    name = StringField('الاسم (بالعربية)', validators=[DataRequired(), Length(max=100)])
    name_en = StringField('الاسم (بالإنجليزية)', validators=[Length(max=100)])  # تم التعديل: name_ar -> name_en
    title = StringField('المنصب (بالعربية)', validators=[Length(max=200)])
    title_en = StringField('المنصب (بالإنجليزية)')  # تم التعديل: title_ar -> title_en
    affiliation = StringField('الجهة', validators=[Length(max=200)])
    bio = TextAreaField('السيرة الذاتية (بالعربية)')
    bio_en = TextAreaField('السيرة الذاتية (بالإنجليزية)')  # تم التعديل: bio_ar -> bio_en
    photo = FileField('الصورة', validators=[FileAllowed(['jpg','png','jpeg','webp'])])
    email = EmailField('البريد الإلكتروني')
    linkedin = StringField('LinkedIn')
    twitter = StringField('Twitter')
    is_keynote = BooleanField('متحدث رئيسي')
    order = IntegerField('ترتيب العرض', default=0)

class SponsorForm(FlaskForm):
    name = StringField('اسم الراعي', validators=[DataRequired(), Length(max=100)])
    logo = FileField('الشعار', validators=[FileRequired(), FileAllowed(['jpg','png','jpeg','webp','svg'])])
    website = StringField('الموقع الإلكتروني')
    description = TextAreaField('الوصف')
    tier = SelectField('المستوى', choices=[
        ('platinum', 'بلاتيني'),
        ('gold', 'ذهبي'),
        ('silver', 'فضي'),
        ('bronze', 'برونزي')
    ])
    is_active = BooleanField('نشط')

class SettingsForm(FlaskForm):
    # معلومات الموقع
    site_name = StringField('اسم الموقع')
    site_description = TextAreaField('وصف الموقع')
    site_logo = StringField('شعار الموقع')
    site_favicon = StringField('أيقونة الموقع')
    meta_keywords = StringField('الكلمات المفتاحية (SEO)')
    
    # معلومات المؤتمر
    conference_dates = StringField('تواريخ المؤتمر')
    conference_venue = StringField('مكان المؤتمر')
    registration_deadline = StringField('آخر موعد للتسجيل')
    submission_deadline = StringField('آخر موعد لتقديم الأبحاث')
    early_bird_deadline = StringField('آخر موعد للخصم المبكر')
    
    registration_open = BooleanField('التسجيل مفتوح')
    submission_open = BooleanField('تقديم الأبحاث مفتوح')
    conference_active = BooleanField('المؤتمر نشط')
    
    # إعدادات المظهر
    dark_mode_default = BooleanField('الوضع المظلم افتراضياً')
    rtl_default = BooleanField('RTL افتراضياً')
    primary_color = StringField('اللون الأساسي')
    
    # روابط التواصل الاجتماعي
    facebook_url = StringField('فيسبوك')
    twitter_url = StringField('تويتر')
    linkedin_url = StringField('لينكدإن')
    youtube_url = StringField('يوتيوب')
    
    # معلومات الاتصال
    contact_email = StringField('بريد التواصل')
    contact_phone = StringField('رقم الهاتف')
    whatsapp_number = StringField('رقم واتساب')
    address = TextAreaField('العنوان')
    
    # تحليلات
    google_analytics_id = StringField('Google Analytics ID')

class ReviewerEmailForm(FlaskForm):
    """نموذج إضافة بريد محكم جديد"""
    track = SelectField('التخصص', choices=[
        ('energy', 'الطاقة المستدامة'),
        ('nanotechnology', 'تكنولوجيا النانو'),
        ('biology', 'العلوم البيولوجية'),
        ('geology', 'الجيولوجيا'),
        ('statistics', 'الإحصاء'),
        ('chemistry', 'الكيمياء'),
    ], validators=[DataRequired()])
    
    email = EmailField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    name = StringField('الاسم', validators=[DataRequired(), Length(max=100)])

# Profile Forms
class ProfileEditForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=3, max=80)])
    affiliation = StringField('الجهة التابع لها', validators=[Length(max=200)])
    phone = TelField('رقم الجوال', validators=[Optional(), Length(max=20)])
    bio = TextAreaField('السيرة الذاتية', validators=[Optional(), Length(max=500)])

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('كلمة المرور الحالية', validators=[DataRequired()])
    new_password = PasswordField('كلمة المرور الجديدة', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('تأكيد كلمة المرور', 
                                     validators=[DataRequired(), EqualTo('new_password')])