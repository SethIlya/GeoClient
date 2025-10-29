# geoclient/parsers.py

from pyproj import Transformer
from django.contrib.gis.geos import Point as DjangoPoint
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Transform
from django.db import transaction
from .models import GeodeticPoint, Observation, UploadedRinexFile
from datetime import datetime, timedelta # --- ИЗМЕНЕНИЕ: импортируем timedelta ---
import traceback
from decimal import Decimal, ROUND_HALF_UP
import os

transformer_ecef_to_wgs84 = Transformer.from_crs("EPSG:4978", "EPSG:4326", always_xy=True)
COORDINATE_PRECISION = 6
POINT_MERGE_RADIUS_METERS = 7.0

def manual_parse_rinex_header(file_like_object):
    # --- ИЗМЕНЕНИЕ: Добавляем 'time_last_obs_str' в словарь ---
    header_data = {
        'marker_name': None, 
        'approx_pos_xyz': None, 
        'time_first_obs_str': None, 
        'time_last_obs_str': None, # <-- НОВОЕ
        'receiver_number': None, 
        'antenna_height_h': None, 
        'version': None, 
        'rinextype': None, 
        'comments': []
    }
    found_end_of_header = False
    LABEL_START_COL = 60
    try:
        if hasattr(file_like_object, 'seek'): file_like_object.seek(0)
        for line_num, line in enumerate(file_like_object):
            if line_num > 250 and not found_end_of_header: break
            line_content = line[:LABEL_START_COL].strip()
            label_content = line[LABEL_START_COL:].strip() if len(line) > LABEL_START_COL else ""
            if label_content == "MARKER NAME": header_data['marker_name'] = line_content
            elif label_content == "REC # / TYPE / VERS":
                parts = line_content.split();
                if len(parts) > 0: header_data['receiver_number'] = parts[0]
            elif label_content == "ANTENNA: DELTA H/E/N":
                parts = line_content.split();
                if len(parts) > 0:
                    try: header_data['antenna_height_h'] = float(parts[0])
                    except ValueError: pass
            elif label_content == "APPROX POSITION XYZ":
                try:
                    coords_parts = line_content.split();
                    if len(coords_parts) >= 3: header_data['approx_pos_xyz'] = [float(c) for c in coords_parts[:3]]
                except ValueError: pass
            elif label_content in ["TIME OF FIRST OBS", "TIME OF FIRST OBSER"]: header_data['time_first_obs_str'] = line_content
            # --- ИЗМЕНЕНИЕ: Добавляем обработку TIME OF LAST OBS ---
            elif label_content in ["TIME OF LAST OBS", "TIME OF LAST OBSER"]: header_data['time_last_obs_str'] = line_content # <-- НОВОЕ
            elif label_content == "RINEX VERSION / TYPE":
                parts = line_content.split();
                if len(parts) > 0: header_data['version'] = parts[0]
                if "OBSERVATION DATA" in line_content: header_data['rinextype'] = 'obs'
            elif label_content == "COMMENT": header_data['comments'].append(line_content)
            elif label_content == "END OF HEADER": found_end_of_header = True; break
    except Exception as e: print(f"[РУЧНОЙ ПАРСЕР HEADER] Ошибка: {e}"); traceback.print_exc()
    return header_data


def parse_rinex_obs_file(text_stream, uploaded_file_instance):
    created_points_count = 0
    messages = []
    
    def _parse_time_string(time_str):
        if not time_str: return None
        try:
            time_parts_raw = time_str.strip().split()
            time_parts_numeric = [float(p) for p in time_parts_raw if p.replace('.', '', 1).replace('-', '', 1).isdigit()]
            if len(time_parts_numeric) < 6: raise ValueError("Недостаточно компонентов времени")
            year, month, day, hour, minute = map(int, time_parts_numeric[:5])
            sec_float = time_parts_numeric[5]
            second, microsecond = int(sec_float), int(round((sec_float - int(sec_float)) * 1_000_000))
            return datetime(year, month, day, hour, minute, second, microsecond)
        except Exception as e:
            print(f"Ошибка парсинга времени из '{time_str}': {e}")
            return None

    try:
        header_info = manual_parse_rinex_header(text_stream)
        
        required_fields = ['marker_name', 'approx_pos_xyz', 'time_first_obs_str']
        missing_fields = [field for field in required_fields if header_info.get(field) is None]
        if missing_fields:
            msg = f"Критическая ошибка: отсутствуют обязательные поля: {', '.join(missing_fields)}."
            messages.append(msg); return 0, messages

        point_id_from_file = header_info['marker_name'].strip().upper()
        if not point_id_from_file:
            messages.append("Критическая ошибка: MARKER NAME (ID пункта) не может быть пустым.")
            return 0, messages
            
        approx_pos_xyz_list = header_info['approx_pos_xyz']
        receiver_number_val = header_info.get('receiver_number')
        antenna_height_val = header_info.get('antenna_height_h')

        # --- ИЗМЕНЕНИЕ: Используем новую функцию для парсинга времени ---
        timestamp_first = _parse_time_string(header_info['time_first_obs_str'])
        if not timestamp_first:
            err_msg = f"Критическая ошибка: не удалось распарсить TIME OF FIRST OBS: {header_info['time_first_obs_str']}"
            messages.append(err_msg); return 0, messages

        timestamp_last = _parse_time_string(header_info.get('time_last_obs_str'))
        
        duration = None
        if timestamp_first and timestamp_last and timestamp_last > timestamp_first:
            duration = timestamp_last - timestamp_first
        # --- КОНЕЦ ИЗМЕНЕНИЯ ---

        x_raw,y_raw,z_raw = approx_pos_xyz_list
        lon_raw,lat_raw,_ = transformer_ecef_to_wgs84.transform(x_raw,y_raw,z_raw)
        quantizer = Decimal('1e-{}'.format(COORDINATE_PRECISION))
        lon_to_store = float(Decimal(str(lon_raw)).quantize(quantizer, rounding=ROUND_HALF_UP))
        lat_to_store = float(Decimal(str(lat_raw)).quantize(quantizer, rounding=ROUND_HALF_UP))
        
        new_location = DjangoPoint(lon_to_store, lat_to_store, srid=4326)

        with transaction.atomic():
            nearby_points_qs = GeodeticPoint.objects.annotate(
                location_mercator=Transform('location', 3857)
            ).filter(
                location_mercator__dwithin=(new_location, D(m=POINT_MERGE_RADIUS_METERS))
            )
            point_by_id_qs = GeodeticPoint.objects.filter(id=point_id_from_file)
            
            candidate_points = (nearby_points_qs | point_by_id_qs).distinct()

            point_obj = None
            if candidate_points.exists():
                main_point = candidate_points.order_by('created_at').first()
                duplicate_points = candidate_points.exclude(id=main_point.id)

                if duplicate_points.exists():
                    ids_to_merge = list(duplicate_points.values_list('id', flat=True))
                    Observation.objects.filter(point__in=duplicate_points).update(point=main_point)
                    duplicate_points.delete()
                    msg = (f"Обнаружены дубликаты. Пункты {ids_to_merge} были объединены с главным пунктом '{main_point.id}'.")
                    messages.append(msg)

                point_obj = main_point
            else:
                point_obj = GeodeticPoint.objects.create(
                    id=point_id_from_file,
                    location=new_location
                )
                messages.append(f"Создан новый геодезический пункт с ID '{point_id_from_file}'.")
            
            if point_obj.observations.filter(timestamp=timestamp_first).exists():
                msg = f"Наблюдение для пункта '{point_obj.id}' от {timestamp_first.strftime('%Y-%m-%d %H:%M')} уже существует. Пропущено."
                messages.append(msg)
            else:
                new_observation = Observation.objects.create(
                    point=point_obj,
                    location=new_location,
                    timestamp=timestamp_first, # Используем время первого наблюдения как ключ
                    source_file=uploaded_file_instance,
                    raw_x=x_raw, raw_y=y_raw, raw_z=z_raw,
                    receiver_number=receiver_number_val,
                    antenna_height=antenna_height_val,
                    duration=duration # <-- НОВОЕ: Сохраняем длительность
                )
                created_points_count = 1
                messages.append(f"Добавлено новое наблюдение для пункта '{point_obj.id}' от {new_observation.timestamp.strftime('%Y-%m-%d %H:%M')}.")
                
                latest_obs = point_obj.observations.latest('timestamp')
                if latest_obs and point_obj.location != latest_obs.location:
                    point_obj.location = latest_obs.location
                    point_obj.save(update_fields=['location'])

    except Exception as e:
        error_message = f"Общая ошибка при обработке файла: {str(e)}"
        traceback.print_exc()
        messages.append(error_message)
             
    return created_points_count, messages

def parse_rinex_nav_file(text_stream, file_type, uploaded_file_instance):
    """
    Заглушка для обработки навигационных файлов.
    """
    msg = f"Обработка файлов типа '{file_type.upper()}' не приводит к созданию точек в текущей реализации парсера."
    return 0, [msg]