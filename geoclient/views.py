from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.middleware.csrf import get_token as django_get_csrf_token
from django.urls import reverse, NoReverseMatch
import os
import traceback
import xml.etree.ElementTree as ET
import re
import hashlib
import io

from django.contrib.gis.geos import Point as DjangoPoint
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Transform
from django.core.files.storage import default_storage

from .models import UploadedRinexFile, GeodeticPoint
from .parsers import parse_rinex_obs_file, parse_rinex_nav_file

class VueAppContainerView(TemplateView):
    template_name = "index.html" 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['csrf_token'] = django_get_csrf_token(self.request)
        try:
            context['api_points_url'] = reverse('geodeticpoint-list')
            context['api_station_names_url'] = reverse('station-name-list')
            context['api_kml_upload_url'] = reverse('geoclient:api_upload_kml')
            context['api_upload_url'] = reverse('geoclient:api_upload_rinex')
            context['api_csrf_url'] = reverse('geoclient:get_csrf_token')

        except NoReverseMatch as e:
            print(f"ПРЕДУПРЕЖДЕНИЕ (VueAppContainerView): Не удалось получить URL через reverse. Ошибка: {e}")
            context.setdefault('api_points_url', "/api/points/")
            context.setdefault('api_station_names_url', "/api/station-names/")
            context.setdefault('api_kml_upload_url', "/api/upload-kml/")
            context.setdefault('api_upload_url', "/api/upload-rinex/")
            context.setdefault('api_csrf_url', "/api/get-csrf-token/")
        return context

class RinexUploadApiView(View):
    def post(self, request, *args, **kwargs):
        uploaded_files_list = request.FILES.getlist('rinex_files')
        if not uploaded_files_list:
            return JsonResponse({'success': False, 'message': 'Файлы не были предоставлены.'}, status=400)

        aggregated_results_messages = []
        total_created_count_all_files = 0
        overall_success_flag = True

        for rinex_file_from_request in uploaded_files_list:
            file_name_original = rinex_file_from_request.name
            
            try:
                rinex_file_from_request.seek(0)
                file_content_bytes = rinex_file_from_request.read()
                
                sha256_hash = hashlib.sha256(file_content_bytes).hexdigest()
                
                text_stream = io.StringIO(file_content_bytes.decode('ascii', errors='ignore'))

                existing_file_record = UploadedRinexFile.objects.filter(file_hash=sha256_hash).first()
                
                file_actually_exists = False
                if existing_file_record and existing_file_record.file:
                    if default_storage.exists(existing_file_record.file.name):
                        file_actually_exists = True
                    else:
                        print(f"Обнаружена 'сломанная' запись для файла {existing_file_record.file.name}. Удаляю ее.")
                        existing_file_record.delete()
                        existing_file_record = None

                uploaded_file_instance = existing_file_record
                
                if not file_actually_exists:
                    file_ext_part = os.path.splitext(file_name_original.lower())[1]
                    file_type_char = None
                    if 'o' in file_ext_part or ('.rnx' in file_ext_part and 'O' in file_name_original.upper()): file_type_char = 'o'
                    elif 'n' in file_ext_part or ('.rnx' in file_ext_part and 'N' in file_name_original.upper()): file_type_char = 'n'
                    elif 'g' in file_ext_part or ('.rnx' in file_ext_part and 'G' in file_name_original.upper()): file_type_char = 'g'
                    
                    if not file_type_char:
                        aggregated_results_messages.append({'type': 'danger', 'text': f"Файл '{file_name_original}': Не удалось определить тип файла."})
                        overall_success_flag = False
                        continue

                    uploaded_file_instance = UploadedRinexFile.objects.create(
                        file=rinex_file_from_request, 
                        file_type=file_type_char,
                        file_hash=sha256_hash
                    )
                else:
                    aggregated_results_messages.append({
                        'type': 'info',
                        'text': f"Файл '{file_name_original}' уже существует в системе. Обработка..."
                    })

                created_count_this_file, parse_messages_this_file = parse_rinex_obs_file(
                    text_stream, uploaded_file_instance
                )
                
                total_created_count_all_files += created_count_this_file
                for msg in parse_messages_this_file:
                    msg_type = 'info'
                    if "ошибка" in str(msg).lower() or "критическая" in str(msg).lower(): msg_type = 'danger'
                    elif "создана" in str(msg).lower() or "добавлено" in str(msg).lower(): msg_type = 'success'
                    aggregated_results_messages.append({'type': msg_type, 'text': f"Файл '{file_name_original}': {msg}"})

            except Exception as e:
                traceback.print_exc()
                overall_success_flag = False
                aggregated_results_messages.append({
                    'type': 'danger',
                    'text': f"Файл '{file_name_original}': Критическая ошибка во время обработки: {str(e)}"
                })
        
        return JsonResponse({
            'success': overall_success_flag, 
            'messages': aggregated_results_messages,
            'total_created_count': total_created_count_all_files
        })

def _parse_kml_description(description_text):
    data = {
        'network_class': None, 'index_name': None, 'center_type': None, 
        'mark_number': None, 'point_type': 'default'
    }
    patterns = {
        'index_name': r'индекс:\s*([^,]+)', 'network_class': r'класс:\s*([^,]+)',
        'center_type': r'центр:\s*([^,]+)', 'mark_number': r'номер марки:\s*([^,]+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, description_text, re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip()

    if data['network_class']:
        # Нормализуем строку для надежного сравнения
        network_class_normalized = data['network_class'].lower().replace(' ', '').replace('-', '')
        
        # Астрономические/Высокоточные пункты (звездочка)
        if any(substr in network_class_normalized for substr in ['вгс', 'фагс', 'сгс1']):
            data['point_type'] = 'astro'
        # Государственная геодезическая сеть (треугольник)
        elif 'ггс' in network_class_normalized or 'государственнаягеодезическая' in network_class_normalized:
            data['point_type'] = 'ggs'
        # Городские/Съемочные сети (квадрат)
        elif 'городская' in network_class_normalized:
            data['point_type'] = 'survey'
        # Нивелирные и ГНСС сети (круг с перекрестием)
        elif any(substr in network_class_normalized for substr in ['гнс', 'нивелирная']):
            data['point_type'] = 'leveling'
    
    return data

class KMLUploadApiView(View):
    def post(self, request, *args, **kwargs):
        kml_files = request.FILES.getlist('kml_files')
        if not kml_files:
            return JsonResponse({'success': False, 'messages': [{'type': 'danger', 'text': 'KML файл(ы) не был(и) предоставлен(ы).'}]}, status=400)

        total_updated, total_skipped, total_not_found = 0, 0, 0
        search_radius = int(request.POST.get('radius', 3))

        for kml_file in kml_files:
            try:
                it = ET.iterparse(kml_file)
                for _, el in it:
                    if '}' in el.tag: el.tag = el.tag.split('}', 1)[1]
                root = it.root

                for placemark in root.findall('.//Placemark'):
                    name_tag = placemark.find('name')
                    point_name_from_kml = name_tag.text.strip() if name_tag is not None else "Без имени"

                    coords_tag = placemark.find('.//coordinates')
                    if not (coords_tag is not None and coords_tag.text):
                        total_skipped += 1; continue
                    
                    try:
                        lon_str, lat_str, *_ = coords_tag.text.strip().split(',')
                        kml_point_location = DjangoPoint(float(lon_str), float(lat_str), srid=4326)
                    except (ValueError, TypeError):
                        total_skipped += 1; continue
                    
                    nearby_points_qs = GeodeticPoint.objects.annotate(
                        location_mercator=Transform('location', 3857)
                    ).filter(
                        location_mercator__dwithin=(kml_point_location, D(m=search_radius))
                    )
                    
                    if nearby_points_qs.count() == 1:
                        point_to_update = nearby_points_qs.first()
                        description_tag = placemark.find('description')
                        if description_tag is not None and description_tag.text:
                            parsed_data = _parse_kml_description(description_tag.text)
                            
                            point_to_update.network_class = parsed_data.get('network_class')
                            point_to_update.index_name = parsed_data.get('index_name')
                            point_to_update.center_type = parsed_data.get('center_type')
                            point_to_update.mark_number = parsed_data.get('mark_number')
                            point_to_update.point_type = parsed_data.get('point_type', 'default')

                            if not point_to_update.station_name:
                                point_to_update.station_name = point_name_from_kml
                                
                            point_to_update.save()
                            total_updated += 1
                    elif nearby_points_qs.count() == 0:
                        total_not_found += 1
                    else:
                        total_skipped += 1
            except ET.ParseError:
                 return JsonResponse({'success': False, 'messages': [{'type': 'danger', 'text': f'Ошибка парсинга XML в файле {kml_file.name}.'}]}, status=400)
            except Exception as e:
                traceback.print_exc()
                return JsonResponse({'success': False, 'messages': [{'type': 'danger', 'text': f'Критическая ошибка при обработке файла {kml_file.name}: {e}'}]}, status=500)
        
        final_message = f'Обработка KML завершена. Обновлено пунктов: {total_updated}, не найдено: {total_not_found}, пропущено: {total_skipped}.'
        return JsonResponse({'success': True, 'messages': [{'type': 'success', 'text': final_message}], 'updated_count': total_updated})


def get_csrf_token_view(request):
    return JsonResponse({'csrfToken': django_get_csrf_token(request)})