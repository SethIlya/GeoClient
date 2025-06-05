# geoclient/parsers.py
from pyproj import Transformer
from django.contrib.gis.geos import Point as DjangoPoint
from .models import Point as PointModel
from datetime import datetime
import traceback
from decimal import Decimal, ROUND_HALF_UP
import os

transformer_ecef_to_wgs84 = Transformer.from_crs("EPSG:4978", "EPSG:4326", always_xy=True)
COORDINATE_PRECISION = 6 # Количество знаков после запятой для хранения и сравнения lat/lon
# Допуск для сравнения float-координат. Для 6 знаков точности, 1e-8 (0.00000001) - это очень маленький допуск,
# который покроет только ошибки округления float, но не реальные различия в 7-м знаке.
COORDINATE_COMPARISON_TOLERANCE = Decimal('1e-{}'.format(COORDINATE_PRECISION + 2))

def manual_parse_rinex_header(file_path_or_object):
    header_data = {
        'marker_name': "UnknownMarker",
        'approx_pos_xyz': None,
        'time_first_obs_str': None,
        'version': None,
        'rinextype': None,
        'comments': []
    }
    found_end_of_header = False
    LABEL_START_COL = 60
    file_identifier = "UnknownFile"
    
    if isinstance(file_path_or_object, (str, os.PathLike)):
        file_identifier = os.path.basename(file_path_or_object)
    elif hasattr(file_path_or_object, 'name') and file_path_or_object.name:
        file_identifier = file_path_or_object.name
    
    lines_to_process_iter = None
    close_after = False

    try:
        if isinstance(file_path_or_object, (str, os.PathLike)):
            # Открываем файл, если это путь
            _f = open(file_path_or_object, 'r', encoding='ascii', errors='ignore')
            lines_to_process_iter = _f
            close_after = True
        else: 
            # Предполагаем, что это file-like объект (например, InMemoryUploadedFile)
            if hasattr(file_path_or_object, 'seek'):
                file_path_or_object.seek(0) # Сбрасываем указатель на начало
            lines_to_process_iter = file_path_or_object

        for line_num, line_raw in enumerate(lines_to_process_iter):
            if isinstance(line_raw, bytes):
                try:
                    line = line_raw.decode('ascii')
                except UnicodeDecodeError:
                    line = line_raw.decode('ascii', errors='ignore')
            else:
                line = str(line_raw) # Убедимся, что это строка

            if line_num > 250 and not found_end_of_header:
                print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) Превышен лимит строк для хедера ({line_num}), END OF HEADER не найден.")
                break

            line_content = line[:LABEL_START_COL]
            label_content = line[LABEL_START_COL:].strip() if len(line) > LABEL_START_COL else ""

            if label_content == "RINEX VERSION / TYPE":
                parts = line_content.split()
                if len(parts) > 0: header_data['version'] = parts[0]
                if "OBSERVATION DATA" in line_content: header_data['rinextype'] = 'obs'
            elif label_content == "MARKER NAME":
                header_data['marker_name'] = line_content.strip()
            elif label_content == "APPROX POSITION XYZ":
                try:
                    # RINEX стандарт: X, Y, Z в полях по 14 символов, начиная с 1-го столбца строки
                    x_str, y_str, z_str = line[0:14].strip(), line[14:28].strip(), line[28:42].strip()
                    if x_str and y_str and z_str:
                         header_data['approx_pos_xyz'] = [float(x_str), float(y_str), float(z_str)]
                    else: # Попытка распарсить, если разделены пробелами в line_content
                        coords_str_split = line_content.strip().split()
                        if len(coords_str_split) >= 3:
                            header_data['approx_pos_xyz'] = [float(c) for c in coords_str_split[:3]]
                except ValueError:
                    print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) Ошибка парсинга APPROX POSITION XYZ: '{line.strip()}'")
            elif label_content in ["TIME OF FIRST OBS", "TIME OF FIRST OBSER"]:
                # RINEX стандарт: год(6), месяц(6), день(6), час(6), мин(6), сек(13.7), система времени(3)
                # Общая длина ~43-44 символа для времени. Берем с запасом до метки.
                header_data['time_first_obs_str'] = line_content.strip() # Берем все до метки
            elif label_content == "COMMENT":
                header_data['comments'].append(line_content.strip())
            elif label_content == "END OF HEADER":
                found_end_of_header = True
                print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) END OF HEADER на строке {line_num + 1}.")
                break
        
        if not found_end_of_header:
            print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) ВНИМАНИЕ: END OF HEADER не найден.")
        
    except Exception as e:
        print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) Ошибка при чтении или обработке файла: {e}")
        traceback.print_exc()
    finally:
        if close_after and lines_to_process_iter:
            lines_to_process_iter.close() # Закрываем файл, если открывали его здесь

    print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) Извлеченные данные хедера: {header_data}")
    return header_data


def parse_rinex_obs_file(file_obj_from_django, uploaded_file_instance):
    created_points_count = 0
    messages = []
    file_identifier = uploaded_file_instance.file.name # Имя файла, как оно сохранено Django
    if '/' in file_identifier: # Берем только имя файла без пути
        file_identifier = file_identifier.split('/')[-1]
    
    print(f"\n[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) Начинаю обработку.")
    try:
        header_info = manual_parse_rinex_header(file_obj_from_django)
        
        if not header_info or header_info.get('approx_pos_xyz') is None or header_info.get('time_first_obs_str') is None:
            msg = "Критическая ошибка парсинга хедера: "
            if not header_info: msg += "не удалось извлечь данные. "
            if header_info and header_info.get('approx_pos_xyz') is None: msg += "APPROX POSITION XYZ отсутствует. "
            if header_info and header_info.get('time_first_obs_str') is None: msg += "TIME OF FIRST OBS отсутствует. "
            messages.append(msg.strip())
            print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) {msg.strip()}")
            return 0, messages

        approx_pos_xyz_list = header_info['approx_pos_xyz']
        marker_name_str = header_info.get('marker_name', "UnknownMarker").strip()
        time_first_obs_str = header_info['time_first_obs_str']

        timestamp = None
        try:
            # Пример строки времени: "2024   1  1  0  0  0.0000000     GPS"
            time_parts_raw = time_first_obs_str.strip().split()
            time_parts_numeric = []
            for part in time_parts_raw:
                try:
                    num_val = float(part) # Попытка преобразовать в число
                    time_parts_numeric.append(num_val)
                except ValueError:
                    # Если не число, и мы уже собрали 6 частей, останавливаемся
                    if len(time_parts_numeric) >= 6:
                        break
            
            if len(time_parts_numeric) < 6:
                raise ValueError(f"Недостаточно числовых компонентов времени ({len(time_parts_numeric)} из 6) в строке: '{time_first_obs_str}' -> {time_parts_numeric}")

            year, month, day = int(time_parts_numeric[0]), int(time_parts_numeric[1]), int(time_parts_numeric[2])
            hour, minute = int(time_parts_numeric[3]), int(time_parts_numeric[4])
            sec_float = time_parts_numeric[5]
            
            second = int(sec_float)
            microsecond = int(round((sec_float - second) * 1_000_000)) # Округляем до ближайшей микросекунды
            
            # Проверка на корректность дат и времени
            if not (1980 <= year <= datetime.now().year + 5 and 1 <= month <= 12 and 1 <= day <= 31 and \
                    0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59): # datetime.now().year + 5 для небольшой гибкости в будущем
                raise ValueError(f"Некорректные компоненты даты/времени: Y={year} M={month} D={day} H={hour} M={minute} S={sec_float}")

            timestamp = datetime(year, month, day, hour, minute, second, microsecond)
            print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) Распарсенное время: {timestamp}")
        except Exception as e:
            err_msg = f"Ошибка парсинга времени из строки '{time_first_obs_str}': {e}"
            messages.append(err_msg)
            print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) {err_msg}")
            traceback.print_exc()
            return 0, messages
        
        x_raw,y_raw,z_raw = approx_pos_xyz_list
        lon_raw,lat_raw,_ = transformer_ecef_to_wgs84.transform(x_raw,y_raw,z_raw)

        quantizer = Decimal('1e-{}'.format(COORDINATE_PRECISION))
        lon_to_store = float(Decimal(str(lon_raw)).quantize(quantizer, rounding=ROUND_HALF_UP))
        lat_to_store = float(Decimal(str(lat_raw)).quantize(quantizer, rounding=ROUND_HALF_UP))
        
        # Проверка на дубликаты
        existing_points_qs = PointModel.objects.filter(
            name__iexact=marker_name_str, # Имя без учета регистра
            timestamp=timestamp          # Точное время (включая микросекунды)
        )

        is_duplicate = False
        if existing_points_qs.exists():
            for existing_point in existing_points_qs:
                # Сравниваем округленные координаты с очень малым допуском
                if abs(existing_point.location.x - lon_to_store) < float(COORDINATE_COMPARISON_TOLERANCE) and \
                   abs(existing_point.location.y - lat_to_store) < float(COORDINATE_COMPARISON_TOLERANCE):
                    is_duplicate = True
                    break
        
        if is_duplicate:
            msg = f"Точка '{marker_name_str}' ({timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')}, [{lat_to_store:.{COORDINATE_PRECISION}f}, {lon_to_store:.{COORDINATE_PRECISION}f}]) пропущена (дубликат)."
            messages.append(msg)
            print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) {msg}")
        else:
            point_obj = PointModel.objects.create(
                name=marker_name_str,
                location=DjangoPoint(lon_to_store, lat_to_store, srid=4326),
                timestamp=timestamp,
                description=f"Из файла {file_identifier}. Ручной парсер.",
                source_file=uploaded_file_instance,
                raw_x=x_raw, raw_y=y_raw, raw_z=z_raw
            )
            created_points_count = 1
            msg = f"Точка '{point_obj.name}' (ID: {point_obj.id}) создана."
            messages.append(msg)
            print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) {msg}")

    except Exception as e:
        error_message = f"Общая ошибка при обработке файла: {str(e)}"
        print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) КРИТИЧЕСКАЯ ОШИБКА: {e}")
        traceback.print_exc()
        messages.append(error_message)
    
    final_log_msg = f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) Завершение. Точек создано: {created_points_count}. Сообщений: {len(messages)}"
    print(final_log_msg)
    if created_points_count == 0 and not any("ошибка" in m.lower() or "критическая" in m.lower() for m in messages):
        if not any("дубликат" in m.lower() for m in messages) and not any ("создана" in m.lower() for m in messages):
             messages.append("Новых точек не создано (возможно, файл пуст или не содержит корректных данных).")

    for msg_text in messages: # Вывод всех сообщений для лога
        print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) Сообщение для ответа: {msg_text}")
            
    return created_points_count, messages


def parse_rinex_nav_file(file_obj_from_django, file_type, uploaded_file_instance):
    file_identifier = uploaded_file_instance.file.name
    if '/' in file_identifier:
        file_identifier = file_identifier.split('/')[-1]
        
    msg = f"Обработка файлов типа '{file_type.upper()}' не приводит к созданию точек в текущей реализации парсера."
    print(f"[РУЧНОЙ ПАРСЕР NAV/GLO] ({file_identifier}) {msg}")
    return 0, [msg]