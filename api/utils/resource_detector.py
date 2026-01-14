from urllib.parse import urlparse
from config import RESOURCE_TYPES

def get_resource_type(url):
    """Определяет тип ресурса по расширению файла в URL"""
    path = urlparse(url).path.lower()
    if not path or path.endswith('/'):
        return 'html'
    if '.' in path:
        extension = path.split('.')[-1]
        extension = extension.split('?')[0]
        return RESOURCE_TYPES.get(extension, 'unknown')
    return 'html'

def detect_content_type_by_header(headers):
    """Определяет тип контента по заголовкам HTTP"""
    content_type = headers.get('Content-Type', '').lower()
    if 'text/html' in content_type:
        return 'html'
    elif 'text/css' in content_type:
        return 'css'
    elif 'application/javascript' in content_type or 'text/javascript' in content_type:
        return 'javascript'
    elif 'application/json' in content_type:
        return 'json'
    elif 'application/pdf' in content_type:
        return 'pdf'
    elif 'application/zip' in content_type:
        return 'archive'
    elif 'image/' in content_type:
        return 'image'
    elif 'video/' in content_type:
        return 'video'
    elif 'audio/' in content_type:
        return 'audio'
    elif 'application/xml' in content_type or 'text/xml' in content_type:
        return 'xml'
    elif 'text/plain' in content_type:
        return 'text'
    return 'unknown'

def get_status_code_category(status_code):
    """Определяет категорию HTTP статус-кода"""
    if 100 <= status_code < 200:
        return 'informational'
    elif 200 <= status_code < 300:
        return 'success'
    elif 300 <= status_code < 400:
        return 'redirect'
    elif 400 <= status_code < 500:
        return 'client_error'
    elif 500 <= status_code < 600:
        return 'server_error'
    else:
        return 'unknown'