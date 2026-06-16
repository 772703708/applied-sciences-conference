from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from models import User, Paper, PaperSubmission, Speaker, Sponsor, News, Event, ContactMessage, Setting, Gallery, Track, FAQ, ReviewerAssignment, EmailLog, Reviewer
from forms import NewsForm, SpeakerForm, SponsorForm, SettingsForm
from utils import admin_required
from services.services import save_uploaded_image, delete_old_file, send_status_update_email, send_paper_to_reviewer_email, assign_reviewer_to_paper
from datetime import datetime
import os
import json

bp = Blueprint('admin', __name__, url_prefix='/admin')


# ==================== Dashboard ====================
@bp.route('/')
@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """لوحة التحكم الرئيسية"""
    stats = {
        'total_papers': PaperSubmission.query.count(),
        'pending_papers': PaperSubmission.query.filter_by(status='pending').count(),
        'under_review': PaperSubmission.query.filter_by(status='under_review').count(),
        'accepted_papers': PaperSubmission.query.filter_by(status='accepted').count(),
        'rejected_papers': PaperSubmission.query.filter_by(status='rejected').count(),
        'total_speakers': Speaker.query.count(),
        'total_sponsors': Sponsor.query.filter_by(is_active=True).count(),
        'total_news': News.query.count(),
        'unread_contacts': ContactMessage.query.filter_by(is_read=False).count(),
        'total_users': User.query.count(),
        'total_events': Event.query.count()
    }
    
    recent_papers = PaperSubmission.query.order_by(PaperSubmission.submitted_at.desc()).limit(5).all()
    recent_contacts = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all()
    recent_news = News.query.order_by(News.created_at.desc()).limit(5).all()
    
    papers_track_stats = {
        'energy': PaperSubmission.query.filter_by(track='energy').count(),
        'nanotechnology': PaperSubmission.query.filter_by(track='nanotechnology').count(),
        'biology': PaperSubmission.query.filter_by(track='biology').count(),
        'geology': PaperSubmission.query.filter_by(track='geology').count(),
        'statistics': PaperSubmission.query.filter_by(track='statistics').count(),
        'chemistry': PaperSubmission.query.filter_by(track='chemistry').count(),
    }
    
    papers_status_stats = {
        'pending': stats['pending_papers'],
        'underReview': stats['under_review'],
        'accepted': stats['accepted_papers'],
        'rejected': stats['rejected_papers']
    }
    
    return render_template('admin/dashboard.html', 
                         dashboardStats=stats,
                         papersStatusStats=papers_status_stats,
                         papersTrackStats=papers_track_stats,
                         recentPapers=recent_papers,
                         recentContacts=recent_contacts,
                         recentNews=recent_news)


# ==================== Participants Management ====================
@bp.route('/participants')
@login_required
@admin_required
def participants():
    """إدارة المشاركين (جميع الأبحاث المقدمة)"""
    status_filter = request.args.get('status', 'all')
    track_filter = request.args.get('track', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = PaperSubmission.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if track_filter != 'all':
        query = query.filter_by(track=track_filter)
    
    participants_list = query.order_by(PaperSubmission.submitted_at.desc()).paginate(page=page, per_page=per_page)
    
    status_counts = {
        'all': PaperSubmission.query.count(),
        'pending': PaperSubmission.query.filter_by(status='pending').count(),
        'under_review': PaperSubmission.query.filter_by(status='under_review').count(),
        'accepted': PaperSubmission.query.filter_by(status='accepted').count(),
        'rejected': PaperSubmission.query.filter_by(status='rejected').count(),
        'revision_required': PaperSubmission.query.filter_by(status='revision_required').count()
    }
    
    return render_template('admin/participants.html', 
                         participants=participants_list,
                         status_filter=status_filter,
                         track_filter=track_filter,
                         status_counts=status_counts)


@bp.route('/participants/<int:participant_id>/view')
@login_required
@admin_required
def view_participant(participant_id):
    """عرض تفاصيل المشارك والبحث"""
    participant = PaperSubmission.query.get_or_404(participant_id)
    reviewers = Reviewer.query.all()
    
    co_authors = []
    if participant.co_authors:
        try:
            co_authors = json.loads(participant.co_authors)
        except:
            co_authors = []
    
    reviewer_assignments = ReviewerAssignment.query.filter_by(paper_id=participant.id).all()
    
    return render_template('admin/view_participant.html', 
                         participant=participant, 
                         co_authors=co_authors, 
                         reviewers=reviewers,
                         reviewer_assignments=reviewer_assignments)


@bp.route('/participants/<int:participant_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_participant_status(participant_id):
    """تحديث حالة البحث"""
    participant = PaperSubmission.query.get_or_404(participant_id)
    new_status = request.form.get('status')
    reviewer_notes = request.form.get('reviewer_notes')
    
    old_status = participant.status
    participant.status = new_status
    
    if reviewer_notes:
        participant.reviewer_notes = reviewer_notes
    
    db.session.commit()
    
    try:
        send_status_update_email(participant, old_status, new_status)
    except Exception as e:
        print(f"خطأ في إرسال البريد: {e}")
    
    flash(f'تم تحديث حالة المشارك {participant.tracking_id} إلى {new_status}', 'success')
    return redirect(url_for('admin.view_participant', participant_id=participant_id))


@bp.route('/participants/<int:participant_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_participant(participant_id):
    """حذف مشارك وبحثه"""
    participant = PaperSubmission.query.get_or_404(participant_id)
    ReviewerAssignment.query.filter_by(paper_id=participant.id).delete()
    EmailLog.query.filter_by(paper_id=participant.id).delete()
    tracking_id = participant.tracking_id
    db.session.delete(participant)
    db.session.commit()
    flash(f'تم حذف المشارك {tracking_id} بنجاح', 'success')
    return redirect(url_for('admin.participants'))


# ==================== Assign Reviewer to Participant ====================
@bp.route('/participants/<int:participant_id>/assign-reviewer', methods=['POST'])
@login_required
@admin_required
def assign_reviewer_to_participant(participant_id):
    """تعيين محكم للبحث"""
    participant = PaperSubmission.query.get_or_404(participant_id)
    reviewer_email = request.form.get('reviewer_email')
    
    if not reviewer_email:
        flash('يرجى اختيار محكم', 'danger')
        return redirect(url_for('admin.view_participant', participant_id=participant_id))
    
    # التحقق من وجود المحكم
    reviewer = Reviewer.query.filter_by(email=reviewer_email).first()
    if not reviewer:
        flash('المحكم غير موجود', 'danger')
        return redirect(url_for('admin.view_participant', participant_id=participant_id))
    
    # التحقق من عدم وجود تعيين سابق
    existing = ReviewerAssignment.query.filter_by(
        paper_id=participant.id, 
        reviewer_email=reviewer_email
    ).first()
    
    if existing:
        flash('تم تعيين هذا المحكم مسبقاً لهذا البحث', 'warning')
        return redirect(url_for('admin.view_participant', participant_id=participant_id))
    
    # تعيين المحكم
    assignment = assign_reviewer_to_paper(participant.id, reviewer_email, reviewer.name)
    
    # إرسال إيميل للمحكم (مع مرفق الملف)
    try:
        # قراءة الملف من Google Drive
        import requests
        file_response = requests.get(participant.gdrive_download_link)
        file_data = file_response.content if file_response.status_code == 200 else None
        
        from services.services import send_paper_to_reviewer_email
        email_result = send_paper_to_reviewer_email(
            participant, 
            reviewer_email, 
            reviewer.name,
            file_data=file_data,
            filename=participant.original_filename or 'paper.pdf'
        )
        
        if email_result['success']:
            flash(f'تم تعيين المحكم {reviewer.name} وإرسال الإيميل بنجاح', 'success')
        else:
            flash(f'تم تعيين المحكم {reviewer.name} ولكن حدث خطأ في إرسال الإيميل', 'warning')
    except Exception as e:
        flash(f'تم تعيين المحكم {reviewer.name} ولكن حدث خطأ في إرسال الإيميل: {str(e)}', 'warning')
    
    return redirect(url_for('admin.view_participant', participant_id=participant_id))


# ==================== Reviewers Management (جدول منفصل Reviewer) ====================
@bp.route('/reviewers')
@login_required
@admin_required
def reviewers():
    """إدارة المحكمين"""
    reviewers_list = Reviewer.query.order_by(Reviewer.created_at.desc()).all()
    return render_template('admin/reviewers.html', reviewers=reviewers_list)


@bp.route('/reviewers/add', methods=['POST'])
@login_required
@admin_required
def add_reviewer():
    """إضافة محكم جديد"""
    name = request.form.get('name')
    degree = request.form.get('degree')
    email = request.form.get('email')
    phone = request.form.get('phone')
    specialties = request.form.get('specialties', '')
    bio = request.form.get('bio', '')
    
    if not name or not email:
        flash('الاسم والبريد الإلكتروني مطلوبان', 'danger')
        return redirect(url_for('admin.reviewers'))
    
    existing = Reviewer.query.filter_by(email=email).first()
    if existing:
        flash('البريد الإلكتروني موجود مسبقاً', 'danger')
        return redirect(url_for('admin.reviewers'))
    
    reviewer = Reviewer(
        name=name,
        degree=degree,
        email=email,
        phone=phone,
        specialties=specialties,
        bio=bio
    )
    db.session.add(reviewer)
    db.session.commit()
    
    flash(f'تم إضافة المحكم {name} بنجاح', 'success')
    return redirect(url_for('admin.reviewers'))


@bp.route('/reviewers/edit/<int:reviewer_id>', methods=['POST'])
@login_required
@admin_required
def edit_reviewer(reviewer_id):
    """تعديل بيانات محكم"""
    reviewer = Reviewer.query.get_or_404(reviewer_id)
    
    reviewer.name = request.form.get('name')
    reviewer.degree = request.form.get('degree')
    reviewer.email = request.form.get('email')
    reviewer.phone = request.form.get('phone')
    reviewer.specialties = request.form.get('specialties', '')
    reviewer.bio = request.form.get('bio', '')
    
    db.session.commit()
    flash(f'تم تحديث بيانات المحكم {reviewer.name} بنجاح', 'success')
    return redirect(url_for('admin.reviewers'))


@bp.route('/reviewers/delete/<int:reviewer_id>', methods=['POST'])
@login_required
@admin_required
def delete_reviewer(reviewer_id):
    """حذف محكم"""
    reviewer = Reviewer.query.get_or_404(reviewer_id)
    name = reviewer.name
    db.session.delete(reviewer)
    db.session.commit()
    flash(f'تم حذف المحكم {name} بنجاح', 'success')
    return redirect(url_for('admin.reviewers'))


# ==================== Papers Management (النموذج القديم) ====================
@bp.route('/papers')
@login_required
@admin_required
def papers():
    """إدارة الأبحاث (النموذج القديم)"""
    status_filter = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = Paper.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    papers_list = query.order_by(Paper.submitted_at.desc()).paginate(page=page, per_page=per_page)
    
    status_counts = {
        'all': Paper.query.count(),
        'pending': Paper.query.filter_by(status='pending').count(),
        'under_review': Paper.query.filter_by(status='under_review').count(),
        'accepted': Paper.query.filter_by(status='accepted').count(),
        'rejected': Paper.query.filter_by(status='rejected').count(),
        'revision_required': Paper.query.filter_by(status='revision_required').count()
    }
    
    return render_template('admin/papers.html', 
                         papers=papers_list, 
                         status_filter=status_filter,
                         status_counts=status_counts)


@bp.route('/papers/<int:paper_id>/view')
@login_required
@admin_required
def view_paper(paper_id):
    """عرض تفاصيل البحث (النموذج القديم)"""
    paper = Paper.query.get_or_404(paper_id)
    reviewers = Reviewer.query.all()
    
    co_authors = []
    if paper.co_authors:
        try:
            co_authors = json.loads(paper.co_authors)
        except:
            co_authors = []
    
    return render_template('admin/view_paper.html', paper=paper, co_authors=co_authors, reviewers=reviewers)


@bp.route('/papers/<int:paper_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_paper_status(paper_id):
    """تحديث حالة البحث (النموذج القديم)"""
    paper = Paper.query.get_or_404(paper_id)
    new_status = request.form.get('status')
    reviewer_notes = request.form.get('reviewer_notes')
    
    old_status = paper.status
    paper.status = new_status
    
    if reviewer_notes:
        paper.reviewer_notes = reviewer_notes
    
    db.session.commit()
    
    try:
        send_status_update_email(paper, old_status, new_status)
    except Exception as e:
        print(f"خطأ في إرسال البريد: {e}")
    
    flash(f'تم تحديث حالة البحث {paper.tracking_id} إلى {new_status}', 'success')
    return redirect(url_for('admin.view_paper', paper_id=paper_id))


@bp.route('/papers/<int:paper_id>/delete')
@login_required
@admin_required
def delete_paper(paper_id):
    """حذف البحث (النموذج القديم)"""
    paper = Paper.query.get_or_404(paper_id)
    
    if paper.file_path:
        delete_old_file(paper.file_path)
    
    tracking_id = paper.tracking_id
    db.session.delete(paper)
    db.session.commit()
    
    flash(f'تم حذف البحث {tracking_id} بنجاح', 'success')
    return redirect(url_for('admin.papers'))


# ==================== Speakers Management ====================
@bp.route('/speakers')
@login_required
@admin_required
def speakers():
    """إدارة المتحدثين"""
    speakers_list = Speaker.query.order_by(Speaker.order).all()
    return render_template('admin/speakers.html', speakers=speakers_list)


@bp.route('/speakers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_speaker():
    """إضافة متحدث جديد"""
    form = SpeakerForm()
    if form.validate_on_submit():
        speaker = Speaker(
            name=form.name.data,
            name_en=form.name_en.data,
            title=form.title.data,
            title_en=form.title_en.data,
            affiliation=form.affiliation.data,
            bio=form.bio.data,
            bio_en=form.bio_en.data,
            email=form.email.data,
            linkedin=form.linkedin.data,
            twitter=form.twitter.data,
            is_keynote=form.is_keynote.data,
            order=form.order.data
        )
        
        if form.photo.data:
            photo_path = save_uploaded_image(form.photo.data, 'speakers_photos')
            speaker.photo = photo_path
        
        db.session.add(speaker)
        db.session.commit()
        
        flash('تم إضافة المتحدث بنجاح', 'success')
        return redirect(url_for('admin.speakers'))
    
    return render_template('admin/speaker_form.html', form=form, title='إضافة متحدث')


@bp.route('/speakers/<int:speaker_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_speaker(speaker_id):
    """تعديل متحدث"""
    speaker = Speaker.query.get_or_404(speaker_id)
    form = SpeakerForm(obj=speaker)
    
    if form.validate_on_submit():
        speaker.name = form.name.data
        speaker.name_en = form.name_en.data
        speaker.title = form.title.data
        speaker.title_en = form.title_en.data
        speaker.affiliation = form.affiliation.data
        speaker.bio = form.bio.data
        speaker.bio_en = form.bio_en.data
        speaker.email = form.email.data
        speaker.linkedin = form.linkedin.data
        speaker.twitter = form.twitter.data
        speaker.is_keynote = form.is_keynote.data
        speaker.order = form.order.data
        
        if form.photo.data:
            if speaker.photo:
                delete_old_file(speaker.photo)
            photo_path = save_uploaded_image(form.photo.data, 'speakers_photos')
            speaker.photo = photo_path
        
        db.session.commit()
        flash('تم تحديث المتحدث بنجاح', 'success')
        return redirect(url_for('admin.speakers'))
    
    return render_template('admin/speaker_form.html', form=form, title='تعديل متحدث', speaker=speaker)


@bp.route('/speakers/<int:speaker_id>/delete')
@login_required
@admin_required
def delete_speaker(speaker_id):
    """حذف متحدث"""
    speaker = Speaker.query.get_or_404(speaker_id)
    if speaker.photo:
        delete_old_file(speaker.photo)
    db.session.delete(speaker)
    db.session.commit()
    flash('تم حذف المتحدث بنجاح', 'success')
    return redirect(url_for('admin.speakers'))


# ==================== News Management ====================
@bp.route('/news')
@login_required
@admin_required
def news():
    """إدارة الأخبار"""
    news_list = News.query.order_by(News.created_at.desc()).all()
    return render_template('admin/news.html', news_list=news_list)


@bp.route('/news/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_news():
    """إضافة خبر جديد"""
    form = NewsForm()
    if form.validate_on_submit():
        news = News(
            title=form.title.data,
            title_en=form.title_en.data,
            slug=form.slug.data,
            content=form.content.data,
            content_en=form.content_en.data,
            excerpt=form.excerpt.data,
            author_id=current_user.id,
            is_published=form.is_published.data
        )
        
        if form.image.data:
            image_path = save_uploaded_image(form.image.data, 'news_images')
            news.image = image_path
        
        db.session.add(news)
        db.session.commit()
        
        flash('تم إضافة الخبر بنجاح', 'success')
        return redirect(url_for('admin.news'))
    
    return render_template('admin/news_form.html', form=form, title='إضافة خبر')


@bp.route('/news/<int:news_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_news(news_id):
    """تعديل خبر"""
    news = News.query.get_or_404(news_id)
    form = NewsForm(obj=news)
    
    if form.validate_on_submit():
        news.title = form.title.data
        news.title_en = form.title_en.data
        news.slug = form.slug.data
        news.content = form.content.data
        news.content_en = form.content_en.data
        news.excerpt = form.excerpt.data
        news.is_published = form.is_published.data
        
        if form.image.data:
            if news.image:
                delete_old_file(news.image)
            image_path = save_uploaded_image(form.image.data, 'news_images')
            news.image = image_path
        
        db.session.commit()
        flash('تم تحديث الخبر بنجاح', 'success')
        return redirect(url_for('admin.news'))
    
    return render_template('admin/news_form.html', form=form, title='تعديل خبر', news=news)


@bp.route('/news/<int:news_id>/delete')
@login_required
@admin_required
def delete_news(news_id):
    """حذف خبر"""
    news = News.query.get_or_404(news_id)
    if news.image:
        delete_old_file(news.image)
    db.session.delete(news)
    db.session.commit()
    flash('تم حذف الخبر بنجاح', 'success')
    return redirect(url_for('admin.news'))


# ==================== Events Management ====================
@bp.route('/events')
@login_required
@admin_required
def events():
    """إدارة الفعاليات"""
    events_list = Event.query.order_by(Event.start_time).all()
    speakers = Speaker.query.all()
    return render_template('admin/events.html', events=events_list, speakers=speakers)


@bp.route('/events/add', methods=['POST'])
@login_required
@admin_required
def add_event():
    """إضافة فعالية جديدة"""
    event = Event(
        title=request.form.get('title'),
        title_en=request.form.get('title_en', ''),
        description=request.form.get('description', ''),
        location=request.form.get('location', ''),
        start_time=datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M'),
        end_time=datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M') if request.form.get('end_time') else None,
        speaker_id=int(request.form.get('speaker_id')) if request.form.get('speaker_id') else None,
        event_type=request.form.get('event_type'),
        order=int(request.form.get('order', 0))
    )
    db.session.add(event)
    db.session.commit()
    flash('تم إضافة الفعالية بنجاح', 'success')
    return redirect(url_for('admin.events'))


@bp.route('/events/<int:event_id>/delete')
@login_required
@admin_required
def delete_event(event_id):
    """حذف فعالية"""
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash('تم حذف الفعالية بنجاح', 'success')
    return redirect(url_for('admin.events'))


@bp.route('/events/edit/<int:event_id>', methods=['POST'])
@login_required
@admin_required
def edit_event(event_id):
    """تعديل فعالية"""
    event = Event.query.get_or_404(event_id)
    
    event.title = request.form.get('title')
    event.title_en = request.form.get('title_en', '')
    event.description = request.form.get('description', '')
    event.location = request.form.get('location', '')
    event.event_type = request.form.get('event_type')
    event.order = int(request.form.get('order', 0))
    
    if request.form.get('start_time'):
        event.start_time = datetime.strptime(request.form.get('start_time'), '%Y-%m-%dT%H:%M')
    if request.form.get('end_time'):
        event.end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
    
    speaker_id = request.form.get('speaker_id')
    event.speaker_id = int(speaker_id) if speaker_id else None
    
    db.session.commit()
    flash('تم تحديث الفعالية بنجاح', 'success')
    return redirect(url_for('admin.events'))


# ==================== Contacts Management ====================
@bp.route('/contacts')
@login_required
@admin_required
def contacts():
    """إدارة رسائل الاتصال"""
    contacts_list = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/contacts.html', contacts=contacts_list)


@bp.route('/contacts/<int:contact_id>/mark-read')
@login_required
@admin_required
def mark_contact_read(contact_id):
    """تعليم الرسالة كمقروءة"""
    contact = ContactMessage.query.get_or_404(contact_id)
    contact.is_read = True
    db.session.commit()
    flash('تم تعليم الرسالة كمقروءة', 'success')
    return redirect(url_for('admin.contacts'))


@bp.route('/contacts/<int:contact_id>/delete')
@login_required
@admin_required
def delete_contact(contact_id):
    """حذف رسالة"""
    contact = ContactMessage.query.get_or_404(contact_id)
    db.session.delete(contact)
    db.session.commit()
    flash('تم حذف الرسالة', 'success')
    return redirect(url_for('admin.contacts'))


@bp.route('/contacts/<int:contact_id>/reply', methods=['POST'])
@login_required
@admin_required
def reply_contact(contact_id):
    """الرد على رسالة الاتصال"""
    import json
    from flask_mail import Message
    from app import mail
    
    data = json.loads(request.data)
    reply_text = data.get('reply')
    recipient_email = data.get('email')
    recipient_name = data.get('name')
    
    if not reply_text or not recipient_email:
        return jsonify({'success': False, 'error': 'بيانات غير مكتملة'})
    
    try:
        subject = "رد على استفسارك - المؤتمر العلمي الدولي الأول"
        body = f"""
        عزيزي {recipient_name}،
        
        نشكرك على تواصلك مع المؤتمر العلمي الدولي الأول.
        
        رد اللجنة المنظمة:
        ----------------------------------------
        {reply_text}
        ----------------------------------------
        
        لمزيد من الاستفسارات، يمكنك التواصل معنا مرة أخرى.
        
        مع خالص التحية،
        اللجنة المنظمة - المؤتمر العلمي الدولي الأول
        كلية العلوم التطبيقية - جامعة ذمار
        """
        
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=body
        )
        mail.send(msg)
        
        # تسجيل أن تم الرد
        contact = ContactMessage.query.get(contact_id)
        if contact:
            contact.replied = True
            db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ==================== Users Management ====================
@bp.route('/users')
@login_required
@admin_required
def users():
    """إدارة المستخدمين"""
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users_list)


@bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    """إضافة مستخدم جديد"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        affiliation = request.form.get('affiliation', '')
        
        existing = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing:
            flash('البريد الإلكتروني أو اسم المستخدم موجود مسبقاً', 'danger')
            return redirect(url_for('admin.add_user'))
        
        new_user = User(
            username=username,
            email=email,
            role=role,
            is_active=True,
            affiliation=affiliation
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'تم إضافة المستخدم {username} بنجاح', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_form.html', title='إضافة مستخدم جديد')


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """تعديل مستخدم"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.affiliation = request.form.get('affiliation', '')
        user.role = request.form.get('role', 'user')
        
        new_password = request.form.get('password')
        if new_password:
            user.set_password(new_password)
        
        db.session.commit()
        flash(f'تم تحديث المستخدم {user.username} بنجاح', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_form.html', title='تعديل مستخدم', user=user)


@bp.route('/users/<int:user_id>/toggle-active')
@login_required
@admin_required
def toggle_user_active(user_id):
    """تفعيل/تعطيل مستخدم"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('لا يمكن تعطيل حسابك الحالي', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    status = 'مفعل' if user.is_active else 'معطل'
    flash(f'تم {status} المستخدم {user.username}', 'success')
    return redirect(url_for('admin.users'))


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """حذف مستخدم"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('لا يمكن حذف حسابك الحالي', 'danger')
        return redirect(url_for('admin.users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'تم حذف المستخدم {username} بنجاح', 'success')
    return redirect(url_for('admin.users'))


# ==================== Settings ====================
@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """إعدادات النظام"""
    settings = Setting.query.first()
    if not settings:
        settings = Setting()
        db.session.add(settings)
    
    form = SettingsForm(obj=settings)
    
    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        flash('تم حفظ الإعدادات بنجاح', 'success')
        return redirect(url_for('admin.settings'))
    
    return render_template('admin/settings.html', form=form, settings=settings)


# ==================== Check Email Status ====================
@bp.route('/check-email-status/<int:paper_id>')
@login_required
@admin_required
def check_email_status(paper_id):
    """التحقق من حالة إرسال الإيميل للبحث"""
    paper = PaperSubmission.query.get_or_404(paper_id)
    
    # جلب سجلات الإيميلات
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