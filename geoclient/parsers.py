# geoclient/parsers.py
from pyproj import Transformer
from django.contrib.gis.geos import Point as DjangoPoint
from .models import Point as PointModel # PointModel теперь имеет id как CharField
from datetime import datetime
import traceback
from decimal import Decimal, ROUND_HALF_UP
import os

transformer_ecef_to_wgs84 = Transformer.from_crs("EPSG:4978", "EPSG:4326", always_xy=True)
COORDINATE_PRECISION = 6
COORDINATE_COMPARISON_TOLERANCE = Decimal('1e-{}'.format(COORDINATE_PRECISION + 2))

def manual_parse_rinex_header(file_path_or_object):
    header_data = {
        'marker_name': None, # Будет ID точки
        'approx_pos_xyz': None,
        'time_first_obs_str': None,
        'receiver_number': None, # Новое поле
        'antenna_height_h': None, # Новое поле (H из H/E/N)
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
            _f = open(file_path_or_object, 'r', encoding='ascii', errors='ignore')
            lines_to_process_iter = _f
            close_after = True
        else: 
            if hasattr(file_path_or_object, 'seek'):
                file_path_or_object.seek(0)
            lines_to_process_iter = file_path_or_object

        for line_num, line_raw in enumerate(lines_to_process_iter):
            if isinstance(line_raw, bytes):
                try: line = line_raw.decode('ascii')
                except UnicodeDecodeError: line = line_raw.decode('ascii', errors='ignore')
            else: line = str(line_raw)

            if line_num > 250 and not found_end_of_header:
                print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) Превышен лимит строк для хедера ({line_num}), END OF HEADER не найден.")
                break

            line_content = line[:LABEL_START_COL].strip() # Убираем пробелы в конце контента
            label_content = line[LABEL_START_COL:].strip() if len(line) > LABEL_START_COL else ""

            if label_content == "MARKER NAME":
                header_data['marker_name'] = line_content # Это будет ID
            elif label_content == "REC # / TYPE / VERS":
                parts = line_content.split()
                if len(parts) > 0:
                    header_data['receiver_number'] = parts[0] # Первое значение - номер приемника
                # Можно также извлечь тип и версию, если нужно
                # if len(parts) > 1: header_data['receiver_type'] = parts[1] ...
            elif label_content == "ANTENNA: DELTA H/E/N":
                parts = line_content.split()
                if len(parts) > 0:
                    try:
                        header_data['antenna_height_h'] = float(parts[0]) # Первое значение - H
                    except ValueError:
                        print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) Ошибка парсинга ANTENNA: DELTA H: '{parts[0]}'")
            elif label_content == "APPROX POSITION XYZ":
                try:
                    x_str, y_str, z_str = line[0:14].strip(), line[14:28].strip(), line[28:42].strip()
                    if x_str and y_str and z_str:
                         header_data['approx_pos_xyz'] = [float(x_str), float(y_str), float(z_str)]
                    else:
                        coords_str_split = line_content.strip().split() # line_content уже strip-нута выше
                        if len(coords_str_split) >= 3:
                            header_data['approx_pos_xyz'] = [float(c) for c in coords_str_split[:3]]
                except ValueError:
                    print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) Ошибка парсинга APPROX POSITION XYZ: '{line.strip()}'")
            elif label_content in ["TIME OF FIRST OBS", "TIME OF FIRST OBSER"]:
                header_data['time_first_obs_str'] = line_content
            elif label_content == "RINEX VERSION / TYPE": # Переместил ниже, чтобы не перезаписывать rinextype
                parts = line_content.split()
                if len(parts) > 0: header_data['version'] = parts[0]
                if "OBSERVATION DATA" in line_content: header_data['rinextype'] = 'obs'
            elif label_content == "COMMENT":
                header_data['comments'].append(line_content)
            elif label_content == "END OF HEADER":
                found_end_of_header = True; break
        
        if not found_end_of_header: print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) ВНИМАНИЕ: END OF HEADER не найден.")
    except Exception as e:
        print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) Ошибка: {e}"); traceback.print_exc()
    finally:
        if close_after and lines_to_process_iter: lines_to_process_iter.close()

    print(f"[РУЧНОЙ ПАРСЕР HEADER] ({file_identifier}) Извлеченные данные: {header_data}")
    return header_data


def parse_rinex_obs_file(file_obj_from_django, uploaded_file_instance):
    created_points_count = 0
    messages = []
    file_identifier = uploaded_file_instance.file.name.split('/')[-1]
    
    print(f"\n[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) Начинаю обработку.")
    try:
        header_info = manual_parse_rinex_header(file_obj_from_django)
        
        # Проверка обязательных полей
        required_fields = ['marker_name', 'approx_pos_xyz', 'time_first_obs_str']
        missing_fields = [field for field in required_fields if header_info.get(field) is None]
        if missing_fields:
            msg = f"Критическая ошибка парсинга хедера: отсутствуют обязательные поля: {', '.join(missing_fields)}."
            messages.append(msg)
            print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) {msg}")
            return 0, messages

        point_id_val = header_info['marker_name'].strip().upper() # ID теперь это MARKER NAME, приводим к верхнему регистру
        if not point_id_val: # Проверка, что ID не пустой
            messages.append("Критическая ошибка: MARKER NAME (ID точки) не может быть пустым.")
            return 0, messages
            
        approx_pos_xyz_list = header_info['approx_pos_xyz']
        time_first_obs_str = header_info['time_first_obs_str']
        receiver_number_val = header_info.get('receiver_number') # Может быть None
        antenna_height_val = header_info.get('antenna_height_h') # Может быть None

        timestamp = None
        try:
            # ... (логика парсинга timestamp остается прежней, но убедитесь, что она надежна)
            time_parts_raw = time_first_obs_str.strip().split()
            time_parts_numeric = []
            for part in time_parts_raw:
                try: time_parts_numeric.append(float(part))
                except ValueError:
                    if len(time_parts_numeric) >= 6: break
            if len(time_parts_numeric) < 6: raise ValueError(f"Недостаточно числовых компонентов времени ({len(time_parts_numeric)}) в '{time_first_obs_str}'")
            year, month, day = int(time_parts_numeric[0]), int(time_parts_numeric[1]), int(time_parts_numeric[2])
            hour, minute = int(time_parts_numeric[3]), int(time_parts_numeric[4])
            sec_float = time_parts_numeric[5]
            second, microsecond = int(sec_float), int(round((sec_float - int(sec_float)) * 1_000_000))
            if not (1980 <= year <= datetime.now().year + 10 and 1 <= month <= 12 and 1 <= day <= 31 and \
                    0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                raise ValueError(f"Некорректные компоненты даты/времени: Y={year} M={month} D={day} H={hour} M={minute} S={sec_float}")
            timestamp = datetime(year, month, day, hour, minute, second, microsecond)
        except Exception as e:
            # ... (обработка ошибок парсинга времени)
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
        
        # Проверка на дубликаты: ID (бывшее имя) + время + координаты
        # Поле `name` в PointModel было заменено на `id` (CharField, primary_key=True)
        # и добавлено `station_name`
        
        # Ищем по новому ID (который равен point_id_val)
        # Если точка с таким ID уже существует, это УЖЕ конфликт первичного ключа,
        # если мы не обновляем, а создаем.
        # Поэтому сначала проверяем существование по ID.
        
        if PointModel.objects.filter(id=point_id_val).exists():
            # Точка с таким ID уже существует. Теперь проверяем, это полный дубликат или нужно обновить?
            # Для простоты, если ID совпадает, считаем это дубликатом данных из этого файла.
            # Более сложная логика могла бы обновлять существующую точку, если другие параметры (время, координаты) отличаются.
            # Но ваша задача - "не добавлять новые точки, если уже существуют подобные".
            # "Подобные" здесь означает: такой же ID (marker_name) И такое же время И такие же координаты.
            existing_point = PointModel.objects.get(id=point_id_val)
            is_duplicate_data = False
            if existing_point.timestamp == timestamp and \
               abs(existing_point.location.x - lon_to_store) < float(COORDINATE_COMPARISON_TOLERANCE) and \
               abs(existing_point.location.y - lat_to_store) < float(COORDINATE_COMPARISON_TOLERANCE):
                is_duplicate_data = True

            if is_duplicate_data:
                msg = f"Точка с ID '{point_id_val}' и такими же параметрами (время, координаты) уже существует. Пропущена."
                messages.append(msg)
                print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) {msg}")
            else:
                # ID совпал, но другие параметры (время/координаты) отличаются.
                # Здесь можно решить: обновить существующую точку или сообщить об ошибке/предупреждении.
                # Пока что сообщим о конфликте ID с разными данными.
                msg = (f"Предупреждение: Точка с ID '{point_id_val}' уже существует, но имеет другие параметры "
                       f"(время: {existing_point.timestamp} vs {timestamp}, "
                       f"коорд: [{existing_point.latitude:.{COORDINATE_PRECISION}f},{existing_point.longitude:.{COORDINATE_PRECISION}f}] vs "
                       f"[{lat_to_store:.{COORDINATE_PRECISION}f},{lon_to_store:.{COORDINATE_PRECISION}f}]). "
                       f"Новая точка не создана, существующая не обновлена.")
                messages.append(msg)
                print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) {msg}")
        else:
            # Точки с таким ID еще нет, создаем новую
            point_obj = PointModel.objects.create(
                id=point_id_val, # Это теперь PK
                # station_name будет устанавливаться пользователем через UI, парсер его не знает
                location=DjangoPoint(lon_to_store, lat_to_store, srid=4326),
                timestamp=timestamp,
                description=f"Из файла {file_identifier}. Ручной парсер.",
                source_file=uploaded_file_instance,
                raw_x=x_raw, raw_y=y_raw, raw_z=z_raw,
                receiver_number=receiver_number_val,
                antenna_height=antenna_height_val
            )
            created_points_count = 1
            msg = f"Точка ID '{point_obj.id}' создана."
            messages.append(msg)
            print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) {msg}")

    except Exception as e: # ... (обработка общих ошибок) ...
        error_message = f"Общая ошибка при обработке файла: {str(e)}"
        print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) КРИТИЧЕСКАЯ ОШИБКА: {e}")
        traceback.print_exc()
        messages.append(error_message)

    # ... (финальное логирование и возврат messages) ...
    final_log_msg = f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) Завершение. Точек создано: {created_points_count}. Сообщений: {len(messages)}"
    print(final_log_msg)
    if created_points_count == 0 and not any("ошибка" in m.lower() or "критическая" in m.lower() or "предупреждение" in m.lower() for m in messages):
        if not any("дубликат" in m.lower() or "пропущена" in m.lower() for m in messages) and not any ("создана" in m.lower() for m in messages):
             messages.append("Новых точек не создано (возможно, файл пуст или не содержит корректных данных для создания).")
    for msg_text in messages: print(f"[РУЧНОЙ ПАРСЕР OBS] ({file_identifier}) Сообщение для ответа: {msg_text}")
    return created_points_count, messages

def parse_rinex_nav_file(file_obj_from_django, file_type, uploaded_file_instance): # ... (без изменений) ...
    file_identifier = uploaded_file_instance.file.name.split('/')[-1]
    msg = f"Обработка файлов типа '{file_type.upper()}' не приводит к созданию точек в текущей реализации парсера."
    print(f"[РУЧНОЙ ПАРСЕР NAV/GLO] ({file_identifier}) {msg}")
    return 0, [msg]
