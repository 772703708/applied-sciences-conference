from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from app import db, mail
from forms import PaperSubmissionForm, PaperTrackingForm
from models import User, Paper, PaperSubmission, Track, ReviewerAssignment, EmailLog
from services import (
    save_paper_file, 
    send_paper_confirmation_email, 
    get_paper_by_tracking_id,
    get_paper_submission_by_tracking_id,
    process_full_paper_submission,
    upload_paper_to_drive_and_save,
    create_paper_submission,
    assign_reviewer_to_paper,
    send_paper_to_reviewer_email,
    get_reviewer_emails_by_track,
    get_reviewer_name_by_email
)
from utils import generate_tracking_id
from datetime import datetime
import json
import traceback

bp = Blueprint('submission', __name__, url_prefix='/submission')


@bp.route('/submit', methods=['GET', 'POST'])
def submit_paper():
    """
    تقديم بحث جديد - يدعم كلاً من:
    1. النظام القديم (حفظ محلي)
    2. النظام الجديد (Google Drive + إرسال للمحكمين)
    """
    form = PaperSubmissionForm()
    
    # تحميل المسارات المتاحة من قاعدة البيانات أو استخدام الإعدادات
    tracks = Track.query.filter_by(is_active=True).all()
    if tracks:
        form.track.choices = [(t.name, t.name_en or t.name) for t in tracks]
    else:
        form.track.choices = current_app.config.get('TRACK_CHOICES', [
            ('energy', 'الطاقة المستدامة والطاقة المتجددة'),
            ('nanotechnology', 'علم المواد المتقدمة وتكنولوجيا النانو'),
            ('biology', 'العلوم البيولوجية والتكنولوجيا الحيوية'),
            ('geology', 'الجيولوجيا والبيئة والموارد المائية'),
            ('statistics', 'الإحصاء والنمذجة الرياضية'),
            ('chemistry', 'الكيمياء وتطبيقاتها التكنولوجية'),
        ])
    
    if form.validate_on_submit():
        try:
            use_google_drive = current_app.config.get('USE_GOOGLE_DRIVE', True)
            
            if use_google_drive:
                result = process_full_paper_submission(
                    form=form,
                    uploaded_file=form.paper_file.data,
                    user_id=current_user.id if current_user.is_authenticated else None
                )
                
                if result['success']:
                    flash(f'✅ تم تقديم بحثك بنجاح! رقم التتبع: {result["tracking_id"]}', 'success')
                    
                    if result.get('assigned_reviewers'):
                        assigned_count = len(result['assigned_reviewers'])
                        flash(f'📧 تم إرسال طلب التحكيم إلى {assigned_count} محكم(ين)', 'info')
                    
                    # إرسال إيميل للمشرف
                    try:
                        send_admin_notification(result, form)
                    except Exception as e:
                        print(f"خطأ في إرسال إيميل المشرف: {e}")
                    
                    return redirect(url_for('submission.track_paper'))
                else:
                    error_msg = result.get('error', 'فشل في تقديم البحث')
                    flash(f'❌ حدث خطأ: {error_msg}', 'danger')
                    print(f"❌ خطأ في تقديم البحث: {error_msg}")
                    print(traceback.format_exc())
                    return render_template('main/paper_submission.html', form=form, tracks=tracks)
            
            else:
                # النظام القديم
                tracking_id = generate_tracking_id()
                
                co_authors_list = []
                if form.co_authors.data:
                    for line in form.co_authors.data.strip().split('\n'):
                        if line.strip():
                            parts = line.split('-')
                            co_authors_list.append({
                                'name': parts[0].strip() if len(parts) > 0 else '',
                                'email': parts[1].strip() if len(parts) > 1 else '',
                                'affiliation': parts[2].strip() if len(parts) > 2 else ''
                            })
                
                paper_file = form.paper_file.data
                file_path = save_paper_file(paper_file, tracking_id)
                
                paper = Paper(
                    tracking_id=tracking_id,
                    title=form.title.data,
                    title_ar=form.title_ar.data,
                    abstract=form.abstract.data,
                    abstract_ar=form.abstract_ar.data,
                    keywords=form.keywords.data,
                    file_path=file_path,
                    main_author_name=form.main_author_name.data,
                    main_author_email=form.main_author_email.data,
                    main_author_phone=form.main_author_phone.data,
                    main_author_affiliation=form.main_author_affiliation.data,
                    co_authors=json.dumps(co_authors_list, ensure_ascii=False) if co_authors_list else None,
                    track=form.track.data,
                    status='pending'
                )
                
                db.session.add(paper)
                db.session.commit()
                
                try:
                    send_paper_confirmation_email(paper)
                except Exception as e:
                    print(f"خطأ في إرسال البريد: {e}")
                
                flash(f'✅ تم تقديم بحثك بنجاح! رقم التتبع: {tracking_id}', 'success')
                return redirect(url_for('submission.track_paper'))
                
        except Exception as e:
            error_msg = str(e)
            flash(f'❌ حدث خطأ غير متوقع: {error_msg}', 'danger')
            print(f"❌ خطأ غير متوقع: {error_msg}")
            print(traceback.format_exc())
            return render_template('main/paper_submission.html', form=form, tracks=tracks)
    
    if form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'⚠️ خطأ في حقل {field}: {error}', 'danger')
    
    return render_template('main/paper_submission.html', form=form, tracks=tracks)


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


@bp.route('/track', methods=['GET', 'POST'])
def track_paper():
    """تتبع البحث - يدعم كلاً من النموذج القديم والجديد"""
    form = PaperTrackingForm()
    paper = None
    paper_new = None
    tracking_status = None
    
    if form.validate_on_submit():
        paper_new = get_paper_submission_by_tracking_id(form.tracking_id.data, form.email.data)
        
        if not paper_new:
            paper = get_paper_by_tracking_id(form.tracking_id.data, form.email.data)
        
        target_paper = paper_new or paper
        
        if target_paper:
            status_map = {
                'pending': {'text': 'قيد الانتظار', 'color': 'warning', 'icon': 'clock', 'step': 1},
                'under_review': {'text': 'قيد المراجعة', 'color': 'info', 'icon': 'eye', 'step': 2},
                'revision_required': {'text': 'تعديلات مطلوبة', 'color': 'danger', 'icon': 'edit', 'step': 2},
                'accepted': {'text': 'مقبول', 'color': 'success', 'icon': 'check-circle', 'step': 3},
                'rejected': {'text': 'مرفوض', 'color': 'danger', 'icon': 'times-circle', 'step': 3}
            }
            
            tracking_status = status_map.get(target_paper.status, status_map['pending'])
            tracking_status['notes'] = getattr(target_paper, 'reviewer_notes', None)
            
            if paper_new:
                tracking_status['gdrive_view_link'] = paper_new.gdrive_view_link
                tracking_status['submission_type'] = paper_new.submission_type
                tracking_status['email_sent_status'] = paper_new.email_sent_status
        else:
            flash('لا يوجد بحث بهذا الرقم التتبع والبريد الإلكتروني.', 'danger')
    
    return render_template('main/paper_tracking.html', 
                         form=form, 
                         paper=paper, 
                         paper_new=paper_new,
                         tracking_status=tracking_status)


@bp.route('/my-papers')
@login_required
def my_papers():
    """الأبحاث الخاصة بالمستخدم - يدعم كلاً من النموذجين"""
    old_papers = Paper.query.filter_by(main_author_email=current_user.email)\
                        .order_by(Paper.submitted_at.desc()).all()
    
    new_papers = PaperSubmission.query.filter_by(main_author_email=current_user.email)\
                        .order_by(PaperSubmission.submitted_at.desc()).all()
    
    return render_template('auth/my_papers.html', 
                         old_papers=old_papers, 
                         new_papers=new_papers)


@bp.route('/paper/<tracking_id>')
@login_required
def paper_detail(tracking_id):
    """تفاصيل البحث (للمستخدم فقط) - يدعم كلاً من النموذجين"""
    paper_new = PaperSubmission.query.filter_by(tracking_id=tracking_id).first()
    
    paper_old = None
    if not paper_new:
        paper_old = Paper.query.filter_by(tracking_id=tracking_id).first()
    
    target_paper = paper_new or paper_old
    
    if not target_paper:
        flash('البحث غير موجود.', 'danger')
        return redirect(url_for('main.home'))
    
    email_condition = (target_paper.main_author_email == current_user.email)
    if not email_condition and not current_user.is_admin():
        flash('غير مصرح بالوصول إلى هذا البحث.', 'danger')
        return redirect(url_for('main.home'))
    
    co_authors = []
    if target_paper.co_authors:
        co_authors = json.loads(target_paper.co_authors)
    
    reviewer_assignments = []
    if paper_new:
        reviewer_assignments = ReviewerAssignment.query.filter_by(paper_id=paper_new.id).all()
    
    return render_template('auth/paper_detail.html', 
                         paper=target_paper, 
                         paper_new=paper_new,
                         co_authors=co_authors,
                         reviewer_assignments=reviewer_assignments)


@bp.route('/paper/<int:paper_id>/resend-to-reviewers', methods=['POST'])
@login_required
def resend_to_reviewers(paper_id):
    """إعادة إرسال طلب التحكيم إلى المحكمين (للمشرفين فقط)"""
    if not current_user.is_admin():
        flash('غير مصرح بهذا الإجراء.', 'danger')
        return redirect(url_for('main.home'))
    
    paper = PaperSubmission.query.get_or_404(paper_id)
    
    reviewer_emails = get_reviewer_emails_by_track(paper.track)
    
    sent_count = 0
    for reviewer_email in reviewer_emails:
        if reviewer_email:
            reviewer_name = get_reviewer_name_by_email(reviewer_email)
            
            existing = ReviewerAssignment.query.filter_by(
                paper_id=paper.id, 
                reviewer_email=reviewer_email
            ).first()
            
            if not existing:
                assignment = assign_reviewer_to_paper(paper.id, reviewer_email, reviewer_name)
            
            result = send_paper_to_reviewer_email(paper, reviewer_email, reviewer_name)
            if result['success']:
                sent_count += 1
    
    flash(f'✅ تم إعادة إرسال طلب التحكيم إلى {sent_count} محكم(ين)', 'success')
    return redirect(url_for('submission.paper_detail', tracking_id=paper.tracking_id))


@bp.route('/get-drive-link/<tracking_id>')
@login_required
def get_drive_link(tracking_id):
    """الحصول على رابط Google Drive للبحث (للمشرفين)"""
    if not current_user.is_authenticated or not current_user.is_admin():
        return jsonify({'error': 'غير مصرح'}), 403
    
    paper = PaperSubmission.query.filter_by(tracking_id=tracking_id).first()
    if not paper:
        return jsonify({'error': 'غير موجود'}), 404
    
    return jsonify({
        'view_link': paper.gdrive_view_link,
        'download_link': paper.gdrive_download_link,
        'file_id': paper.gdrive_file_id,
        'tracking_id': paper.tracking_id,
        'title': paper.title,
        'author': paper.main_author_name
    })


@bp.route('/check-email-status/<int:paper_id>')
@login_required
def check_email_status(paper_id):
    """التحقق من حالة إرسال الإيميل للبحث (للمشرفين)"""
    if not current_user.is_admin():
        return jsonify({'error': 'غير مصرح'}), 403
    
    paper = PaperSubmission.query.get_or_404(paper_id)
    
    email_logs = EmailLog.query.filter_by(paper_id=paper.id).all()
    
    result = {
        'tracking_id': paper.tracking_id,
        'title': paper.title,
        'email_sent': paper.email_sent_status,
        'email_sent_at': paper.email_sent_at.strftime('%Y-%m-%d %H:%M:%S') if paper.email_sent_at else None,
        'logs': []
    }
    
    for log in email_logs:
        result['logs'].append({
            'recipient': log.recipient,
            'recipient_name': log.recipient_name,
            'email_type': log.email_type,
            'status': log.status,
            'sent_at': log.sent_at.strftime('%Y-%m-%d %H:%M:%S') if log.sent_at else None,
            'error': log.error_message if log.status == 'failed' else None
        })
    
    return jsonify(result)