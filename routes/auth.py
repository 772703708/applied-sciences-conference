from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app import db
from models import User
from forms import LoginForm, RegistrationForm, AdminLoginForm, ProfileEditForm, ChangePasswordForm
from services.services import send_registration_email, send_password_reset_email

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """تسجيل الدخول للمستخدمين العاديين"""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('الحساب غير نشط. يرجى التواصل مع الدعم.', 'danger')
                return render_template('auth/login.html', form=form)
            
            login_user(user, remember=form.remember.data)
            
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            else:
                next_page = request.args.get('next')
                flash(f'مرحباً {user.username}! تم تسجيل الدخول بنجاح.', 'success')
                return redirect(next_page or url_for('main.home'))
        else:
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة.', 'danger')
    
    return render_template('auth/login.html', form=form)

@bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """تسجيل الدخول للوحة التحكم (صفحة منفصلة)"""
    if current_user.is_authenticated and current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.check_password(form.password.data) and user.is_admin():
            login_user(user, remember=form.remember.data)
            flash(f'مرحباً {user.username}! تم تسجيل الدخول إلى لوحة التحكم.', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('بيانات الدخول غير صحيحة أو ليس لديك صلاحيات المشرف.', 'danger')
    
    return render_template('admin/login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """تسجيل مستخدم جديد"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # التحقق من وجود المستخدم
        existing_user = User.query.filter(
            (User.email == form.email.data) | (User.username == form.username.data)
        ).first()
        
        if existing_user:
            flash('البريد الإلكتروني أو اسم المستخدم موجود مسبقاً.', 'danger')
            return render_template('auth/register.html', form=form)
        
        # إنشاء مستخدم جديد
        user = User(
            username=form.username.data,
            email=form.email.data,
            affiliation=form.affiliation.data,
            phone=form.phone.data if form.phone.data else '',
            role='user'
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        # إرسال بريد تأكيد
        try:
            send_registration_email(user)
        except Exception as e:
            print(f"خطأ في إرسال البريد: {e}")
        
        flash('تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    """تسجيل الخروج"""
    logout_user()
    flash('تم تسجيل الخروج بنجاح.', 'info')
    return redirect(url_for('main.home'))

@bp.route('/profile')
@login_required
def profile():
    """صفحة الملف الشخصي"""
    return render_template('auth/profile.html', user=current_user)

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """تعديل الملف الشخصي"""
    form = ProfileEditForm(obj=current_user)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.affiliation = form.affiliation.data
        current_user.phone = form.phone.data
        current_user.bio = form.bio.data
        
        db.session.commit()
        flash('تم تحديث الملف الشخصي بنجاح.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/edit_profile.html', form=form)

@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """تغيير كلمة المرور"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('تم تغيير كلمة المرور بنجاح.', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('كلمة المرور الحالية غير صحيحة.', 'danger')
    
    return render_template('auth/change_password.html', form=form)

@bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """معالجة طلب استعادة كلمة المرور"""
    import json
    
    try:
        data = json.loads(request.data)
        email = data.get('email')
    except:
        return jsonify({'success': False, 'message': 'بيانات غير صالحة'})
    
    if not email:
        return jsonify({'success': False, 'message': 'البريد الإلكتروني مطلوب'})
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'success': False, 'message': 'لا يوجد حساب مرتبط بهذا البريد الإلكتروني'})
    
    try:
        # إرسال بريد إعادة تعيين كلمة المرور
        send_password_reset_email(user)
        return jsonify({'success': True, 'message': 'تم إرسال رابط إعادة التعيين إلى بريدك الإلكتروني'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'})

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """إعادة تعيين كلمة المرور باستخدام الرابط"""
    from services.services import verify_reset_token
    
    email = verify_reset_token(token)
    if not email:
        flash('الرابط غير صالح أو منتهي الصلاحية.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or len(password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل.', 'danger')
        elif password != confirm_password:
            flash('كلمة المرور وتأكيدها غير متطابقين.', 'danger')
        else:
            user = User.query.filter_by(email=email).first()
            if user:
                user.set_password(password)
                db.session.commit()
                flash('تم إعادة تعيين كلمة المرور بنجاح. يمكنك تسجيل الدخول الآن.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('المستخدم غير موجود.', 'danger')
    
    return render_template('auth/reset_password.html', token=token)