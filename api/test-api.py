import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

app = Flask(__name__)

def get_all_links(domain):
    """
    Рекурсивно собирает все ссылки на сайте, относящиеся к указанному домену
    """
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    
    base_domain = urlparse(domain).netloc
    visited = set()
    to_visit = [domain]
    all_links = set()
    
    while to_visit:
        current_url = to_visit.pop(0)
        
        if current_url in visited:
            continue
        
        try:
            print(f"Парсим: {current_url}")
            response = requests.get(current_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Находим все ссылки на странице
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                
                # Пропускаем пустые ссылки, якоря и javascript
                if not href or href.startswith('#') or href.startswith('javascript:'):
                    continue
                
                # Преобразуем относительные ссылки в абсолютные
                full_url = urljoin(current_url, href)
                
                # Убираем фрагменты (якоря) из URL
                full_url = full_url.split('#')[0]
                
                # Проверяем, что ссылка относится к нашему домену
                if urlparse(full_url).netloc == base_domain:
                    # Добавляем только если это HTTP/HTTPS
                    if full_url.startswith(('http://', 'https://')):
                        if full_url not in all_links:
                            all_links.add(full_url)
                            
                            # Если это новая страница того же домена, добавляем в очередь
                            if full_url not in visited and full_url not in to_visit:
                                to_visit.append(full_url)
            
            visited.add(current_url)
            time.sleep(0.5)  # Задержка между запросами
            
        except requests.RequestException as e:
            print(f"Ошибка при загрузке {current_url}: {e}")
            visited.add(current_url)
        except Exception as e:
            print(f"Ошибка при парсинге {current_url}: {e}")
            visited.add(current_url)
    
    return sorted(list(all_links))
