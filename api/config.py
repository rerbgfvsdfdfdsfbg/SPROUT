# Список user-agent'ов для имитации разных устройств
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36',
]

# Карта расширений файлов к типам ресурсов
RESOURCE_TYPES = {
    'html': 'html', 'htm': 'html', 'php': 'html', 'asp': 'html', 'aspx': 'html',
    'jsp': 'html', 'do': 'html', 'action': 'html', 'cgi': 'html',
    'css': 'css',
    'js': 'javascript', 'jsx': 'javascript', 'ts': 'javascript', 'tsx': 'javascript',
    'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image',
    'bmp': 'image', 'svg': 'image', 'webp': 'image', 'ico': 'image',
    'tiff': 'image', 'tif': 'image', 'heic': 'image', 'heif': 'image',
    'mp4': 'video', 'avi': 'video', 'mov': 'video', 'wmv': 'video',
    'flv': 'video', 'mkv': 'video', 'webm': 'video', 'm4v': 'video',
    'mp3': 'audio', 'wav': 'audio', 'ogg': 'audio', 'flac': 'audio',
    'aac': 'audio', 'm4a': 'audio', 'wma': 'audio',
    'zip': 'archive', 'rar': 'archive', '7z': 'archive', 'tar': 'archive',
    'gz': 'archive', 'bz2': 'archive', 'xz': 'archive', 'tgz': 'archive',
    'pdf': 'document', 'doc': 'document', 'docx': 'document',
    'xls': 'document', 'xlsx': 'document', 'ppt': 'document',
    'pptx': 'document', 'txt': 'document', 'rtf': 'document',
    'odt': 'document', 'ods': 'document', 'odp': 'document',
    'csv': 'document', 'tsv': 'document', 'xml': 'document',
    'exe': 'executable', 'msi': 'executable', 'dmg': 'executable',
    'pkg': 'executable', 'deb': 'executable', 'rpm': 'executable',
    'apk': 'executable', 'ipa': 'executable',
    'json': 'data', 'yaml': 'data', 'yml': 'data', 'sql': 'data',
    'db': 'data', 'sqlite': 'data', 'mdb': 'data',
    'ini': 'config', 'cfg': 'config', 'conf': 'config', 'properties': 'config',
    'ttf': 'font', 'otf': 'font', 'woff': 'font', 'woff2': 'font', 'eot': 'font',
}

# Полные конфигурации устройств
DEVICE_CONFIGS = [
    {
        "id": "desktop-chrome-windows",
        "name": "Desktop Chrome Windows",
        "user_agent": USER_AGENTS[0],
        "screen_resolution": "1920x1080",
        "platform": "Windows",
        "language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "timezone": "Europe/Moscow"
    },
    {
        "id": "macbook-safari",
        "name": "MacBook Safari",
        "user_agent": USER_AGENTS[1],
        "screen_resolution": "2560x1600",
        "platform": "macOS",
        "language": "en-US,en;q=0.9",
        "timezone": "America/New_York"
    },
    {
        "id": "firefox-windows",
        "name": "Firefox Windows",
        "user_agent": USER_AGENTS[2],
        "screen_resolution": "1920x1080",
        "platform": "Windows",
        "language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "timezone": "Europe/Moscow"
    },
    {
        "id": "iphone-safari",
        "name": "iPhone Safari",
        "user_agent": USER_AGENTS[3],
        "screen_resolution": "390x844",
        "platform": "iOS",
        "language": "ru-RU,ru;q=0.9",
        "timezone": "Europe/Moscow"
    },
    {
        "id": "android-chrome",
        "name": "Android Chrome",
        "user_agent": USER_AGENTS[4],
        "screen_resolution": "360x800",
        "platform": "Android",
        "language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "timezone": "Europe/Moscow"
    }
]

# Конфигурация таймаутов
TIMEOUT_CONFIG = {
    'total_scan_timeout': 100,  # Максимальное время сканирования (5 минут)
    'request_timeout': 15,      # Таймаут на HTTP запрос
    'queue_timeout': 2,         # Таймаут ожидания из очереди
    'graceful_shutdown': 5,     # Время на graceful shutdown
    'health_check_timeout': 30, # Таймаут health check
}

# Конфигурация приложения
APP_CONFIG = {
    'max_workers': 10,
    'default_max_pages': 50,
    'default_max_depth': 3,
    'request_timeout': TIMEOUT_CONFIG['request_timeout'],
    'min_delay': 0.5,
    'max_delay': 2.0,
    'total_scan_timeout': TIMEOUT_CONFIG['total_scan_timeout'],  # Новый параметр
}