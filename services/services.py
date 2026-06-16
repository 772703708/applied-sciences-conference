from flask import current_app, url_for
from flask_mail import Message
from werkzeug.utils import secure_filename
import os
import uuid
import json
import io
from datetime import datetime
from app import mail, db
from models import User, Paper, PaperSubmission, ReviewerAssignment, EmailLog, Reviewer
from utils import generate_tracking_id, secure_filename_ar


# ========================================
# Local File Services (للحفاظ على التوافق مع النظام القديم)
# ========================================

def save_paper_file(file, tracking_id):
    """حفظ ملف البحث والعودة بمسار الملف (محلياً)"""
    filename = secure_filename_ar(file.filename)
    safe_filename = f"{tracking_id}_{filename}"
    
    # إنشاء مجلد السنة والشهر لتنظيم الملفات
    year_month = datetime.now().strftime('%Y/%m')
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'papers', year_month)
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, safe_filename)
    file.save(file_path)
    
    # إرجاع المسار النسبي للتخزين في قاعدة البيانات
    return os.path.join('papers', year_month, safe_filename)


# ========================================
# Email Services
# ========================================

def send_paper_confirmation_email(paper):
    """إرسال بريد تأكيد عند تقديم البحث"""
    subject = f"تأكيد استلام البحث - {paper.tracking_id}"
    
    body = f"""
عزيزي {paper.main_author_name}،

تم استلام بحثك بنجاح.

عنوان البحث: {paper.title}
رقم التتبع: {paper.tracking_id}
تاريخ التقديم: {paper.submitted_at.strftime('%Y-%m-%d %H:%M')}

يمكنك تتبع حالة بحثك عبر الرابط التالي:
{url_for('submission.track_paper', _external=True)}

سيتم إعلامك عند اكتمال عملية التحكيم.

شكراً لمشاركتكم.
-- 
فريق المؤتمر
"""
    
    msg = Message(
        subject=subject,
        recipients=[paper.main_author_email],
        body=body
    )
    mail.send(msg)
    
    # تسجيل الإيميل
    email_log = EmailLog(
        recipient=paper.main_author_email,
        recipient_name=paper.main_author_name,
        subject=subject,
        body=body,
        paper_id=paper.id if hasattr(paper, 'id') else None,
        email_type='submission_confirmation',
        status='sent',
        sent_at=datetime.utcnow()
    )
    db.session.add(email_log)
    db.session.commit()


def send_status_update_email(paper, old_status, new_status):
    """إرسال بريد عند تغيير حالة البحث"""
    status_messages = {
        'under_review': 'بحثك قيد المراجعة حالياً',
        'accepted': 'تم قبول بحثك في المؤتمر 🎉',
        'rejected': 'نأسف لإبلاغك بأن بحثك لم يتم قبوله',
        'revision_required': 'مطلوب إجراء تعديلات على بحثك'
    }
    
    subject = f"تحديث حالة البحث - {paper.tracking_id}"
    body = f"""
عزيزي {paper.main_author_name}،

{status_messages.get(new_status, 'تم تحديث حالة بحثك')}

الحالة الجديدة: {new_status}

للمزيد من التفاصيل، يرجى تتبع بحثك:
{url_for('submission.track_paper', _external=True)}

شكراً لتواصلكم.
"""
    
    msg = Message(subject=subject, recipients=[paper.main_author_email], body=body)
    mail.send(msg)
    
    # تسجيل الإيميل
    email_log = EmailLog(
        recipient=paper.main_author_email,
        recipient_name=paper.main_author_name,
        subject=subject,
        body=body,
        paper_id=paper.id if hasattr(paper, 'id') else None,
        email_type='status_update',
        status='sent',
        sent_at=datetime.utcnow()
    )
    db.session.add(email_log)
    db.session.commit()


def send_contact_acknowledgement(name, email, message_subject):
    """إرسال إقرار باستلام رسالة الاتصال"""
    subject = "شكراً لتواصلكم مع المؤتمر"
    body = f"""
عزيزي {name}،

تم استلام رسالتكم بعنوان "{message_subject}" بنجاح.
سنقوم بالرد عليكم في أقرب وقت ممكن.

شكراً لاهتمامكم.
--
فريق دعم المؤتمر
"""
    
    msg = Message(subject=subject, recipients=[email], body=body)
    mail.send(msg)


def send_registration_email(user):
    """إرسال بريد تأكيد التسجيل"""
    subject = "مرحباً بك في منصة المؤتمر"
    body = f"""
عزيزي {user.username}،

تم تسجيل حسابك بنجاح في منصة المؤتمر.

بريدك الإلكتروني: {user.email}

يمكنك الآن تقديم أبحاثك وتتبعها من خلال حسابك.

مع أطيب التمنيات،
فريق المؤتمر
"""
    
    msg = Message(subject=subject, recipients=[user.email], body=body)
    mail.send(msg)


def send_conference_registration_confirmation(registration):
    """إرسال تأكيد تسجيل المشارك في المؤتمر"""
    subject = "تأكيد التسجيل في المؤتمر العلمي الدولي الأول"
    body = f"""
عزيزي {registration.full_name}،

تم تسجيلك بنجاح في المؤتمر العلمي الدولي الأول.

بيانات التسجيل:
• نوع التسجيل: {registration.registration_type}
• البريد الإلكتروني: {registration.email}
• رقم الجوال: {registration.phone}

سيتم إرسال المزيد من التفاصيل قريباً.

شكراً لمشاركتكم.
--
فريق المؤتمر
"""
    
    msg = Message(subject=subject, recipients=[registration.email], body=body)
    mail.send(msg)


def send_admin_notification(result, form):
    """
    إرسال إيميل للمشرف عند تقديم بحث جديد
    """
    from flask_mail import Message
    
    subject = f"📌 ورقة علمية جديدة - {result['tracking_id']}"
    
    body = f"""
السلام عليكم،

تم تقديم ورقة علمية جديدة في نظام المؤتمر.

تفاصيل الورقة:
----------------------------------------
• رقم التتبع: {result['tracking_id']}
• عنوان الورقة: {form.title.data}
• التخصص: {form.track.data}
• الباحث الرئيسي: {form.main_author_name.data}
• البريد الإلكتروني: {form.main_author_email.data}
• رقم الجوال: {form.main_author_phone.data}
• الجهة: {form.main_author_affiliation.data}

حالة الرفع إلى Google Drive: ✅ تم الرفع بنجاح
رابط الملف: {result['view_link']}

المحكمون المعينون:
----------------------------------------
"""
    if result.get('assigned_reviewers'):
        for reviewer in result['assigned_reviewers']:
            status = "✅" if reviewer['success'] else "❌"
            body += f"{status} {reviewer['name']} - {reviewer['email']}\n"
    else:
        body += "⚠️ لم يتم تعيين محكمين (لا توجد إيميلات مسجلة لهذا التخصص)\n"

    body += f"""
----------------------------------------
تم تقديم الورقة في: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

يرجى متابعة حالة الورقة من خلال لوحة التحكم.
    
مع خالص التحية،
نظام إدارة المؤتمر العلمي
"""

    try:
        admins = User.query.filter_by(role='admin').all()
        admin_emails = [admin.email for admin in admins if admin.email]
        
        if admin_emails:
            msg = Message(
                subject=subject,
                recipients=admin_emails,
                body=body
            )
            mail.send(msg)
            print(f"✅ تم إرسال إيميل للمشرفين: {admin_emails}")
        else:
            print("⚠️ لا يوجد بريد إلكتروني للمشرفين")
            
    except Exception as e:
        print(f"❌ خطأ في إرسال إيميل المشرف: {e}")
        raise


# ========================================
# Paper Query Services
# ========================================

def get_paper_by_tracking_id(tracking_id, email):
    """البحث عن بحث باستخدام رقم التتبع والبريد الإلكتروني (النموذج القديم)"""
    return Paper.query.filter_by(
        tracking_id=tracking_id,
        main_author_email=email
    ).first()


def get_paper_submission_by_tracking_id(tracking_id, email):
    """البحث عن بحث باستخدام رقم التتبع والبريد الإلكتروني (النموذج الجديد)"""
    return PaperSubmission.query.filter_by(
        tracking_id=tracking_id,
        main_author_email=email
    ).first()


# ========================================
# File Validation Services
# ========================================

def validate_pdf_file(file_stream):
    """التحقق من صحة ملف PDF (ليس فقط الامتداد)"""
    header = file_stream.read(4)
    file_stream.seek(0)
    return header == b'%PDF'


def save_uploaded_image(file, folder):
    """حفظ الصورة المرفوعة"""
    filename = secure_filename_ar(file.filename)
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    return os.path.join(folder, filename)


def delete_old_file(file_path):
    """حذف ملف قديم"""
    if file_path:
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
    return False


# ========================================
# Password Reset Services
# ========================================

def generate_reset_token(email):
    """إنشاء رمز لإعادة تعيين كلمة المرور"""
    import jwt
    from datetime import datetime, timedelta
    from flask import current_app
    
    payload = {
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def verify_reset_token(token):
    """التحقق من صحة رمز إعادة تعيين كلمة المرور"""
    import jwt
    from flask import current_app
    
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload.get('email')
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def send_password_reset_email(user):
    """إرسال بريد إعادة تعيين كلمة المرور"""
    from flask import url_for
    
    reset_token = generate_reset_token(user.email)
    reset_url = url_for('auth.reset_password', token=reset_token, _external=True)
    
    subject = "إعادة تعيين كلمة المرور - المؤتمر العلمي الدولي الأول"
    body = f"""
عزيزي {user.username}،

تم طلب إعادة تعيين كلمة المرور لحسابك في منصة المؤتمر العلمي الدولي الأول.

اضغط على الرابط التالي لإعادة تعيين كلمة المرور:
{reset_url}

هذا الرابط صالح لمدة 24 ساعة فقط.

إذا لم تقم بطلب إعادة التعيين، يرجى تجاهل هذا البريد.

شكراً لكم،
فريق المؤتمر
"""
    
    msg = Message(subject=subject, recipients=[user.email], body=body)
    mail.send(msg)


# ========================================
# Google Drive Services
# ========================================

from services.google_drive import upload_file_to_drive, get_folder_id_by_track, get_file_info


def upload_paper_to_drive_and_save(file_stream, filename, tracking_id, track):
    """
    رفع ملف البحث إلى Google Drive وحفظ المعلومات
    """
    # تحديد المجلد المناسب حسب التخصص
    folder_id = get_folder_id_by_track(track)
    
    # إنشاء اسم ملف فريد
    safe_filename = f"{tracking_id}_{filename}"
    
    # رفع الملف إلى Google Drive
    upload_result = upload_file_to_drive(file_stream, safe_filename, folder_id)
    
    if not upload_result['success']:
        return {
            'success': False,
            'error': upload_result.get('error', 'فشل رفع الملف إلى Google Drive')
        }
    
    return {
        'success': True,
        'file_id': upload_result['file_id'],
        'view_link': upload_result['view_link'],
        'download_link': upload_result['download_link']
    }


def create_paper_submission(form_data, file_info, tracking_id, user_id=None):
    """
    إنشاء سجل تقديم بحث جديد في قاعدة البيانات (النموذج الجديد)
    """
    # معالجة المؤلفين المشاركين
    co_authors_list = []
    if form_data.get('co_authors'):
        for line in form_data['co_authors'].strip().split('\n'):
            if line.strip():
                parts = line.split('-')
                co_authors_list.append({
                    'name': parts[0].strip() if len(parts) > 0 else '',
                    'email': parts[1].strip() if len(parts) > 1 else '',
                    'affiliation': parts[2].strip() if len(parts) > 2 else ''
                })
    
    submission = PaperSubmission(
        tracking_id=tracking_id,
        title=form_data['title'],
        title_en=form_data.get('title_en', ''),
        abstract=form_data['abstract'],
        abstract_en=form_data.get('abstract_en', ''),
        keywords=form_data.get('keywords', ''),
        submission_type=form_data.get('submission_type', 'paper'),
        track=form_data['track'],
        main_author_name=form_data['main_author_name'],
        main_author_email=form_data['main_author_email'],
        main_author_phone=form_data['main_author_phone'],
        main_author_affiliation=form_data['main_author_affiliation'],
        co_authors=json.dumps(co_authors_list, ensure_ascii=False) if co_authors_list else None,
        gdrive_file_id=file_info['file_id'],
        gdrive_view_link=file_info['view_link'],
        gdrive_download_link=file_info['download_link'],
        original_filename=form_data.get('paper_file_filename', ''),
        status='pending',
        user_id=user_id
    )
    
    db.session.add(submission)
    db.session.commit()
    
    return submission


def assign_reviewer_to_paper(paper_id, reviewer_email, reviewer_name=None):
    """
    تعيين محكم لبحث معين
    """
    # التحقق من وجود المحكم في قاعدة البيانات
    reviewer = Reviewer.query.filter_by(email=reviewer_email).first()
    if not reviewer:
        print(f"⚠️ المحكم {reviewer_email} غير موجود في قاعدة البيانات")
        # إنشاء المحكم تلقائياً
        reviewer = Reviewer(
            name=reviewer_name or reviewer_email.split('@')[0],
            degree='دكتور',
            email=reviewer_email,
            phone='+967XXXXXXXXX',
            specialties=''
        )
        db.session.add(reviewer)
        db.session.commit()
        print(f"✅ تم إضافة المحكم {reviewer_email} إلى قاعدة البيانات")
    
    assignment = ReviewerAssignment(
        paper_id=paper_id,
        reviewer_email=reviewer_email,
        reviewer_name=reviewer_name or reviewer.name,
        assigned_at=datetime.utcnow(),
        status='pending'
    )
    
    db.session.add(assignment)
    db.session.commit()
    
    return assignment


def send_paper_to_reviewer_email(paper_submission, reviewer_email, reviewer_name=None, file_data=None, filename=None):
    """
    إرسال إيميل إلى المحكم مع رابط البحث والملف مرفق
    """
    print(f"📧 محاولة إرسال إيميل إلى: {reviewer_email}")
    
    if not reviewer_email:
        print("❌ البريد الإلكتروني فارغ!")
        return {'success': False, 'error': 'البريد الإلكتروني فارغ'}
    
    subject = f"[طلب تحكيم] ورقة علمية جديدة - {paper_submission.tracking_id}"
    
    body = f"""
السلام عليكم ورحمة الله وبركاته،

تم إسناد ورقة علمية إليكم لتحكيمها ضمن فعاليات المؤتمر العلمي الدولي الأول.

بيانات الورقة العلمية:
----------------------------------------
• عنوان الورقة: {paper_submission.title}
• التخصص: {paper_submission.track}
• رقم التتبع: {paper_submission.tracking_id}

بيانات الباحث الرئيسي:
• الاسم: {paper_submission.main_author_name}
• البريد الإلكتروني: {paper_submission.main_author_email}
• رقم الجوال: {paper_submission.main_author_phone}
• الجهة: {paper_submission.main_author_affiliation}

الملف المرفق:
----------------------------------------
تم إرفاق ملف الورقة العلمية مع هذا البريد الإلكتروني.

رابط الملف على Google Drive (للمعاينة):
{paper_submission.gdrive_view_link}

رابط التحميل المباشر:
{paper_submission.gdrive_download_link}

----------------------------------------
يرجى مراجعة الورقة العلمية وإرسال تقرير التحكيم في أقرب وقت ممكن.

شكراً لتعاونكم في إثراء المحتوى العلمي للمؤتمر.

مع خالص التحية،
اللجنة العلمية - المؤتمر العلمي الدولي الأول
كلية العلوم التطبيقية - جامعة ذمار
"""
    
    msg = Message(
        subject=subject,
        recipients=[reviewer_email],
        body=body
    )
    
    # إضافة المرفق إذا كان موجوداً
    if file_data and filename:
        try:
            msg.attach(
                filename=filename,
                content_type='application/pdf',
                data=file_data
            )
            print(f"📎 تم إرفاق الملف: {filename}")
        except Exception as e:
            print(f"⚠️ خطأ في إرفاق الملف: {e}")
    
    try:
        mail.send(msg)
        print(f"✅ تم إرسال الإيميل إلى {reviewer_email} مع المرفق")
        
        # تسجيل الإيميل في قاعدة البيانات
        email_log = EmailLog(
            recipient=reviewer_email,
            recipient_name=reviewer_name,
            subject=subject,
            body=body,
            paper_id=paper_submission.id,
            email_type='review_request',
            status='sent',
            sent_at=datetime.utcnow()
        )
        db.session.add(email_log)
        
        # تحديث حالة إرسال الإيميل في الورقة
        paper_submission.email_sent_status = True
        paper_submission.email_sent_at = datetime.utcnow()
        
        db.session.commit()
        
        return {'success': True}
        
    except Exception as e:
        print(f"❌ فشل إرسال الإيميل إلى {reviewer_email}: {str(e)}")
        
        # تسجيل الفشل
        email_log = EmailLog(
            recipient=reviewer_email,
            recipient_name=reviewer_name,
            subject=subject,
            body=body,
            paper_id=paper_submission.id,
            email_type='review_request',
            status='failed',
            error_message=str(e)
        )
        db.session.add(email_log)
        db.session.commit()
        
        return {'success': False, 'error': str(e)}


def get_reviewer_emails_by_track(track):
    """
    الحصول على قائمة إيميلات المحكمين حسب التخصص من قاعدة البيانات
    """
    # تعيين التخصصات إلى المفاتيح الصحيحة
    track_mapping = {
        'energy': 'energy',
        'renewable_energy': 'energy',
        'nanotechnology': 'nanotechnology',
        'advanced_materials': 'nanotechnology',
        'biology': 'biology',
        'biotech': 'biology',
        'geology': 'geology',
        'statistics': 'statistics',
        'chemistry': 'chemistry',
    }
    
    key = track_mapping.get(track, track)
    
    # البحث عن المحكمين في قاعدة البيانات حسب التخصص
    reviewers = Reviewer.query.filter(
        Reviewer.specialties.like(f'%{key}%')
    ).all()
    
    # إرجاع قائمة الإيميلات
    emails = [r.email for r in reviewers if r.email]
    
    # إذا لم يتم العثور على محكمين، استخدم الإيميلات الافتراضية
    if not emails:
        default_emails = {
            'energy': ['abdullah2803@tu.edu.ye', 'adnan.alnehia@tu.edu.ye'],
            'nanotechnology': ['abdullah2803@tu.edu.ye', 'adnan.alnehia@tu.edu.ye'],
            'biology': ['sallam27@tu.edu.ye'],
            'geology': ['ayman_Khalf@tu.edu.ye'],
            'statistics': ['alaoshm@tu.edu.ye'],
            'chemistry': ['alqawatimohammed@gmail.com'],
        }
        emails = default_emails.get(key, [])
        print(f"⚠️ تم استخدام الإيميلات الافتراضية للتخصص {key}: {emails}")
    
    print(f"📧 إيميلات المحكمين للتخصص {key}: {emails}")
    return emails


def get_reviewer_name_by_email(email):
    """
    الحصول على اسم المحكم من خلال بريده الإلكتروني
    """
    # البحث في قاعدة البيانات أولاً
    reviewer = Reviewer.query.filter_by(email=email).first()
    if reviewer:
        return reviewer.name
    
    # إذا لم يوجد، استخدم القائمة الافتراضية
    default_names = {
        'abdullah2803@tu.edu.ye': 'Prof. Dr. Abdullah A. A. Ahmed',
        'adnan.alnehia@tu.edu.ye': 'Dr. Adnan Radman Al-Nehia',
        'sallam27@tu.edu.ye': 'Dr. Hussein Khaleel',
        'ayman_Khalf@tu.edu.ye': 'Dr. Ayman ABDELSABOUR Ahmed Khalf',
        'alqawatimohammed@gmail.com': 'د. محمد القواتي',
        'alaoshm@tu.edu.ye': 'أ. محمد العوش'
    }
    return default_names.get(email, 'المحكم المحترم')


def process_full_paper_submission(form, uploaded_file, user_id=None):
    """
    معالجة كاملة لتقديم بحث جديد (رفع إلى Drive + حفظ في DB + إرسال إيميل للمحكم)
    """
    # 1. قراءة محتوى الملف للإرفاق قبل رفعه إلى Drive
    file_content = uploaded_file.read()
    file_name = uploaded_file.filename
    uploaded_file.seek(0)  # إعادة المؤشر للبداية لرفع الملف إلى Drive
    
    # 2. إنشاء رقم تتبع فريد
    tracking_id = generate_tracking_id()
    
    # 3. رفع الملف إلى Google Drive
    drive_result = upload_paper_to_drive_and_save(
        file_stream=uploaded_file,
        filename=uploaded_file.filename,
        tracking_id=tracking_id,
        track=form.track.data
    )
    
    if not drive_result['success']:
        return {
            'success': False,
            'error': drive_result.get('error', 'فشل رفع الملف إلى Google Drive')
        }
    
    # 4. إعداد بيانات النموذج
    form_data = {
        'title': form.title.data,
        'title_en': form.title_en.data if hasattr(form, 'title_en') else '',
        'abstract': form.abstract.data,
        'abstract_en': form.abstract_en.data if hasattr(form, 'abstract_en') else '',
        'keywords': form.keywords.data,
        'submission_type': form.submission_type.data if hasattr(form, 'submission_type') else 'paper',
        'track': form.track.data,
        'main_author_name': form.main_author_name.data,
        'main_author_email': form.main_author_email.data,
        'main_author_phone': form.main_author_phone.data,
        'main_author_affiliation': form.main_author_affiliation.data,
        'co_authors': form.co_authors.data if hasattr(form, 'co_authors') else '',
        'paper_file_filename': uploaded_file.filename
    }
    
    # 5. إنشاء سجل في قاعدة البيانات
    submission = create_paper_submission(form_data, drive_result, tracking_id, user_id)
    
    # 6. إرسال إيميل تأكيد للباحث
    try:
        send_paper_confirmation_email(submission)
        print(f"✅ تم إرسال إيميل التأكيد إلى {submission.main_author_email}")
    except Exception as e:
        print(f"❌ خطأ في إرسال إيميل التأكيد: {e}")
    
    # 7. الحصول على إيميلات المحكمين حسب التخصص
    reviewer_emails = get_reviewer_emails_by_track(form.track.data)
    print(f"📧 إيميلات المحكمين للتخصص {form.track.data}: {reviewer_emails}")
    
    # 8. إرسال إيميل لكل محكم وتعيينه (مع مرفق الملف)
    assigned_reviewers = []
    for reviewer_email in reviewer_emails:
        if reviewer_email:
            reviewer_name = get_reviewer_name_by_email(reviewer_email)
            print(f"📧 جاري إرسال الإيميل إلى {reviewer_email} ({reviewer_name})")
            
            # تعيين المحكم
            assignment = assign_reviewer_to_paper(submission.id, reviewer_email, reviewer_name)
            
            # إرسال إيميل للمحكم مع المرفق
            email_result = send_paper_to_reviewer_email(
                submission, 
                reviewer_email, 
                reviewer_name,
                file_data=file_content,  # محتوى الملف للإرفاق
                filename=file_name        # اسم الملف للإرفاق
            )
            
            assigned_reviewers.append({
                'email': reviewer_email,
                'name': reviewer_name,
                'success': email_result['success']
            })
    
    return {
        'success': True,
        'tracking_id': tracking_id,
        'submission_id': submission.id,
        'assigned_reviewers': assigned_reviewers,
        'drive_file_id': drive_result['file_id'],
        'view_link': drive_result['view_link'],
        'download_link': drive_result['download_link']
    }