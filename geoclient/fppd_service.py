# geoclient/fppd_service.py

import requests
import urllib3
import logging

# Отключаем предупреждения SSL, так как портал использует специфичные сертификаты
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

def find_station_metadata(lat, lon):
    """
    Ищет метаданные пункта на федеральном портале по координатам.
    Возвращает словарь с данными для модели GeodeticPoint или None.
    """
    delta = 0.0005  # Немного увеличил дельту для надежности поиска (примерно 50м)
    
    polygon = [
        [lon - delta, lat - delta],
        [lon + delta, lat - delta],
        [lon + delta, lat + delta],
        [lon - delta, lat + delta],
        [lon - delta, lat - delta]
    ]

    url = "https://mdss.fppd.cgkipd.ru/api/v1/GGSStation/Search"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://portal.fppd.cgkipd.ru",
        "Referer": "https://portal.fppd.cgkipd.ru/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    payload = {
        "fields_include": [
            "index", "name", "mark", "class_ref", "guid", 
            "surveyyear", "regions_ref", "districts_ref", "center_ref"
        ],
        "filter": {
            # 110: ГГС, 109: СГС-1, 108: ВГС, 107: ФАГС, 106: АГС, 111: ГГС (утрачен)
            "subtype_ref": [110, 109, 108, 107, 106, 111], 
            "geoms": [{"type": "Polygon", "coordinates": [polygon]}]
        },
        "paging": {"pagenumber": 1, "pagesize": 1}
    }

    try:
        # Ставим таймаут 3 секунды, чтобы загрузка файла не висела вечно, если сайт лежит
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=3)
        
        if response.status_code == 200:
            result = response.json()
            entities = result.get("entities", [])
            
            if not entities:
                return None

            station_data = entities[0]["properties"]
            
            # Маппинг данных API в структуру нашего проекта
            # Примечание: class_ref возвращает ID. Для красоты можно было бы сделать словарь соответствий,
            # но пока вернем как есть или с префиксом.
            
            mapped_data = {
                'index_name': station_data.get('index'),
                'mark_number': station_data.get('mark'),
                'network_class': _format_class(station_data.get('class_ref')),
                'official_name': station_data.get('name'),
                'survey_year': station_data.get('surveyyear'),
            }
            return mapped_data

        else:
            logger.warning(f"FPPD API Error: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Error fetching metadata from FPPD: {e}")
        return None

def _format_class(class_ref_id):
    """Преобразует ID класса в читаемый вид (примерная логика)"""
    if not class_ref_id:
        return None
    # Примерный маппинг, если известен. Если нет - возвращаем строкой.
    # Обычно на портале: 1 -> 1 класс, 2 -> 2 класс и т.д.
    return f"{class_ref_id} класс (ID)"