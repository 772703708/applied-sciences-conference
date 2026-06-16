"""
Google Drive Integration Services
رفع الملفات وإدارة المجلدات في Google Drive باستخدام OAuth 2.0
"""

import os
import io
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload
from flask import current_app

# نطاقات الصلاحيات المطلوبة
SCOPES = ['https://www.googleapis.com/auth/drive.file']


def get_drive_service():
    """
    تهيئة الاتصال بـ Google Drive API باستخدام OAuth 2.0
    """
    try:
        creds = None
        token_path = os.path.join(current_app.config['BASEDIR'], 'token.json')
        client_secret_path = os.path.join(current_app.config['BASEDIR'], 'client_secret.json')
        
        # تحميل token إذا كان موجوداً
        if os.path.exists(token_path):
            with open(token_path, 'r') as token:
                creds = Credentials.from_authorized_user_info(
                    eval(token.read()), 
                    SCOPES
                )
        
        # إذا لم تكن هناك صلاحيات صالحة، اطلب من المستخدم تسجيل الدخول
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(client_secret_path):
                    raise FileNotFoundError(
                        f"client_secret.json not found at: {client_secret_path}\n"
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secret_path, 
                    SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # حفظ token للمرة القادمة
            with open(token_path, 'w') as token:
                token.write(str(creds.to_json()))
            print(f"✅ تم حفظ token في: {token_path}")
        
        # بناء خدمة Drive
        service = build('drive', 'v3', credentials=creds)
        return service
        
    except Exception as e:
        print(f"❌ خطأ في الاتصال بـ Google Drive: {str(e)}")
        raise


def get_folder_id_by_track(track):
    """
    الحصول على Folder ID بناءً على التخصص العلمي
    """
    folder_mapping = current_app.config.get('TRACK_FOLDER_MAPPING', {})
    
    track_key_mapping = {
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
    
    key = track_key_mapping.get(track, track)
    folder_id = folder_mapping.get(key)
    
    if not folder_id:
        folder_id = current_app.config['DRIVE_FOLDER_IDS'].get('papers_root')
    
    return folder_id


def upload_file_to_drive(file_stream, filename, folder_id):
    """
    رفع ملف إلى Google Drive في مجلد محدد باستخدام OAuth 2.0
    بدون استخدام ملفات مؤقتة (يتم الرفع مباشرة من الذاكرة)
    """
    try:
        service = get_drive_service()
        
        # قراءة الملف مباشرة من الذاكرة (بدون حفظ مؤقت)
        file_content = file_stream.read()
        
        # إعداد metadata للملف
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        # رفع الملف مباشرة من الذاكرة باستخدام MediaIoBaseUpload
        media = MediaIoBaseUpload(
            io.BytesIO(file_content),
            mimetype='application/pdf',
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink, webContentLink'
        ).execute()
        
        # إنشاء روابط الملف
        file_id = file.get('id')
        view_link = file.get('webViewLink') or f"https://drive.google.com/file/d/{file_id}/view"
        download_link = file.get('webContentLink') or f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # إضافة صلاحية القراءة للجميع
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            service.permissions().create(fileId=file_id, body=permission).execute()
        except Exception as e:
            print(f"⚠️ تحذير: لم نتمكن من إضافة صلاحية عامة: {e}")
        
        return {
            'success': True,
            'file_id': file_id,
            'view_link': view_link,
            'download_link': download_link
        }
        
    except Exception as e:
        print(f"❌ خطأ في رفع الملف: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def get_file_info(file_id):
    """
    الحصول على معلومات ملف من Google Drive
    """
    try:
        service = get_drive_service()
        file = service.files().get(
            fileId=file_id,
            fields='id, name, webViewLink, webContentLink, size, mimeType, createdTime'
        ).execute()
        
        return {
            'success': True,
            'file_id': file.get('id'),
            'name': file.get('name'),
            'view_link': file.get('webViewLink'),
            'download_link': file.get('webContentLink'),
            'size': file.get('size'),
            'mime_type': file.get('mimeType'),
            'created_time': file.get('createdTime')
        }
        
    except Exception as e:
        print(f"❌ خطأ في جلب معلومات الملف: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def delete_file_from_drive(file_id):
    """
    حذف ملف من Google Drive
    """
    try:
        service = get_drive_service()
        service.files().delete(fileId=file_id).execute()
        return {'success': True}
        
    except Exception as e:
        print(f"❌ خطأ في حذف الملف: {str(e)}")
        return {'success': False, 'error': str(e)}