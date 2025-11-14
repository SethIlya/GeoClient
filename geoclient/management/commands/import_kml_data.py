# geoclient/management/commands/import_kml_data.py

import xml.etree.ElementTree as ET
import re
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import Point as DjangoPoint
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Transform
from geoclient.models import Point

# Функция-помощник для извлечения данных из строки description
def parse_description(description_text):
    """
    Парсит текстовое описание из KML для извлечения структурированных данных.
    """
    data = {
        'network_class': None,
        'index_name': None,
        'center_type': None,
        'mark_number': None,
        'status': None, # В вашем примере нет статуса, но оставим на всякий случай
        'description': None,
    }
    
    # Используем регулярные выражения для надежного поиска
    # re.IGNORECASE делает поиск нечувствительным к регистру ("индекс:" или "Индекс:")
    
    match = re.search(r'индекс:\s*([^,]+)', description_text, re.IGNORECASE)
    if match:
        data['index_name'] = match.group(1).strip()

    match = re.search(r'класс:\s*([^,]+)', description_text, re.IGNORECASE)
    if match:
        data['network_class'] = match.group(1).strip()

    match = re.search(r'центр:\s*([^,]+)', description_text, re.IGNORECASE)
    if match:
        data['center_type'] = match.group(1).strip()

    match = re.search(r'номер марки:\s*([^,]+)', description_text, re.IGNORECASE)
    if match:
        data['mark_number'] = match.group(1).strip()
        
    # Можно добавить логику для извлечения дополнительного описания, если потребуется
    
    return data


class Command(BaseCommand):
    help = 'Импортирует или обновляет данные о пунктах из KML файла (экспорт из Geoeye).'

    def add_arguments(self, parser):
        parser.add_argument('kml_file', type=str, help='Полный путь к KML файлу для импорта.')
        parser.add_argument(
            '--radius', type=int, default=10,
            help='Радиус поиска в метрах для сопоставления точек по координатам.'
        )

    def handle(self, *args, **options):
        file_path = options['kml_file']
        search_radius = options['radius']

        updated_count = 0
        skipped_count = 0
        not_found_count = 0

        self.stdout.write(self.style.SUCCESS(f"Начинаю импорт из KML файла: {file_path}"))
        self.stdout.write(self.style.SUCCESS(f"Радиус поиска для сопоставления точек: {search_radius} метров."))

        try:
            # Парсим KML файл. Этот метод убирает namespace для простоты поиска тегов.
            it = ET.iterparse(file_path)
            for _, el in it:
                if '}' in el.tag:
                    el.tag = el.tag.split('}', 1)[1]
            root = it.root

            for placemark in root.findall('.//Placemark'):
                name_tag = placemark.find('name')
                point_name_from_kml = name_tag.text.strip() if name_tag is not None else "Без имени"

                coords_tag = placemark.find('.//coordinates')
                if coords_tag is None or not coords_tag.text:
                    self.stdout.write(self.style.WARNING(f'Точка "{point_name_from_kml}": Пропущена. Отсутствуют координаты.'))
                    skipped_count += 1
                    continue
                
                try:
                    lon_str, lat_str, *_ = coords_tag.text.strip().split(',')
                    lon_float = float(lon_str)
                    lat_float = float(lat_str)
                except (ValueError, TypeError):
                    self.stdout.write(self.style.WARNING(f'Точка "{point_name_from_kml}": Неверный формат координат "{coords_tag.text}". Пропущено.'))
                    skipped_count += 1
                    continue

                kml_point_location = DjangoPoint(lon_float, lat_float, srid=4326)

                # --- ИСПРАВЛЕННЫЙ ЗАПРОС ---
                # Трансформируем поле location в SRID 3857 (Web Mercator), где единицы - метры,
                # и только после этого сравниваем с расстоянием в метрах.
                nearby_points_qs = Point.objects.annotate(
                    location_mercator=Transform('location', 3857)
                ).filter(
                    location_mercator__dwithin=(kml_point_location, D(m=search_radius))
                )
                # --- КОНЕЦ ИСПРАВЛЕНИЙ ---
                
                found_count = nearby_points_qs.count()

                if found_count == 1:
                    point_to_update = nearby_points_qs.first()
                    description_tag = placemark.find('description')

                    if description_tag is not None and description_tag.text:
                        parsed_data = parse_description(description_tag.text)
                        
                        point_to_update.network_class = parsed_data['network_class']
                        point_to_update.index_name = parsed_data['index_name']
                        point_to_update.center_type = parsed_data['center_type']
                        point_to_update.mark_number = parsed_data['mark_number']
                        
                        if not point_to_update.station_name:
                            point_to_update.station_name = point_name_from_kml
                            
                        point_to_update.save()
                        updated_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Точка "{point_to_update.id}" обновлена данными для "{point_name_from_kml}".'))
                    else:
                        self.stdout.write(self.style.NOTICE(f'Точка "{point_name_from_kml}" найдена, но у нее нет тега <description>. Обновление пропущено.'))
                        skipped_count += 1

                elif found_count == 0:
                    not_found_count += 1
                    self.stdout.write(self.style.NOTICE(f'Для точки "{point_name_from_kml}" не найдено соответствий в радиусе {search_radius}м. Пропущено.'))
                
                else: # found_count > 1
                    skipped_count += 1
                    ids_found = list(nearby_points_qs.values_list('id', flat=True))
                    self.stdout.write(self.style.ERROR(f'Для точки "{point_name_from_kml}" найдено несколько кандидатов ({found_count} шт: {ids_found}) в радиусе {search_radius}м. Пропущено из-за неоднозначности.'))

        except FileNotFoundError:
            raise CommandError(f'Файл не найден по пути: "{file_path}"')
        except ET.ParseError:
            raise CommandError(f'Ошибка парсинга XML в файле: "{file_path}". Убедитесь, что это корректный KML.')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Произошла критическая ошибка: {e}'))
            import traceback
            traceback.print_exc()

        self.stdout.write(self.style.SUCCESS(
            f'\nИмпорт завершен. Обновлено: {updated_count}, Не найдено: {not_found_count}, Пропущено: {skipped_count}.'
        ))