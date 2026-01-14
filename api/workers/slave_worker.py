import time
import random
import requests
import signal
import functools
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from config import DEVICE_CONFIGS, APP_CONFIG, TIMEOUT_CONFIG
from utils.resource_detector import get_resource_type, detect_content_type_by_header


class TimeoutException(Exception):
    """Исключение при превышении времени выполнения"""
    pass


def timeout_handler(signum, frame):
    """Обработчик сигнала таймаута"""
    raise TimeoutException("Превышено время выполнения операции")


class SlaveWorker:
    """Рабочий слейв для обработки страниц с таймаутами"""

    def __init__(self, slave_id, device_config=None, request_timeout=None):
        self.slave_id = slave_id
        self.device = device_config or random.choice(DEVICE_CONFIGS)
        self.request_timeout = request_timeout or APP_CONFIG['request_timeout']
        self.session = requests.Session()
        self._setup_session()

        self.stats = {
            'pages_processed': 0,
            'links_found': 0,
            'errors': 0,
            'total_bytes': 0,
            'total_time': 0,
            'timeout_errors': 0
        }

        # Для отслеживания времени выполнения операции
        self.operation_start_time = None

    def _setup_session(self):
        """Настраивает HTTP сессию с заголовками устройства"""
        self.session.headers.update({
            'User-Agent': self.device['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': self.device.get('language', 'en-US,en;q=0.9'),
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1'
        })
        self.session.max_redirects = 5
        # Устанавливаем общий таймаут для сессии
        self.session.request = functools.partial(self.session.request, timeout=self.request_timeout)

    def _check_operation_timeout(self, max_operation_time=30):
        """Проверяет, не превышено ли время выполнения операции"""
        if self.operation_start_time:
            elapsed = time.time() - self.operation_start_time
            if elapsed > max_operation_time:
                raise TimeoutException(f"Превышено время операции: {elapsed:.2f} секунд")
        return True

    def process_url(self, url, depth, timeout=None):
        """Обрабатывает одну страницу с таймаутом"""
        start_time = time.time()
        self.operation_start_time = start_time
        operation_timeout = timeout or self.request_timeout

        try:
            print(f"Слейв {self.slave_id} обрабатывает: {url} (глубина: {depth}, таймаут: {operation_timeout}с)")

            # Устанавливаем таймаут для сигналов (Unix системах)
            try:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(operation_timeout + 5)  # +5 секунд на завершение
            except (AttributeError, ValueError):
                pass  # На Windows нет signal.alarm

            # Случайная задержка для имитации человеческого поведения
            time.sleep(random.uniform(APP_CONFIG['min_delay'], APP_CONFIG['max_delay']))

            # Проверяем общее время операции
            self._check_operation_timeout(operation_timeout + 10)

            response = self.session.get(
                url,
                timeout=operation_timeout,
                allow_redirects=True,
                verify=True
            )
            response.raise_for_status()

            processing_time = time.time() - start_time

            # Сбрасываем таймер сигнала
            try:
                signal.alarm(0)
            except (AttributeError, ValueError):
                pass

            return self._process_successful_response(response, url, depth, processing_time)

        except TimeoutException as e:
            processing_time = time.time() - start_time
            self.stats['timeout_errors'] += 1
            return self._process_timeout_error(e, url, depth, processing_time)

        except requests.exceptions.Timeout as e:
            processing_time = time.time() - start_time
            self.stats['timeout_errors'] += 1
            return self._process_timeout_error(e, url, depth, processing_time)

        except requests.RequestException as e:
            processing_time = time.time() - start_time
            return self._process_error_response(e, url, depth, processing_time)

        except Exception as e:
            processing_time = time.time() - start_time
            return self._process_exception(e, url, depth, processing_time)
        finally:
            self.operation_start_time = None
            # Гарантируем сброс таймера
            try:
                signal.alarm(0)
            except (AttributeError, ValueError):
                pass

    def _process_successful_response(self, response, url, depth, processing_time):
        """Обрабатывает успешный HTTP ответ"""
        # Проверяем время выполнения
        if processing_time > self.request_timeout:
            print(
                f"Предупреждение: обработка {url} заняла {processing_time:.2f}с, больше таймаута {self.request_timeout}с")

        # Определяем тип контента
        content_type = detect_content_type_by_header(response.headers)
        if content_type == 'unknown':
            content_type = get_resource_type(url)

        # Парсим только HTML
        links = []
        if 'html' in response.headers.get('Content-Type', '').lower():
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
                base_domain = urlparse(url).netloc
                links = self._extract_links(soup, url, base_domain)
            except Exception as e:
                print(f"Ошибка при парсинге {url}: {e}")

        # Обновляем статистику слейва
        self.stats['pages_processed'] += 1
        self.stats['links_found'] += len(links)
        self.stats['total_bytes'] += len(response.content)
        self.stats['total_time'] += processing_time

        return {
            'success': True,
            'url': url,
            'status_code': response.status_code,
            'content_type': response.headers.get('Content-Type', ''),
            'page_type': content_type,
            'title': self._extract_title(response),
            'page_size_kb': len(response.content) / 1024,
            'links': links,
            'device_used': self.device['id'],
            'depth': depth,
            'slave_id': self.slave_id,
            'processing_time': round(processing_time, 3),
            'timeout_warning': processing_time > self.request_timeout * 0.8,
            'redirect_chain': [r.url for r in response.history] + [response.url] if response.history else [
                response.url],
            'headers': dict(response.headers)
        }

    def _extract_links(self, soup, base_url, base_domain):
        """Извлекает все ссылки из HTML с проверкой времени"""
        links = []
        start_extract_time = time.time()
        max_extract_time = 5

        for element in soup.find_all(['a', 'link', 'script', 'img', 'iframe']):
            # Проверяем время извлечения
            if time.time() - start_extract_time > max_extract_time:
                print(f"Прервано извлечение ссылок из {base_url} - превышено время")
                break

            href = None
            if element.name == 'a' or element.name == 'link':
                href = element.get('href')
            elif element.name in ['script', 'img', 'iframe']:
                href = element.get('src')

            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'data:')):
                continue

            # Преобразуем в абсолютный URL
            absolute_url = urljoin(base_url, href)
            absolute_url = absolute_url.split('#')[0].rstrip('/')

            # Определяем тип ссылки
            link_type = 'internal' if urlparse(absolute_url).netloc == base_domain else 'external'
            resource_type = get_resource_type(absolute_url)

            links.append({
                'url': absolute_url,
                'type': link_type,
                'resource_type': resource_type,
                'element': element.name,
                'text': element.get_text(strip=True)[:100] if element.name == 'a' else '',
                'attributes': {k: v for k, v in element.attrs.items() if k not in ['href', 'src']}
            })
        return links

    def _extract_title(self, response):
        """Извлекает заголовок страницы с таймаутом"""
        if 'html' in response.headers.get('Content-Type', '').lower():
            try:
                soup = BeautifulSoup(response.text[:5000], 'html.parser')
                if soup.title and soup.title.string:
                    return soup.title.string.strip()[:200]
            except Exception:
                pass
        return 'No title'

    def _process_timeout_error(self, error, url, depth, processing_time):
        """Обрабатывает ошибку таймаута"""
        self.stats['errors'] += 1
        self.stats['timeout_errors'] += 1
        self.stats['total_time'] += processing_time

        return {
            'success': False,
            'url': url,
            'status_code': 408,
            'error': str(error),
            'error_type': 'timeout',
            'device_used': self.device['id'],
            'depth': depth,
            'slave_id': self.slave_id,
            'processing_time': round(processing_time, 3),
            'timeout_exceeded': True
        }

    def _process_error_response(self, error, url, depth, processing_time):
        """Обрабатывает ошибку запроса"""
        self.stats['errors'] += 1
        self.stats['total_time'] += processing_time

        status_code = 0
        if hasattr(error, 'response') and error.response is not None:
            status_code = error.response.status_code

        return {
            'success': False,
            'url': url,
            'status_code': status_code,
            'error': str(error),
            'error_type': type(error).__name__,
            'device_used': self.device['id'],
            'depth': depth,
            'slave_id': self.slave_id,
            'processing_time': round(processing_time, 3)
        }

    def _process_exception(self, error, url, depth, processing_time):
        """Обрабатывает общее исключение"""
        self.stats['errors'] += 1
        self.stats['total_time'] += processing_time

        return {
            'success': False,
            'url': url,
            'status_code': 0,
            'error': str(error),
            'error_type': type(error).__name__,
            'device_used': self.device['id'],
            'depth': depth,
            'slave_id': self.slave_id,
            'processing_time': round(processing_time, 3)
        }

    def get_stats_summary(self):
        """Возвращает сводную статистику работы слейва"""
        avg_time = self.stats['total_time'] / self.stats['pages_processed'] if self.stats['pages_processed'] > 0 else 0
        avg_size = self.stats['total_bytes'] / self.stats['pages_processed'] if self.stats['pages_processed'] > 0 else 0

        return {
            'slave_id': self.slave_id,
            'device': self.device['name'],
            'pages_processed': self.stats['pages_processed'],
            'links_found': self.stats['links_found'],
            'errors': self.stats['errors'],
            'timeout_errors': self.stats['timeout_errors'],
            'total_bytes_mb': round(self.stats['total_bytes'] / (1024 * 1024), 2),
            'avg_processing_time': round(avg_time, 3),
            'avg_page_size_kb': round(avg_size / 1024, 2),
            'error_rate': round(
                self.stats['errors'] / max(self.stats['pages_processed'] + self.stats['errors'], 1) * 100, 2),
            'timeout_rate': round(
                self.stats['timeout_errors'] / max(self.stats['pages_processed'] + self.stats['timeout_errors'],
                                                   1) * 100, 2)
        }