import signal
import functools
import threading
import time


class TimeoutError(Exception):
    """Исключение при превышении таймаута"""
    pass


def timeout(seconds, error_message="Превышено время выполнения"):
    """Декоратор для установки таймаута на функцию"""

    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Устанавливаем таймаут для Unix систем
            try:
                signal.signal(signal.SIGALRM, _handle_timeout)
                signal.alarm(seconds)
            except (AttributeError, ValueError):
                pass  # На Windows нет signal.alarm

            try:
                result = func(*args, **kwargs)
            finally:
                # Сбрасываем таймер
                try:
                    signal.alarm(0)
                except (AttributeError, ValueError):
                    pass

            return result

        return wrapper

    return decorator


def timeout_thread(seconds, default=None):
    """Декоратор для установки таймаута с использованием потоков"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result_container = []
            exception_container = []

            def target():
                try:
                    result_container.append(func(*args, **kwargs))
                except Exception as e:
                    exception_container.append(e)

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)

            if thread.is_alive():
                raise TimeoutError(f"Функция {func.__name__} превысила таймаут {seconds} секунд")

            if exception_container:
                raise exception_container[0]

            return result_container[0] if result_container else default

        return wrapper

    return decorator


def retry_with_timeout(max_retries=3, timeout=5, backoff=1):
    """Декоратор для повторных попыток с таймаутом"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    # Используем декоратор таймаута
                    @timeout(timeout)
                    def timed_func():
                        return func(*args, **kwargs)

                    return timed_func()

                except (TimeoutError, TimeoutException) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff * (2 ** attempt)
                        print(f"Попытка {attempt + 1} не удалась: {e}. "
                              f"Повтор через {wait_time} секунд...")
                        time.sleep(wait_time)

            raise last_exception

        return wrapper

    return decorator


class TimeoutManager:
    """Менеджер для управления таймаутами"""

    def __init__(self, default_timeout=30):
        self.default_timeout = default_timeout
        self.active_timeouts = {}

    def execute_with_timeout(self, func, timeout=None, *args, **kwargs):
        """Выполняет функцию с таймаутом"""
        timeout = timeout or self.default_timeout
        timeout_id = f"{func.__name__}_{time.time()}"

        def timeout_handler():
            raise TimeoutError(f"Операция {func.__name__} превысила таймаут {timeout} секунд")

        # Создаем таймер
        timer = threading.Timer(timeout, timeout_handler)
        timer.daemon = True
        self.active_timeouts[timeout_id] = timer

        try:
            timer.start()
            result = func(*args, **kwargs)
            return result
        except TimeoutError:
            raise
        finally:
            # Останавливаем таймер и удаляем из активных
            if timeout_id in self.active_timeouts:
                self.active_timeouts[timeout_id].cancel()
                del self.active_timeouts[timeout_id]

    def cancel_all_timeouts(self):
        """Отменяет все активные таймауты"""
        for timer in self.active_timeouts.values():
            timer.cancel()
        self.active_timeouts.clear()

    def get_active_timeouts(self):
        """Возвращает список активных таймаутов"""
        return list(self.active_timeouts.keys())