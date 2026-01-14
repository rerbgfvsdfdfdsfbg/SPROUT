import threading
import queue
import time
from collections import defaultdict
from urllib.parse import urlparse, urlunparse
from datetime import datetime
from workers.slave_worker import SlaveWorker, TimeoutException
from config import DEVICE_CONFIGS, APP_CONFIG, TIMEOUT_CONFIG
from utils.resource_detector import get_status_code_category, get_resource_type


class MasterController:
    """Мастер-контроллер для управления слейвами с таймаутами"""

    def __init__(self, scan_id, domain, max_pages=100, max_depth=3, num_workers=5,
                 timeout=None, request_timeout=None):
        if not domain.startswith(('http://', 'https://')):
            domain = 'https://' + domain

        self.scan_id = scan_id
        self.domain = domain
        parsed_domain = urlparse(domain)
        self.base_domain = parsed_domain.netloc
        self.scheme = parsed_domain.scheme
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.num_workers = min(num_workers, APP_CONFIG['max_workers'])
        self.total_timeout = timeout or APP_CONFIG['total_scan_timeout']
        self.request_timeout = request_timeout or APP_CONFIG['request_timeout']

        # Флаги состояния
        self.timed_out = False
        self.scan_start_time = None
        self.scan_completed = False
        self.shutdown_requested = False

        # Структуры для управления
        self.visited_urls = set()
        self.url_queue = queue.Queue()
        self.results = []
        self.stats_lock = threading.Lock()
        self.progress_callback = None

        # Таймеры и события
        self.timeout_timer = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()

        # Семафор для контроля количества обработанных страниц
        self.pages_semaphore = threading.Semaphore(max_pages)

        # Хранилища для уникальных ссылок
        self.all_unique_links = set()
        self.internal_links_by_type = defaultdict(set)
        self.external_links_by_type = defaultdict(set)
        self.internal_links_details = {}
        self.external_links_details = {}

        # Статистика
        self.stats = {
            'status_codes': defaultdict(int),
            'status_categories': defaultdict(int),
            'content_types': defaultdict(int),
            'resource_types': defaultdict(int),
            'device_usage': defaultdict(int),
            'slave_stats': defaultdict(lambda: {'processed': 0, 'errors': 0, 'total_time': 0, 'timeouts': 0}),
            'redirects': defaultdict(int),
            'response_times': [],
            'depths': defaultdict(int),
            'link_types': defaultdict(int),
            'timeout_errors': 0,
            'total_operations': 0,
            'avg_operation_time': 0
        }

        # Инициализация рабочих
        self.workers = self._create_workers()

        # Добавляем начальный URL
        initial_url = self._normalize_url(domain)
        self.url_queue.put((initial_url, 0))
        self.visited_urls.add(initial_url)

    def _normalize_url(self, url):
        """Нормализует URL: убирает фрагменты, приводит к единому виду"""
        parsed = urlparse(url)
        normalized = parsed._replace(fragment="", params="")
        normalized_url = urlunparse(normalized)
        if normalized_url.endswith('/'):
            normalized_url = normalized_url.rstrip('/')
        return normalized_url

    def _create_workers(self):
        """Создает и возвращает список рабочих с настройками таймаутов"""
        workers = []
        for i in range(self.num_workers):
            device_config = DEVICE_CONFIGS[i % len(DEVICE_CONFIGS)]
            worker = SlaveWorker(
                slave_id=f"slave-{i + 1}",
                device_config=device_config,
                request_timeout=self.request_timeout
            )
            workers.append(worker)
        return workers

    def _start_timeout_timer(self):
        """Запускает таймер общего таймаута сканирования"""
        if self.total_timeout > 0:
            self.timeout_timer = threading.Timer(
                self.total_timeout,
                self._handle_total_timeout
            )
            self.timeout_timer.daemon = True
            self.timeout_timer.start()
            print(f"Установлен общий таймаут сканирования: {self.total_timeout} секунд")

    def _handle_total_timeout(self):
        """Обрабатывает общий таймаут сканирования"""
        print(f"Сработал общий таймаут сканирования ({self.total_timeout} секунд)")
        self.timed_out = True
        self.stop_event.set()

        with self.stats_lock:
            self.stats['timeout_errors'] += 1

    def _check_scan_timeout(self):
        """Проверяет, не превышено ли общее время сканирования"""
        if self.scan_start_time and self.total_timeout > 0:
            elapsed = time.time() - self.scan_start_time
            if elapsed > self.total_timeout:
                self._handle_total_timeout()
                return True
        return False

    def set_progress_callback(self, callback):
        """Устанавливает callback для отслеживания прогресса"""
        self.progress_callback = callback

    def pause_scan(self):
        """Приостанавливает сканирование"""
        self.pause_event.clear()
        print("Сканирование приостановлено")

    def resume_scan(self):
        """Возобновляет сканирование"""
        self.pause_event.set()
        print("Сканирование возобновлено")

    def stop_scan(self):
        """Останавливает сканирование по запросу пользователя"""
        print("Получен запрос на остановку сканирования")
        self.shutdown_requested = True
        self.stop_event.set()

    def _update_progress(self):
        """Обновляет информацию о прогрессе"""
        if self.progress_callback:
            elapsed = time.time() - self.scan_start_time if self.scan_start_time else 0
            remaining = max(0, self.total_timeout - elapsed) if self.total_timeout > 0 else None

            progress = {
                'total': len(self.results),
                'max': self.max_pages,
                'queue_size': self.url_queue.qsize(),
                'visited': len(self.visited_urls),
                'unique_links': len(self.all_unique_links),
                'elapsed_time': round(elapsed, 2),
                'remaining_time': round(remaining, 2) if remaining is not None else None,
                'percentage': min(100, round(len(self.results) / self.max_pages * 100, 1)),
                'timed_out': self.timed_out,
                'is_paused': not self.pause_event.is_set(),
                'shutdown_requested': self.shutdown_requested
            }
            self.progress_callback(progress)

    def _process_and_store_link(self, link, source_url):
        """Обрабатывает и сохраняет информацию о ссылке"""
        url = self._normalize_url(link['url'])

        self.all_unique_links.add(url)

        parsed_url = urlparse(url)
        is_internal = parsed_url.netloc == self.base_domain

        resource_type = link.get('resource_type', get_resource_type(url))

        link_details = {
            'url': url,
            'type': 'internal' if is_internal else 'external',
            'resource_type': resource_type,
            'element': link.get('element', 'unknown'),
            'text': link.get('text', ''),
            'found_on_pages': [],
            'first_seen_at': time.time()
        }

        if is_internal:
            self.internal_links_by_type[resource_type].add(url)
            if url not in self.internal_links_details:
                self.internal_links_details[url] = link_details
            if source_url not in self.internal_links_details[url]['found_on_pages']:
                self.internal_links_details[url]['found_on_pages'].append(source_url)
        else:
            self.external_links_by_type[resource_type].add(url)
            if url not in self.external_links_details:
                self.external_links_details[url] = link_details
            if source_url not in self.external_links_details[url]['found_on_pages']:
                self.external_links_details[url]['found_on_pages'].append(source_url)

        return is_internal, resource_type

    def _update_statistics(self, worker, result, depth, source_url):
        """Обновляет статистику на основе результата"""
        with self.stats_lock:
            # Добавляем результат
            self.results.append(result)

            # Статистика по глубине
            self.stats['depths'][depth] += 1

            # Статистика по слейву
            self.stats['slave_stats'][worker.slave_id]['processed'] += 1
            self.stats['slave_stats'][worker.slave_id]['total_time'] += result.get('processing_time', 0)

            if result['success']:
                # Статистика успешных запросов
                status_code = result['status_code']
                self.stats['status_codes'][status_code] += 1
                self.stats['status_categories'][get_status_code_category(status_code)] += 1
                self.stats['content_types'][result.get('content_type', '')] += 1
                self.stats['device_usage'][result['device_used']] += 1
                self.stats['response_times'].append(result.get('processing_time', 0))

                # Статистика по редиректам
                if 'redirect_chain' in result and len(result['redirect_chain']) > 1:
                    self.stats['redirects'][len(result['redirect_chain'])] += 1

                # Обрабатываем и сохраняем все ссылки
                if 'links' in result:
                    for link in result['links']:
                        # Обрабатываем ссылку
                        is_internal, resource_type = self._process_and_store_link(link, source_url)

                        # Обновляем общую статистику по типам
                        self.stats['resource_types'][resource_type] += 1
                        self.stats['link_types']['internal' if is_internal else 'external'] += 1
            else:
                # Статистика ошибок
                self.stats['slave_stats'][worker.slave_id]['errors'] += 1
                self.stats['status_codes'][result.get('status_code', 0)] += 1
                self.stats['status_categories']['error'] += 1

    def _add_new_links_to_queue(self, links, current_depth, source_url):
        """Добавляет новые ссылки в очередь для обработки"""
        if current_depth >= self.max_depth:
            return

        for link in links:
            # Добавляем только внутренние HTML-ссылки
            if (link['type'] == 'internal'
                    and link['resource_type'] == 'html'
                    and link['url'] not in self.visited_urls
                    and len(self.results) < self.max_pages):

                normalized_url = self._normalize_url(link['url'])
                if normalized_url not in self.visited_urls:
                    self.visited_urls.add(normalized_url)
                    self.url_queue.put((normalized_url, current_depth + 1))

    def worker_task(self, worker):
        """Задача для одного рабочего потока"""
        while not self.stop_event.is_set() and len(self.results) < self.max_pages:
            try:
                # Ждем, если сканирование на паузе
                self.pause_event.wait()

                # Проверяем общий таймаут
                if self._check_scan_timeout():
                    break
                # Проверка по max_pages
                if not self.pages_semaphore.acquire(blocking=False):
                    # Достигнут лимит страниц, завершаем работу
                    break

                # Берем URL из очереди с таймаутом
                try:
                    url, depth = self.url_queue.get(timeout=TIMEOUT_CONFIG['queue_timeout'])
                except queue.Empty:
                    # Если очередь пуста, проверяем, может быть сканирование завершено
                    self.pages_semaphore.release()
                    if len(self.results) >= self.max_pages or self.timed_out:
                        break
                    continue

                # Обрабатываем URL
                result = worker.process_url(url, depth, timeout=self.request_timeout)

                # Обновляем статистику
                self._update_statistics(worker, result, depth, url)

                # Добавляем новые ссылки в очередь
                if result['success']:
                    self._add_new_links_to_queue(result['links'], depth, url)

                self.url_queue.task_done()

                # Обновляем прогресс
                self._update_progress()

            except TimeoutException as e:
                print(f"Таймаут в рабочем {worker.slave_id}: {e}")
                with self.stats_lock:
                    self.stats['slave_stats'][worker.slave_id]['timeouts'] += 1
                    self.stats['timeout_errors'] += 1
                if 'url' in locals():
                    self.pages_semaphore.release()
            except Exception as e:
                print(f"Ошибка в рабочем {worker.slave_id}: {e}")
                with self.stats_lock:
                    self.stats['slave_stats'][worker.slave_id]['errors'] += 1
                if 'url' in locals():
                    self.pages_semaphore.release()

    def run_scan(self):
        """Запускает параллельное сканирование с таймаутом"""
        self.scan_start_time = time.time()
        print(f"Начинаем сканирование {self.domain} с {self.num_workers} воркерами")
        print(f"Общий таймаут: {self.total_timeout}с, Таймаут запроса: {self.request_timeout}с")

        # Запускаем таймер общего таймаута
        self._start_timeout_timer()

        threads = []

        # Запускаем рабочие потоки
        for worker in self.workers:
            thread = threading.Thread(
                target=self.worker_task,
                args=(worker,),
                daemon=True
            )
            thread.start()
            threads.append(thread)

        # Мониторим прогресс
        try:
            while (not self.stop_event.is_set() and
                   len(self.results) < self.max_pages and
                   (self.url_queue.qsize() > 0 or any(t.is_alive() for t in threads))):

                time.sleep(0.5)

                # Проверяем общий таймаут
                if self._check_scan_timeout():
                    print("Общий таймаут сработал, останавливаем сканирование...")
                    break

                # Проверяем запрос на остановку
                if self.shutdown_requested:
                    print("Останавливаем сканирование по запросу пользователя...")
                    break

                # Периодически выводим прогресс
                if len(self.results) % 10 == 0 and len(self.results) > 0:
                    elapsed = time.time() - self.scan_start_time
                    print(f"Прогресс: {len(self.results)}/{self.max_pages} страниц, "
                          f"{len(self.all_unique_links)} ссылок, "
                          f"{elapsed:.1f} секунд")

        except KeyboardInterrupt:
            print("Сканирование прервано пользователем (Ctrl+C)")
            self.shutdown_requested = True
            self.stop_event.set()
        finally:
            # Отмечаем сканирование как завершенное
            self.scan_completed = True

            # Останавливаем таймер
            if self.timeout_timer:
                self.timeout_timer.cancel()

            # Останавливаем рабочие потоки
            self.stop_event.set()
            self.pause_event.set()  # Разблокируем потоки на паузе

            # Ждем завершения потоков с таймаутом
            shutdown_timeout = TIMEOUT_CONFIG['graceful_shutdown']
            for thread in threads:
                thread.join(timeout=shutdown_timeout)
                if thread.is_alive():
                    print(f"Предупреждение: поток {thread.name} не завершился за {shutdown_timeout} секунд")
            # Очищаем семафор
            for _ in range(self.max_pages):
                try:
                    self.pages_semaphore.release()
                except ValueError:
                    break

        scan_duration = time.time() - self.scan_start_time

        # Формируем итоговую статистику
        final_stats = self._compile_final_stats(scan_duration)

        return self.results, final_stats

    def _compile_final_stats(self, scan_duration):
        """Компилирует финальную статистику с учетом таймаутов"""
        successful_pages = [r for r in self.results if r.get('success', False)]
        error_pages = [r for r in self.results if not r.get('success', False)]
        timeout_pages = [r for r in self.results if r.get('timeout_exceeded', False)]

        # Подготовка данных о ссылках
        unique_links_data = self._prepare_links_data()

        # Статистика по слейвам
        slave_performance = {}
        for worker in self.workers:
            slave_performance[worker.slave_id] = worker.get_stats_summary()

        # Анализ кодов ответа
        status_code_analysis = {}
        for code, count in self.stats['status_codes'].items():
            status_code_analysis[code] = {
                'count': count,
                'category': get_status_code_category(code),
                'percentage': round(count / len(self.results) * 100, 2) if self.results else 0
            }

        # Расчет среднего времени ответа
        avg_response_time = sum(self.stats['response_times']) / len(self.stats['response_times']) if self.stats[
            'response_times'] else 0

        response_data = {
            'scan_summary': {
                'scan_id': self.scan_id,
                'domain': self.domain,
                'base_domain': self.base_domain,
                'total_pages_scanned': len(self.results),
                'successful_pages': len(successful_pages),
                'error_pages': len(error_pages),
                'timeout_pages': len(timeout_pages),
                'scan_duration_seconds': round(scan_duration, 2),
                'pages_per_second': round(len(self.results) / scan_duration, 2) if scan_duration > 0 else 0,
                'avg_response_time_seconds': round(avg_response_time, 3),
                'max_depth_reached': max([r.get('depth', 0) for r in self.results], default=0),
                'unique_urls_visited': len(self.visited_urls),
                'timed_out': self.timed_out,
                'shutdown_requested': self.shutdown_requested,
                'total_timeout_seconds': self.total_timeout,
                'request_timeout_seconds': self.request_timeout,
                'timeout_exceeded': scan_duration > self.total_timeout if self.total_timeout > 0 else False,
                'completion_status': self._get_completion_status()
            },
            'links_analysis': {
                'total_links_found': self.stats['link_types']['internal'] + self.stats['link_types']['external'],
                'unique_internal_links': len(self.internal_links_details),
                'unique_external_links': len(self.external_links_details),
                'links_by_resource_type': dict(self.stats['resource_types']),
                'links_by_type': dict(self.stats['link_types']),
                'internal_links_by_resource_type': {k: len(v) for k, v in self.internal_links_by_type.items()},
                'external_links_by_resource_type': {k: len(v) for k, v in self.external_links_by_type.items()}
            },
            'http_analysis': {
                'status_codes': status_code_analysis,
                'status_categories': dict(self.stats['status_categories']),
                'content_types': dict(self.stats['content_types']),
                'redirect_analysis': dict(self.stats['redirects'])
            },
            'device_analysis': {
                'device_usage': dict(self.stats['device_usage']),
                'depth_distribution': dict(self.stats['depths'])
            },
            'performance': {
                'slave_performance': slave_performance,
                'total_processing_time': sum(worker.stats['total_time'] for worker in self.workers),
                'total_data_transferred_mb': round(
                    sum(worker.stats['total_bytes'] for worker in self.workers) / (1024 * 1024), 2)
            },
            'configuration': {
                'max_pages': self.max_pages,
                'max_depth': self.max_depth,
                'num_workers': self.num_workers,
                'devices_used': [worker.device['name'] for worker in self.workers],
                'scan_id': self.scan_id
            }
        }

        # Добавляем данные об уникальных ссылках
        if unique_links_data:
            response_data['unique_links'] = unique_links_data

        return response_data

    def _prepare_links_data(self):
        """Подготавливает данные о всех уникальных ссылках"""
        try:
            # Преобразуем множества в списки для JSON
            internal_links_by_type = {}
            for resource_type, urls in self.internal_links_by_type.items():
                internal_links_by_type[resource_type] = sorted(list(urls))

            external_links_by_type = {}
            for resource_type, urls in self.external_links_by_type.items():
                external_links_by_type[resource_type] = sorted(list(urls))

            # Подготавливаем детали ссылок для JSON
            internal_details = {}
            for url, details in self.internal_links_details.items():
                # Создаем копию деталей
                details_copy = {
                    'url': details['url'],
                    'type': details['type'],
                    'resource_type': details['resource_type'],
                    'element': details['element'],
                    'text': details['text'],
                    'found_on_pages': list(details['found_on_pages']),
                    'first_seen_at': datetime.fromtimestamp(details['first_seen_at']).isoformat()
                }
                internal_details[url] = details_copy

            external_details = {}
            for url, details in self.external_links_details.items():
                # Создаем копию деталей
                details_copy = {
                    'url': details['url'],
                    'type': details['type'],
                    'resource_type': details['resource_type'],
                    'element': details['element'],
                    'text': details['text'],
                    'found_on_pages': list(details['found_on_pages']),
                    'first_seen_at': datetime.fromtimestamp(details['first_seen_at']).isoformat()
                }
                external_details[url] = details_copy

            # Подготавливаем top_internal_pages
            top_internal_pages = []
            for url, details in self.internal_links_details.items():
                top_internal_pages.append({
                    'url': url,
                    'found_on_pages_count': len(details['found_on_pages']),
                    'resource_type': details['resource_type']
                })
            top_internal_pages.sort(key=lambda x: x['found_on_pages_count'], reverse=True)
            top_internal_pages = top_internal_pages[:10]

            # Получаем топ внешних доменов
            top_external_domains = self._get_top_external_domains()

            return {
                'all_unique_links': sorted(list(self.all_unique_links)),
                'internal_links': {
                    'total': len(self.internal_links_details),
                    'by_type': internal_links_by_type,
                    'details': internal_details
                },
                'external_links': {
                    'total': len(self.external_links_details),
                    'by_type': external_links_by_type,
                    'details': external_details
                },
                'summary': {
                    'top_internal_pages': top_internal_pages,
                    'top_external_domains': top_external_domains,
                    'resource_type_distribution': {
                        'internal': {k: len(v) for k, v in self.internal_links_by_type.items()},
                        'external': {k: len(v) for k, v in self.external_links_by_type.items()}
                    }
                }
            }
        except Exception as e:
            print(f"Ошибка при подготовке данных о ссылках: {e}")
            return None

    def _get_top_external_domains(self):
        """Получает топ внешних доменов"""
        domain_counts = defaultdict(int)
        for url in self.external_links_details.keys():
            try:
                domain = urlparse(url).netloc
                if domain:
                    domain_counts[domain] += 1
            except Exception:
                continue

        top_domains = [
            {'domain': domain, 'count': count}
            for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return top_domains

    def _get_completion_status(self):
        """Определяет статус завершения сканирования"""
        if self.shutdown_requested:
            return 'user_cancelled'
        elif self.timed_out:
            return 'timeout_exceeded'
        elif len(self.results) >= self.max_pages:
            return 'max_pages_reached'
        elif not self.url_queue.qsize():
            return 'queue_empty'
        else:
            return 'completed'