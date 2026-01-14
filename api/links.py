from flask import Blueprint, jsonify, request
from datetime import datetime
import re
from urllib.parse import urlparse

links_bp = Blueprint('links', __name__, url_prefix='/api/links')

# Хранилище ссылок (в реальном приложении - база данных)
links_storage = {}


@links_bp.route('/analyze', methods=['POST'])
def analyze_links():
    """Анализирует список ссылок"""
    data = request.json
    if not data or 'links' not in data:
        return jsonify({"error": "Список links обязателен"}), 400

    links = data['links']
    if not isinstance(links, list):
        return jsonify({"error": "links должен быть списком"}), 400

    analysis = {
        'total_links': len(links),
        'unique_links': len(set(links)),
        'domains': {},
        'protocols': defaultdict(int),
        'file_types': defaultdict(int),
        'invalid_links': []
    }

    for link in links[:1000]:  # Ограничиваем анализ 1000 ссылками
        try:
            parsed = urlparse(link)

            # Анализ протокола
            protocol = parsed.scheme if parsed.scheme else 'no_protocol'
            analysis['protocols'][protocol] += 1

            # Анализ домена
            if parsed.netloc:
                domain = parsed.netloc
                analysis['domains'][domain] = analysis['domains'].get(domain, 0) + 1
            else:
                analysis['invalid_links'].append(link)
                continue

            # Анализ типа файла
            path = parsed.path.lower()
            if '.' in path:
                ext = path.split('.')[-1].split('?')[0]
                analysis['file_types'][ext] += 1
            elif not path or path.endswith('/'):
                analysis['file_types']['directory'] += 1
            else:
                analysis['file_types']['unknown'] += 1

        except Exception as e:
            analysis['invalid_links'].append(link)

    # Сортируем домены по количеству ссылок
    sorted_domains = sorted(
        analysis['domains'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:20]  # Топ 20 доменов

    analysis['top_domains'] = [{'domain': d, 'count': c} for d, c in sorted_domains]

    return jsonify(analysis)


@links_bp.route('/filter', methods=['POST'])
def filter_links():
    """Фильтрует ссылки по различным критериям"""
    data = request.json
    if not data or 'links' not in data:
        return jsonify({"error": "Список links обязателен"}), 400

    links = data['links']
    filters = data.get('filters', {})

    if not isinstance(links, list):
        return jsonify({"error": "links должен быть списком"}), 400

    filtered_links = []

    for link in links:
        try:
            parsed = urlparse(link)

            # Применяем фильтры
            include = True

            # Фильтр по домену
            if 'domain' in filters:
                if parsed.netloc != filters['domain']:
                    include = False

            # Фильтр по протоколу
            if 'protocol' in filters:
                if parsed.scheme != filters['protocol']:
                    include = False

            # Фильтр по расширению файла
            if 'file_type' in filters:
                path = parsed.path.lower()
                if '.' in path:
                    ext = path.split('.')[-1].split('?')[0]
                    if ext != filters['file_type']:
                        include = False
                else:
                    include = False

            # Фильтр по ключевому слову в пути
            if 'keyword' in filters:
                if filters['keyword'].lower() not in link.lower():
                    include = False

            if include:
                filtered_links.append(link)

        except:
            continue

    return jsonify({
        'total_input': len(links),
        'total_filtered': len(filtered_links),
        'filtered_links': filtered_links,
        'filters_applied': filters
    })


@links_bp.route('/export', methods=['POST'])
def export_links():
    """Экспортирует ссылки в различных форматах"""
    data = request.json
    if not data or 'links' not in data:
        return jsonify({"error": "Список links обязателен"}), 400

    links = data['links']
    format_type = data.get('format', 'txt').lower()

    if not isinstance(links, list):
        return jsonify({"error": "links должен быть списком"}), 400

    if format_type == 'txt':
        content = '\n'.join(sorted(set(links)))
        return content, 200, {'Content-Type': 'text/plain'}

    elif format_type == 'csv':
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['URL', 'Domain', 'Protocol', 'Path'])

        for link in sorted(set(links)):
            try:
                parsed = urlparse(link)
                writer.writerow([
                    link,
                    parsed.netloc,
                    parsed.scheme,
                    parsed.path
                ])
            except:
                writer.writerow([link, 'ERROR', 'ERROR', 'ERROR'])

        return output.getvalue(), 200, {'Content-Type': 'text/csv'}

    elif format_type == 'json':
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'total_links': len(set(links)),
            'links': sorted(set(links))
        })

    else:
        return jsonify({"error": f"Формат {format_type} не поддерживается"}), 400