# geoclient/parsers.py
import georinex
from pyproj import Transformer
from django.contrib.gis.geos import Point as DjangoPoint
from .models import Point as PointModel # Переименовываем импорт, чтобы не конфликтовал с DjangoPoint
from datetime import datetime

# Трансформер из ECEF (EPSG:4978) в WGS84 (EPSG:4326)
# ECEF X, Y, Z -> Geographic lat, lon, height
transformer_ecef_to_wgs84 = Transformer.from_crs("EPSG:4978", "EPSG:4326", always_xy=True)


def parse_rinex_obs_file(file_path, uploaded_file_instance):
    """
    Парсит RINEX Observation файл (.o) и создает точки.
    Это упрощенный пример, фокусирующийся на данных из хедера.
    """
    created_points_count = 0
    errors = []

    try:
        # Georinex может читать прямо из файлового объекта или пути
        obs_data = georinex.read_obs(file_path)

        marker_name = obs_data.attrs.get('marker_name', 'UnknownMarker')
        approx_pos_xyz = obs_data.attrs.get('position_xyz') # [X, Y, Z]
        time_first_obs_str = obs_data.attrs.get('time_first_obs') # строка типа '2025  5  20  5  28 10.0000000'

        if not approx_pos_xyz or len(approx_pos_xyz) != 3:
            errors.append(f"Не найдены или некорректны APPROX POSITION XYZ в хедере файла {file_path.name}")
            return created_points_count, errors
        
        if not time_first_obs_str:
            errors.append(f"Не найдено TIME OF FIRST OBS в хедере файла {file_path.name}")
            return created_points_count, errors

        # Конвертация времени
        # Пример формата: '2025     5    20     5    28   10.0000000'
        # Год, Месяц, День, Час, Минута, Секунда.микросекунды
        try:
            # Удаляем лишние пробелы и разделяем
            time_parts_str = [p for p in time_first_obs_str.split(' ') if p]
            year = int(time_parts_str[0])
            month = int(time_parts_str[1])
            day = int(time_parts_str[2])
            hour = int(time_parts_str[3])
            minute = int(time_parts_str[4])
            second_float = float(time_parts_str[5])
            second = int(second_float)
            microsecond = int((second_float - second) * 1_000_000)
            
            timestamp = datetime(year, month, day, hour, minute, second, microsecond)
        except Exception as e:
            errors.append(f"Ошибка парсинга времени '{time_first_obs_str}': {e}")
            return created_points_count, errors

        # Конвертация координат
        x, y, z = approx_pos_xyz
        lon, lat, alt = transformer_ecef_to_wgs84.transform(x, y, z) # Порядок lon, lat из-за always_xy=True

        # Создание точки в БД
        point_obj = PointModel.objects.create(
            name=marker_name.strip() if marker_name else "Default Name",
            location=DjangoPoint(lon, lat, srid=4326), # lon, lat
            timestamp=timestamp,
            description=f"Из файла {uploaded_file_instance.file.name}. Approx position.",
            source_file=uploaded_file_instance,
            raw_x=x,
            raw_y=y,
            raw_z=z
        )
        created_points_count += 1
        
        # Тут можно добавить логику для парсинга самих наблюдений из `obs_data` (DataFrame)
        # если нужно создавать точки для каждой эпохи наблюдений, а не только APPROX POSITION.
        # Это значительно усложнит логику.

    except Exception as e:
        errors.append(f"Общая ошибка парсинга файла {file_path.name if hasattr(file_path, 'name') else file_path}: {e}")

    return created_points_count, errors

def parse_rinex_nav_file(file_path, file_type, uploaded_file_instance):
    """
    Заглушка для парсинга NAV файлов (.n, .g).
    Обычно они не содержат точек для отображения на карте напрямую,
    а содержат эфемериды спутников.
    """
    # Пример чтения, если понадобится:
    # if file_type == 'n': # GPS
    #     nav_data = georinex.read_nav(file_path)
    # elif file_type == 'g': # GLONASS
    #     nav_data = georinex.read_glnav(file_path)
    # else:
    #     return 0, [f"Неподдерживаемый тип NAV файла: {file_type}"]
    
    # print(f"Парсинг NAV файла ({file_type}): {file_path.name}")
    # print(nav_data.head()) # DataFrame с данными
    # print(nav_data.attrs) # Метаданные из хедера
    
    return 0, [f"Парсинг для NAV файлов типа '{file_type}' еще не реализован."]