from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from app import db
from forms import ContactForm
from models import ContactMessage, Setting
from services.services import send_contact_acknowledgement

bp = Blueprint('contact', __name__)

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """صفحة الاتصال"""
    form = ContactForm()
    settings = Setting.query.first()
    
    if form.validate_on_submit():
        # حفظ الرسالة في قاعدة البيانات
        message = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            subject=form.subject.data,
            message=form.message.data
        )
        
        db.session.add(message)
        db.session.commit()
        
        # إرسال بريد إقرار
        try:
            send_contact_acknowledgement(form.name.data, form.email.data, form.subject.data)
        except Exception as e:
            print(f"خطأ في إرسال البريد: {e}")
        
        flash('تم إرسال رسالتك بنجاح. سنقوم بالرد عليك قريباً.', 'success')
        return redirect(url_for('contact.contact'))
    
    # معلومات الاتصال من الإعدادات
    contact_info = {
        'email': settings.contact_email if settings else '',
        'phone': settings.contact_phone if settings else '',
        'whatsapp': settings.whatsapp_number if settings else '',
        'address': settings.address if settings else '',
        'facebook': settings.facebook_url if settings else '',
        'twitter': settings.twitter_url if settings else '',
        'linkedin': settings.linkedin_url if settings else '',
        'youtube': settings.youtube_url if settings else ''
    }
    
    return render_template('main/contact.html', form=form, contact_info=contact_info)

@bp.route('/api/contact', methods=['POST'])
def api_contact():
    """API للاتصال (للاستخدام مع AJAX)"""
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('email') or not data.get('message'):
        return jsonify({'success': False, 'error': 'بيانات غير مكتملة'}), 400
    
    message = ContactMessage(
        name=data['name'],
        email=data['email'],
        phone=data.get('phone', ''),
        subject=data.get('subject', ''),
        message=data['message']
    )
    
    db.session.add(message)
    db.session.commit()
    
    try:
        send_contact_acknowledgement(data['name'], data['email'], data.get('subject', ''))
    except Exception as e:
        print(f"خطأ في إرسال البريد: {e}")
    
    return jsonify({'success': True, 'message': 'تم إرسال رسالتك بنجاح'})