from flask import Flask, render_template
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from config import Config
import os

# استيراد db من models بدلاً من إنشاء واحد جديد
from models import db
from models import User, Setting, Reviewer

# تهيئة الملحقات الأخرى
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # ربط db مع التطبيق
    db.init_app(app)
    
    # ربط الملحقات الأخرى مع التطبيق
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    # إعدادات Login Manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'الرجاء تسجيل الدخول أولاً'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # سياق عام لجميع القوالب
    @app.context_processor
    def inject_conf():
        try:
            settings = Setting.query.first()
            return {
                'conference_name': Config.CONFERENCE_NAME,
                'conference_dates': Config.CONFERENCE_DATES,
                'settings': settings
            }
        except:
            return {
                'conference_name': Config.CONFERENCE_NAME,
                'conference_dates': Config.CONFERENCE_DATES,
                'settings': None
            }
    
    # تسجيل المسارات (Blueprints)
    from routes import main, auth, submission, contact, admin
    
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(submission.bp)
    app.register_blueprint(contact.bp)
    app.register_blueprint(admin.bp)
    
    # صفحات الأخطاء
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(413)
    def too_large(error):
        return 'الملف كبير جداً (الحد الأقصى 10MB)', 413
    
    # إنشاء الجداول والإعدادات الافتراضية داخل سياق التطبيق
    with app.app_context():
        # إنشاء جميع الجداول
        db.create_all()
        
        try:
            # إنشاء إعدادات افتراضية
            if not Setting.query.first():
                default_settings = Setting(
                    site_name=Config.CONFERENCE_NAME,
                    site_description="المؤتمر العلمي الدولي الأول لآفاق العلوم التطبيقية",
                    conference_dates=Config.CONFERENCE_DATES,
                    conference_venue=Config.CONFERENCE_VENUE,
                    contact_email=Config.CONFERENCE_EMAIL,
                    contact_phone=Config.CONFERENCE_PHONE,
                    whatsapp_number=Config.WHATSAPP_NUMBER,
                    dark_mode_default=False,
                    rtl_default=True,
                    conference_active=True,
                    registration_open=True,
                    submission_open=True,
                    submission_deadline="2026-05-01"
                )
                db.session.add(default_settings)
                db.session.commit()
                print("✅ تم إنشاء الإعدادات الافتراضية")
        except Exception as e:
            print(f"⚠️ خطأ في إنشاء الإعدادات: {e}")
        
        try:
            # إنشاء مستخدم Admin افتراضي أول
            if not User.query.filter_by(email='admin@conference.com').first():
                admin_user = User(
                    username='admin',
                    email='admin@conference.com',
                    role='admin',
                    is_active=True,
                    affiliation='جامعة ذمار'
                )
                admin_user.set_password('Admin123!')
                db.session.add(admin_user)
                db.session.commit()
                print("✅ تم إنشاء المستخدم admin (البريد: admin@conference.com | كلمة المرور: Admin123!)")
        except Exception as e:
            print(f"⚠️ خطأ في إنشاء المستخدم admin: {e}")
        
        try:
            # إنشاء المستخدم الأدمن الثاني (محمد البلالي)
            if not User.query.filter_by(email='albelali@gmail.com').first():
                albelali_admin = User(
                    username='albelali772',
                    email='albelali@gmail.com',
                    role='admin',
                    is_active=True,
                    affiliation='مدير النظام - مطور المنصة'
                )
                albelali_admin.set_password('albelali772')
                db.session.add(albelali_admin)
                db.session.commit()
                print("✅ تم إنشاء المستخدم albelali772 (البريد: albelali@gmail.com | كلمة المرور: albelali772)")
            else:
                # تحديث المستخدم الموجود إلى أدمن
                existing_user = User.query.filter_by(email='albelali@gmail.com').first()
                if existing_user.role != 'admin':
                    existing_user.role = 'admin'
                    existing_user.set_password('albelali772')
                    db.session.commit()
                    print("✅ تم تحديث المستخدم albelali@gmail.com إلى أدمن")
        except Exception as e:
            print(f"⚠️ خطأ في إنشاء المستخدم albelali772: {e}")
        
        try:
            # قائمة المحكمين الأساسيين (سيتم إضافتهم إلى قاعدة البيانات)
            default_reviewers = [
                {"name": "أ.د. عبدالله احمد علي", "degree": "أستاذ دكتور", "email": "abdullah2803@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "energy,nanotechnology"},
                {"name": "د. عدنان رضمان الناحية", "degree": "دكتور", "email": "adnan.alnehia@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "energy,nanotechnology"},
                {"name": "د. حسين خليل", "degree": "دكتور", "email": "sallam27@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "biology"},
                {"name": "د. أيمن عبد الصبور", "degree": "دكتور", "email": "ayman_Khalf@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "geology"},
                {"name": "أ. محمد العوش", "degree": "أستاذ", "email": "alaoshm@tu.edu.ye", "phone": "+967774553051", "specialties": "statistics"},
                {"name": "د. محمد القواتي", "degree": "دكتور", "email": "alqawatimohammed@gmail.com", "phone": "+967XXXXXXXXX", "specialties": "chemistry"},
                {"name": "أ.د. نبيل العريق", "degree": "أستاذ دكتور", "email": "nabeel@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "biology"},
                {"name": "أ.د. عمر الشجاع", "degree": "أستاذ دكتور", "email": "omar@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "geology"},
                {"name": "أ.د. انور مسعود", "degree": "أستاذ دكتور", "email": "anwar@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "physics"},
                {"name": "أ.د. دايخ الحسناوي", "degree": "أستاذ دكتور", "email": "daykh@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "chemistry"},
                {"name": "أ.د. عبده محمد عبد الوهاب", "degree": "أستاذ دكتور", "email": "abdo@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "mathematics"},
                {"name": "أ.د. علي الحوباني", "degree": "أستاذ دكتور", "email": "ali@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "geology"},
                {"name": "أ.م.د. فهمي العبسي", "degree": "أستاذ مشارك دكتور", "email": "fahmi@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "physics"},
                {"name": "أ.م.د. انس الشرعبي", "degree": "أستاذ مشارك دكتور", "email": "anas@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "mathematics"},
                {"name": "أ.م.د. عادل الارياني", "degree": "أستاذ مشارك دكتور", "email": "adel@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "chemistry"},
                {"name": "أ.م.د. فؤاد الدبعي", "degree": "أستاذ مشارك دكتور", "email": "fuad@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "energy"},
                {"name": "أ.م.د. روحي الخطيب", "degree": "أستاذ مشارك دكتور", "email": "rouhi@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "geology"},
                {"name": "أ.م.د. يحيى البريهي", "degree": "أستاذ مشارك دكتور", "email": "yahya@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "nanotechnology"},
                {"name": "أ.م.د. فتح اللهبي", "degree": "أستاذ مشارك دكتور", "email": "fath@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "physics"},
                {"name": "أ.م.د. عامر الصبري", "degree": "أستاذ مشارك دكتور", "email": "amer@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "mathematics"},
                {"name": "د. ساره المحاقري", "degree": "دكتور", "email": "sarah@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "biology"},
                {"name": "د. انصاف الخلقي", "degree": "دكتور", "email": "ansaf@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "chemistry"},
                {"name": "د. ماجد الجبلي", "degree": "دكتور", "email": "majed@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "energy"},
                {"name": "د. سليمان الحسام", "degree": "دكتور", "email": "sulaiman@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "physics"},
                {"name": "د. قاسم الشرجبي", "degree": "دكتور", "email": "qasim@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "mathematics"},
                {"name": "أ.م.د. عبد القوي دبوان", "degree": "أستاذ مشارك دكتور", "email": "abdulqawi@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "statistics"},
                {"name": "أ.م.د. عبد الحبيب القباطي", "degree": "أستاذ مشارك دكتور", "email": "abdulhabib@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "biology"},
                {"name": "أ.د. عبد الحليم التميمي", "degree": "أستاذ دكتور", "email": "abdulhalim@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "energy"},
                {"name": "أ.د. نبيل المخلافي", "degree": "أستاذ دكتور", "email": "nabil@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "biology"},
                {"name": "ا.م.د. عبد الوهاب السنباني", "degree": "أستاذ مشارك دكتور", "email": "sanbani@tu.edu.ye", "phone": "+967XXXXXXXXX", "specialties": "statistics"},
            ]
            
            for reviewer_data in default_reviewers:
                existing = Reviewer.query.filter_by(email=reviewer_data["email"]).first()
                if not existing:
                    new_reviewer = Reviewer(
                        name=reviewer_data["name"],
                        degree=reviewer_data["degree"],
                        email=reviewer_data["email"],
                        phone=reviewer_data["phone"],
                        specialties=reviewer_data["specialties"]
                    )
                    db.session.add(new_reviewer)
            db.session.commit()
            print("✅ تم إنشاء المحكمين الأساسيين بنجاح")
        except Exception as e:
            print(f"⚠️ خطأ في إنشاء المحكمين: {e}")
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
