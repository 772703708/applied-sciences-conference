from flask import Blueprint, render_template, request, jsonify, Response, current_app
from models import Speaker, Sponsor, News, Gallery, Track, FAQ, Event, Setting
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    """الصفحة الرئيسية"""
    speakers = Speaker.query.filter_by(is_keynote=True).order_by(Speaker.order).limit(6).all()
    sponsors = Sponsor.query.filter_by(is_active=True).order_by(Sponsor.order).all()
    news = News.query.filter_by(is_published=True).order_by(News.published_at.desc()).limit(3).all()
    tracks = Track.query.filter_by(is_active=True).order_by(Track.order).all()
    events = Event.query.order_by(Event.start_time).limit(5).all()
    
    return render_template('main/home.html',
                         speakers=speakers,
                         sponsors=sponsors,
                         news=news,
                         tracks=tracks,
                         events=events)

@bp.route('/about')
def about():
    """عن المؤتمر"""
    return render_template('main/about.html')

@bp.route('/objectives')
def objectives():
    """أهداف المؤتمر"""
    return render_template('main/objectives.html')

@bp.route('/tracks')
def tracks():
    """محاور المؤتمر"""
    all_tracks = Track.query.filter_by(is_active=True).order_by(Track.order).all()
    return render_template('main/tracks.html', tracks=all_tracks)

@bp.route('/speakers')
def speakers():
    """المتحدثون"""
    keynote_speakers = Speaker.query.filter_by(is_keynote=True).order_by(Speaker.order).all()
    other_speakers = Speaker.query.filter_by(is_keynote=False).order_by(Speaker.order).all()
    return render_template('main/speakers.html', 
                         keynote_speakers=keynote_speakers,
                         other_speakers=other_speakers)

@bp.route('/sponsors')
def sponsors():
    """الرعاة"""
    sponsors_by_tier = {
        'platinum': Sponsor.query.filter_by(tier='platinum', is_active=True).order_by(Sponsor.order).all(),
        'gold': Sponsor.query.filter_by(tier='gold', is_active=True).order_by(Sponsor.order).all(),
        'silver': Sponsor.query.filter_by(tier='silver', is_active=True).order_by(Sponsor.order).all(),
        'bronze': Sponsor.query.filter_by(tier='bronze', is_active=True).order_by(Sponsor.order).all()
    }
    return render_template('main/sponsors.html', sponsors_by_tier=sponsors_by_tier)

@bp.route('/news')
def news():
    """الأخبار"""
    page = request.args.get('page', 1, type=int)
    per_page = 9
    news_list = News.query.filter_by(is_published=True)\
                         .order_by(News.published_at.desc())\
                         .paginate(page=page, per_page=per_page)
    return render_template('main/news.html', news_list=news_list)

@bp.route('/news/<slug>')
def news_detail(slug):
    """تفاصيل الخبر"""
    news_item = News.query.filter_by(slug=slug, is_published=True).first_or_404()
    news_item.views += 1

    from app import db
    db.session.commit()

    # أخبار ذات صلة
    related_news = News.query.filter(
        News.id != news_item.id,
        News.is_published == True
    ).order_by(
        News.published_at.desc()
    ).limit(3).all()

    return render_template(
        'main/news_detail.html',
        news=news_item,
        related_news=related_news
    )

@bp.route('/gallery')
def gallery():
    """معرض الصور"""
    page = request.args.get('page', 1, type=int)
    per_page = 12
    category = request.args.get('category', 'all')
    
    query = Gallery.query
    if category != 'all':
        query = query.filter_by(category=category)
    
    gallery_items = query.order_by(Gallery.order, Gallery.uploaded_at.desc())\
                        .paginate(page=page, per_page=per_page)
    
    categories = ['all', 'conference', 'workshop', 'social']
    return render_template('main/gallery.html', 
                         gallery_items=gallery_items,
                         categories=categories,
                         current_category=category)

@bp.route('/faq')
def faq():
    """الأسئلة الشائعة"""
    # تجميع الأسئلة حسب التصنيف
    faqs_by_category = {}
    categories = ['general', 'submission', 'registration', 'visa']
    
    for category in categories:
        faqs_by_category[category] = FAQ.query.filter_by(
            category=category, is_active=True
        ).order_by(FAQ.order).all()
    
    return render_template('main/faq.html', faqs_by_category=faqs_by_category)

@bp.route('/register')
def register_page():
    """صفحة التسجيل (معلومات فقط)"""
    return render_template('main/register.html')

@bp.route('/api/conference-info')
def conference_info():
    """API لمعلومات المؤتمر"""
    settings = Setting.query.first()
    return jsonify({
        'name': settings.site_name if settings else 'المؤتمر',
        'dates': settings.conference_dates if settings else '27-29 يوليو 2026',  # تم التعديل
        'venue': settings.conference_venue if settings else 'كلية العلوم التطبيقية - جامعة ذمار',
        'registration_open': settings.registration_open if settings else True,
        'submission_open': settings.submission_open if settings else True
    })

@bp.route('/sitemap.xml')
def sitemap():
    """خريطة الموقع الديناميكية"""
    from models import News, Speaker
    
    # الحصول على URL الأساسي
    host_url = request.host_url.rstrip('/')
    
    # الصفحات الثابتة
    static_pages = [
        ('/', 1.0),
        ('/about', 0.9),
        ('/objectives', 0.9),
        ('/tracks', 0.9),
        ('/speakers', 0.9),
        ('/sponsors', 0.8),
        ('/news', 0.9),
        ('/gallery', 0.8),
        ('/faq', 0.7),
        ('/register', 0.8),
        ('/submission/submit', 0.9),  # تم التعديل: paper-submission -> submission/submit
        ('/submission/track', 0.9),   # تم التعديل: paper-tracking -> submission/track
        ('/contact', 0.8)
    ]
    
    # الصفحات الديناميكية
    news_items = News.query.filter_by(is_published=True).all()
    
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # إضافة الصفحات الثابتة
    for page_url, priority in static_pages:
        xml += f'  <url>\n'
        xml += f'    <loc>{host_url}{page_url}</loc>\n'
        xml += f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>\n'
        xml += f'    <priority>{priority}</priority>\n'
        xml += f'  </url>\n'
    
    # إضافة الأخبار
    for news in news_items:
        xml += f'  <url>\n'
        xml += f'    <loc>{host_url}/news/{news.slug}</loc>\n'
        xml += f'    <lastmod>{news.published_at.strftime("%Y-%m-%d") if news.published_at else datetime.now().strftime("%Y-%m-%d")}</lastmod>\n'
        xml += f'    <priority>0.6</priority>\n'
        xml += f'  </url>\n'
    
    xml += '</urlset>'
    
    return Response(xml, mimetype='application/xml')

@bp.route('/about-college')
def about_college():
    """عن كلية العلوم التطبيقية"""
    return render_template('main/about_college.html')