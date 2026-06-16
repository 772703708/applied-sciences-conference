from functools import wraps
from flask import flash, redirect, url_for, session, request
from flask_login import current_user
import re
import os
from werkzeug.utils import secure_filename
from datetime import datetime

def admin_required(f):
    """Decorator للتحقق من صلاحيات المشرف"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('غير مصرح بالوصول. هذه الصفحة مخصصة للمشرفين فقط.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def reviewer_required(f):
    """Decorator للتحقق من صلاحيات المحكم"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_admin() or current_user.is_reviewer()):
            flash('غير مصرح بالوصول.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_tracking_id():
    """إنشاء رقم تتبع فريد للبحث"""
    from datetime import datetime
    import random
    import string
    
    timestamp = datetime.now().strftime('%y%m%d')
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    tracking_id = f'PAP{timestamp}{random_chars}'
    return tracking_id

def allowed_file(filename, allowed_extensions):
    """التحقق من صيغة الملف"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def secure_filename_ar(filename):
    """تأمين اسم الملف مع دعم العربية"""
    name, ext = os.path.splitext(filename)
    name = secure_filename(name) if name else 'file'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{name}_{timestamp}{ext}"

def validate_arabic_text(text):
    """التحقق من صحة النص العربي"""
    arabic_pattern = re.compile(r'^[\u0600-\u06FF\s\d\W]+$')
    return bool(arabic_pattern.match(text)) if text else True

def get_rtl_direction(text):
    """تحديد اتجاه النص (RTL/LTR)"""
    arabic_range = range(0x0600, 0x06FF + 1)
    if any(ord(char) in arabic_range for char in text[:100]):
        return 'rtl'
    return 'ltr'

def format_date_ar(date):
    """تنسيق التاريخ بالعربية"""
    if not date:
        return ''
    
    months_ar = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
    
    return f"{date.day} {months_ar[date.month - 1]} {date.year}"

def truncate_text(text, length=150):
    """اقتطاع النص مع إضافة ..."""
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0] + '...'

def get_file_size(file_path):
    """الحصول على حجم الملف بشكل مقروء"""
    size = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"

def sanitize_html(content):
    """تنظيف HTML من النصوص الضارة"""
    import bleach
    allowed_tags = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4',
        'ul', 'ol', 'li', 'a', 'img', 'div', 'span', 'table',
        'tr', 'td', 'th', 'thead', 'tbody'
    ]
    allowed_attrs = {
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'width', 'height'],
        'div': ['class'],
        'span': ['class']
    }
    return bleach.clean(content, tags=allowed_tags, attributes=allowed_attrs, strip=True)