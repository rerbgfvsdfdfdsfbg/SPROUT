import mimetypes
import time
from flask import Flask, request, jsonify
from datetime import datetime
import uuid
from config import APP_CONFIG, RESOURCE_TYPES, DEVICE_CONFIGS, TIMEOUT_CONFIG
from workers.master_controller import MasterController

app = Flask(__name__)

# Хранилище активных сканирований
active_scans = {}


@app.route('/api/scan')
def scan_website():
    """Основной endpoint для сканирования сайта с таймаутами"""
    domain = request.args.get('domain')
    max_pages = request.args.get('max_pages', APP_CONFIG['default_max_pages'], type=int)
    max_depth = request.args.get('max_depth', APP_CONFIG['default_max_depth'], type=int)
    num_workers = request.args.get('workers', 5, type=int)
    timeout = request.args.get('timeout', APP_CONFIG['total_scan_timeout'], type=int)
    request_timeout = request.args.get('request_timeout', APP_CONFIG['request_timeout'], type=int)
    detailed = request.args.get('detailed', 'false').lower() == 'true'
    include_links = request.args.get('include_links', 'true').lower() == 'true'

    # Валидация параметров
    if not domain:
        return jsonify({
            "error": "Параметр domain обязателен",
            "example": "/api/scan?domain=example.com&max_pages=50&max_depth=3&workers=5&timeout=300"
        }), 400

    if num_workers > APP_CONFIG['max_workers']:
        return jsonify({
            "error": f"Количество воркеров не может превышать {APP_CONFIG['max_workers']}"
        }), 400

    # Валидация таймаутов
    if timeout <= 0:
        return jsonify({
            "error": "Таймаут должен быть положительным числом"
        }), 400

    if timeout > 3600:  # Максимум 1 час
        return jsonify({
            "error": "Таймаут не может превышать 3600 секунд (1 час)"
        }), 400

    if request_timeout <= 0:
        return jsonify({
            "error": "Таймаут запроса должен быть положительным числом"
        }), 400

    if request_timeout > 120:  # Максимум 2 минуты на запрос
        return jsonify({
            "error": "Таймаут запроса не может превышать 120 секунд"
        }), 400

    try:
        scan_id = str(uuid.uuid4())
        print(f"Начинаем сканирование {domain} (ID: {scan_id})")
        print(f"Конфигурация: workers={num_workers}, max_pages={max_pages}, "
              f"max_depth={max_depth}, total_timeout={timeout}s, "
              f"request_timeout={request_timeout}s")

        # Создаем мастер-контроллер с таймаутами
        master = MasterController(
            scan_id=scan_id,
            domain=domain,
            max_pages=max_pages,
            max_depth=max_depth,
            num_workers=num_workers,
            timeout=timeout,
            request_timeout=request_timeout
        )

        # Сохраняем ссылку на активное сканирование
        active_scans[scan_id] = master

        # Запускаем сканирование
        results, stats = master.run_scan()

        # Удаляем из активных сканирований
        if scan_id in active_scans:
            del active_scans[scan_id]

        # Формируем ответ
        response_data = {
            "scan_id": scan_id,
            "timestamp": datetime.now().isoformat(),
            "domain": domain,
            "summary": stats['scan_summary'],
            "links": stats.get('links_analysis', {}),
            "http_analysis": stats.get('http_analysis', {}),
            "devices": stats.get('device_analysis', {}),
            "performance": stats.get('performance', {}),
            "config": stats.get('configuration', {}),
            "timeout_info": {
                "total_timeout_seconds": timeout,
                "request_timeout_seconds": request_timeout,
                "actual_duration_seconds": stats['scan_summary']['scan_duration_seconds'],
                "timeout_exceeded": stats['scan_summary'].get('timeout_exceeded', False),
                "completion_status": stats['scan_summary'].get('completion_status', 'unknown')
            },
            "status": "completed"
        }

        # Добавляем подробные результаты если запрошено
        if detailed:
            response_data["detailed_results"] = results

        # Добавляем списки уникальных ссылок если запрошено и данные доступны
        if include_links and 'unique_links' in stats and stats['unique_links'] is not None:
            response_data["unique_links"] = stats['unique_links']

        return jsonify(response_data)

    except Exception as e:
        print(f"Критическая ошибка при сканировании: {e}")
        import traceback
        traceback.print_exc()

        # Удаляем сканирование из активных в случае ошибки
        if 'scan_id' in locals() and scan_id in active_scans:
            del active_scans[scan_id]

        return jsonify({
            "error": str(e),
            "domain": domain,
            "scan_timestamp": datetime.now().isoformat(),
            "status": "failed",
            "timeout_config": {
                "total_timeout": timeout,
                "request_timeout": request_timeout
            }
        }), 500


@app.route('/api/scan/<scan_id>/control', methods=['POST'])
def control_scan(scan_id):
    """Управление активным сканированием (пауза, остановка)"""
    if scan_id not in active_scans:
        return jsonify({
            "scan_id": scan_id,
            "status": "not_found",
            "message": "Сканирование не найдено или завершено"
        }), 404

    action = request.json.get('action')
    master = active_scans[scan_id]

    if action == 'pause':
        master.pause_scan()
        return jsonify({
            "scan_id": scan_id,
            "action": "pause",
            "status": "success",
            "message": "Сканирование приостановлено"
        })

    elif action == 'resume':
        master.resume_scan()
        return jsonify({
            "scan_id": scan_id,
            "action": "resume",
            "status": "success",
            "message": "Сканирование возобновлено"
        })

    elif action == 'stop':
        master.stop_scan()
        return jsonify({
            "scan_id": scan_id,
            "action": "stop",
            "status": "success",
            "message": "Запрос на остановку сканирования отправлен"
        })

    else:
        return jsonify({
            "error": "Неизвестное действие",
            "available_actions": ["pause", "resume", "stop"]
        }), 400


@app.route('/api/scan/<scan_id>/progress')
def get_scan_progress(scan_id):
    """Получить прогресс активного сканирования"""
    if scan_id in active_scans:
        master = active_scans[scan_id]

        # Создаем временный callback для получения прогресса
        progress_data = {}

        def progress_callback(data):
            progress_data.update(data)

        master.set_progress_callback(progress_callback)
        master._update_progress()

        return jsonify({
            "scan_id": scan_id,
            "status": "running",
            "progress": progress_data
        })

    return jsonify({
        "scan_id": scan_id,
        "status": "not_found",
        "message": "Сканирование не найдено или завершено"
    }), 404


@app.route('/api/scan/status')
def scan_status():
    """Endpoint для проверки статуса всех сканирований"""
    return jsonify({
        "status": "ready",
        "active_scans": len(active_scans),
        "max_workers": APP_CONFIG['max_workers'],
        "available_devices": [
            {"id": device['id'], "name": device['name'], "type": device['platform']}
            for device in DEVICE_CONFIGS
        ]
    })


@app.route('/api/statistics')
def get_statistics():
    """Возвращает общую статистику по всем сканированиям"""
    return jsonify({
        "resource_types": RESOURCE_TYPES,
        "status_code_categories": {
            "1xx": "Informational",
            "2xx": "Success",
            "3xx": "Redirection",
            "4xx": "Client Error",
            "5xx": "Server Error"
        },
        "device_profiles": DEVICE_CONFIGS,
        "app_config": APP_CONFIG
    })


@app.route('/api/timeouts')
def get_timeout_info():
    """Получить информацию о настройках таймаутов"""
    return jsonify({
        "timeout_config": TIMEOUT_CONFIG,
        "recommended_timeouts": {
            "small_sites": {
                "total_timeout": 60,
                "request_timeout": 10,
                "description": "Небольшие сайты (до 50 страниц)"
            },
            "medium_sites": {
                "total_timeout": 300,
                "request_timeout": 15,
                "description": "Средние сайты (до 500 страниц)"
            },
            "large_sites": {
                "total_timeout": 1800,
                "request_timeout": 20,
                "description": "Крупные сайты (до 5000 страниц)"
            },
            "cautious": {
                "total_timeout": 30,
                "request_timeout": 5,
                "description": "Быстрая проверка (ограниченное время)"
            }
        },
        "limits": {
            "max_total_timeout": 3600,
            "max_request_timeout": 120,
            "min_timeout": 1
        }
    })


@app.route('/health')
def health_check():
    """Health check endpoint с проверкой таймаутов"""
    start_time = time.time()

    # Простая проверка доступности
    try:
        # Проверяем, что приложение отвечает в разумное время
        if time.time() - start_time > TIMEOUT_CONFIG['health_check_timeout']:
            return jsonify({
                "status": "degraded",
                "timestamp": datetime.now().isoformat(),
                "response_time": round(time.time() - start_time, 3),
                "warning": "Медленный ответ health check"
            }), 200

        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "website-scanner",
            "active_scans": len(active_scans),
            "response_time": round(time.time() - start_time, 3),
            "timeout_config": TIMEOUT_CONFIG
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "response_time": round(time.time() - start_time, 3)
        }), 500


if __name__ == '__main__':
    mimetypes.init()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)