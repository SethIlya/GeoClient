import os
import traceback
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import requests
import urllib3
from pyproj import Transformer

from django.contrib.gis.geos import Point as DjangoPoint
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Transform
from django.db import transaction

from .models import GeodeticPoint, Observation

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- КОНСТАНТЫ ---
transformer_ecef_to_wgs84 = Transformer.from_crs("EPSG:4978", "EPSG:4326", always_xy=True)
COORDINATE_PRECISION = 6
POINT_MERGE_RADIUS_METERS = 7.0  # Радиус объединения (7 метров)

# --- СЛОВАРЬ КЛАССОВ СЕТИ (FPPD) ---
FPPD_CLASS_MAPPING = {
    1: "ФАГС", 2: "ВГС", 3: "СГС - 1", 4: "Астрономо-Геодезическая сеть 1 класса (ГГС - 1 класса)",
    5: "Астрономо-Геодезическая сеть 2 класса (ГГС - 2 класса)", 6: "Геодезическая сеть сгущения 3 класса (ГГС - 3 класса)",
    7: "Геодезическая сеть сгущения 4 класса (ГГС - 4 класса)", 8: "Спутниковая городская геодезическая сеть 1 класса (СГГС – 1)",
    9: "Спутниковая городская геодезическая сеть 2 класса (СГГС – 2)", -1: "Не установлено"
}

def _fetch_fppd_metadata(lat, lon):
    """Поиск ближайшего пункта на портале fppd."""
    delta = 0.0005
    polygon = [[lon - delta, lat - delta], [lon + delta, lat - delta], [lon + delta, lat + delta], [lon - delta, lat + delta], [lon - delta, lat - delta]]
    url = "https://mdss.fppd.cgkipd.ru/api/v1/GGSStation/Search"
    headers = {
        "Content-Type": "application/json", "Accept": "application/json, text/plain, */*",
        "Origin": "https://portal.fppd.cgkipd.ru", "Referer": "https://portal.fppd.cgkipd.ru/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    payload = {
        "fields_include": ["index", "name", "mark", "class_ref", "guid", "surveyyear", "subtype_ref"],
        "filter": {"subtype_ref": [110, 109, 108, 107, 106, 111, 100, 101, 102, 103, 104, 105], "geoms": [{"type": "Polygon", "coordinates": [polygon]}]},
        "paging": {"pagenumber": 1, "pagesize": 1}
    }
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False, timeout=3)
        if response.status_code == 200:
            result = response.json()
            entities = result.get("entities", [])
            if not entities: return None
            data = entities[0]["properties"]
            class_name = FPPD_CLASS_MAPPING.get(data.get('class_ref'), str(data.get('class_ref')))
            subtype = data.get('subtype_ref')
            pt_type = 'ggs'
            if subtype in [107, 108, 109] or data.get('class_ref') in [1, 2, 3]: pt_type = 'astro'
            elif data.get('class_ref') in [18, 19, 20, 21]: pt_type = 'leveling'
            return {
                'index': data.get('index'), 'name': data.get('name'), 'mark': data.get('mark'),
                'class_name': class_name, 'survey_year': data.get('surveyyear'), 'point_type': pt_type
            }
    except: return None

def manual_parse_rinex_header(file_iterator):
    """
    Парсит заголовок из итератора строк (экономит память).
    """
    header_data = {
        'marker_name': None, 'approx_pos_xyz': None, 'time_first_obs_str': None, 
        'time_last_obs_str': None, 'receiver_number': None, 'antenna_height_h': None, 'rinextype': None
    }
    LABEL_START_COL = 60
    
    try:
        for i, line in enumerate(file_iterator):
            # Декодируем, если пришли байты
            if isinstance(line, bytes): line = line.decode('ascii', errors='ignore')
            
            if i > 500 and "END OF HEADER" not in line: break
            
            content = line[:LABEL_START_COL].strip()
            label = line[LABEL_START_COL:].strip()
            
            if label == "MARKER NAME": header_data['marker_name'] = content
            elif label == "REC # / TYPE / VERS": header_data['receiver_number'] = content.split()[0] if content else None
            elif label == "ANTENNA: DELTA H/E/N": 
                try: header_data['antenna_height_h'] = float(content.split()[0])
                except: pass
            elif label == "APPROX POSITION XYZ":
                try: header_data['approx_pos_xyz'] = [float(x) for x in content.split()[:3]]
                except: pass
            elif "TIME OF FIRST OBS" in label: header_data['time_first_obs_str'] = content
            elif "TIME OF LAST OBS" in label: header_data['time_last_obs_str'] = content
            elif "RINEX VERSION" in label and "OBSERVATION DATA" in content: header_data['rinextype'] = 'obs'
            elif "END OF HEADER" in label: break
    except Exception as e:
        print(f"Header parse error: {e}")
        
    return header_data

def parse_rinex_obs_file(file_path_or_obj, uploaded_file_instance):
    """
    Основная функция парсинга. 
    Оптимизирована по памяти (читает с диска).
    ВКЛЮЧЕНА логика объединения точек по радиусу 7 метров.
    """
    created_points_count = 0
    messages = []
    
    def _parse_time(t_str):
        if not t_str: return None
        try:
            parts = [float(p) for p in t_str.split() if p.replace('.','').replace('-','').isdigit()]
            if len(parts) < 5: return None
            sec = parts[5] if len(parts) > 5 else 0
            return datetime(int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), int(sec), int((sec-int(sec))*1000000))
        except: return None

    should_close = False
    f = None
    
    try:
        # Открываем файл как поток, чтобы не грузить в RAM
        if isinstance(file_path_or_obj, str):
            f = open(file_path_or_obj, 'rb')
            should_close = True
        else:
            f = file_path_or_obj
            f.seek(0)

        # 1. Парсим заголовок
        header = manual_parse_rinex_header(f)
        
        raw_id = header.get('marker_name', '').strip().upper()
        if not raw_id: return 0, ["Критическая ошибка: MARKER NAME не найден."]
        if not header.get('approx_pos_xyz'): return 0, ["Критическая ошибка: Нет координат."]

        # 2. Координаты и Время
        x, y, z = header['approx_pos_xyz']
        lon, lat, _ = transformer_ecef_to_wgs84.transform(x, y, z)
        
        # Округляем
        quantizer = Decimal('1e-{}'.format(COORDINATE_PRECISION))
        lon_st = float(Decimal(str(lon)).quantize(quantizer, rounding=ROUND_HALF_UP))
        lat_st = float(Decimal(str(lat)).quantize(quantizer, rounding=ROUND_HALF_UP))
        new_location = DjangoPoint(lon_st, lat_st, srid=4326)

        t_start = _parse_time(header['time_first_obs_str'])
        t_end = _parse_time(header.get('time_last_obs_str'))
        duration = (t_end - t_start) if (t_start and t_end) else None
        
        if not t_start: return 0, ["Ошибка парсинга времени."]

        # 3. Работа с БД (ЛОГИКА ОБЪЕДИНЕНИЯ ВКЛЮЧЕНА)
        with transaction.atomic():
            # А. Ищем точки рядом (в радиусе 7 метров)
            nearby_qs = GeodeticPoint.objects.annotate(
                loc_merc=Transform('location', 3857)
            ).filter(
                loc_merc__dwithin=(new_location.transform(3857, clone=True), D(m=POINT_MERGE_RADIUS_METERS))
            )
            
            # Б. Ищем точки с таким же ID (на случай, если координаты "уплыли", но имя то же)
            same_id_qs = GeodeticPoint.objects.filter(id=raw_id)
            
            # Объединяем результаты поиска
            candidates = (nearby_qs | same_id_qs).distinct()

            point_obj = None
            
            if candidates.exists():
                # Если нашли соседей или одноименные пункты -> берем самый старый (основной)
                main_point = candidates.order_by('created_at').first()
                
                # Все остальные кандидаты считаются дубликатами.
                # Сливаем их в один (это решит проблему TATA vs SANG)
                duplicates = candidates.exclude(pk=main_point.pk)
                
                if duplicates.exists():
                    dup_ids = list(duplicates.values_list('id', flat=True))
                    # Перевешиваем наблюдения на main_point
                    Observation.objects.filter(point__in=duplicates).update(point=main_point)
                    # Удаляем лишние пункты
                    duplicates.delete()
                    messages.append(f"Объединение: Пункты {dup_ids} влиты в '{main_point.id}' из-за близости координат.")
                
                point_obj = main_point
                
                # Если у основного пункта имя отличается от файла (SANG vs TATA), 
                # добавляем примечание, но не меняем ID
                if point_obj.id != raw_id:
                    if not point_obj.description: point_obj.description = ""
                    if raw_id not in point_obj.description:
                         point_obj.description += f"\n[Алиас из файла: {raw_id}]"
                    point_obj.save(update_fields=['description'])
                    messages.append(f"Найден близкий пункт '{point_obj.id}'. Файл '{raw_id}' привязан к нему.")
                else:
                    messages.append(f"Найден существующий пункт: {point_obj.id}")

            else:
                # Если ничего рядом нет -> создаем новый
                point_obj = GeodeticPoint.objects.create(id=raw_id, location=new_location)
                messages.append(f"Создан новый пункт: {raw_id}")

            # Обогащение данными (FPPD)
            if not point_obj.network_class:
                meta = _fetch_fppd_metadata(lat_st, lon_st)
                if meta:
                    point_obj.index_name = meta.get('index', point_obj.index_name)
                    point_obj.mark_number = meta.get('mark', point_obj.mark_number)
                    point_obj.network_class = meta.get('class_name', point_obj.network_class)
                    if point_obj.point_type == 'default' and meta.get('point_type'):
                        point_obj.point_type = meta['point_type']
                    if meta.get('name') and not point_obj.station_name:
                        point_obj.station_name = meta['name']
                    point_obj.save()

            # 4. Создание наблюдения
            if point_obj.observations.filter(timestamp=t_start).exists():
                messages.append(f"Наблюдение за {t_start} уже существует. Пропущено.")
            else:
                Observation.objects.create(
                    point=point_obj, location=new_location, timestamp=t_start,
                    source_file=uploaded_file_instance,
                    duration=duration,
                    receiver_number=header.get('receiver_number'),
                    antenna_height=header.get('antenna_height_h')
                )
                created_points_count = 1
                
                # Актуализируем координаты пункта
                latest = point_obj.observations.latest('timestamp')
                if latest and point_obj.location != latest.location:
                    point_obj.location = latest.location
                    point_obj.save(update_fields=['location'])

    except Exception as e:
        messages.append(f"Ошибка обработки: {e}")
        traceback.print_exc()
    finally:
        if should_close and f: f.close()

    return created_points_count, messages

def parse_rinex_nav_file(text_stream, file_type, uploaded_file_instance):
    """
    Заглушка для обработки навигационных файлов.
    Нужна для совместимости, если views.py пытается её вызвать.
    """
    msg = f"Файл навигации '{file_type.upper()}' сохранен, но не создает точек."
    return 0, [msg]