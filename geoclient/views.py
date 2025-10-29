# geoclient/views.py
import json
import os
import traceback
import hashlib
import io
import re
import xml.etree.ElementTree as ET

from django.views.generic import TemplateView
from django.urls import reverse, NoReverseMatch
from django.contrib.gis.geos import Point as DjangoPoint
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Transform
from django.http import JsonResponse
from django.middleware.csrf import get_token

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .permissions import IsUploader
from .models import UploadedRinexFile, GeodeticPoint, StationDirectoryName
from .parsers import parse_rinex_obs_file


class VueAppContainerView(TemplateView):
    """
    Этот view рендерит основной HTML-шаблон, который служит контейнером
    для всего Vue-приложения. Он просто передает контекст в шаблон,
    а теги django-vite делают всю остальную работу.
    """
    template_name = "geoclient/base_vue.html" # Используем наш шаблон

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_dict = {}
        try:
            settings_dict = {
                'apiPointsUrl': reverse('point-list'),
                'apiStationNamesUrl': reverse('station-name-list'),
                'apiKmlUploadUrl': reverse('api_upload_kml'),
                'apiUploadUrl': reverse('api_upload_rinex'),
                'apiLoginUrl': reverse('api_login'),
                'apiLogoutUrl': reverse('api_logout'),
                'apiUserStatusUrl': reverse('api_user_status'),
                'apiCsrfUrl': reverse('get_csrf_token'), 
            }
        except NoReverseMatch as e:
            print(f"ПРЕДУПРЕЖДЕНИЕ: Не удалось получить URL через reverse: {e}.")
            settings_dict = {
                'apiPointsUrl': "/api/points/",
                'apiStationNamesUrl': "/api/station-names/",
                'apiKmlUploadUrl': "/api/upload-kml/",
                'apiUploadUrl': "/api/upload-rinex/",
                'apiLoginUrl': "/api/login/",
                'apiLogoutUrl': "/api/logout/",
                'apiUserStatusUrl': "/api/user-status/",
            }

        context["django_settings_json"] = json.dumps(settings_dict)
        return context


class RinexUploadApiView(APIView):
    """
    API для обработки загрузки одного или нескольких RINEX-файлов.
    Доступно только для пользователей с правами 'Uploader'.
    """
    permission_classes = [IsAuthenticated, IsUploader]

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
                
                uploaded_file_instance = None
                if existing_file_record:
                    uploaded_file_instance = existing_file_record
                    aggregated_results_messages.append({'type': 'info', 'text': f"Файл '{file_name_original}' уже был обработан. Проверка наблюдений..."})
                else:
                    file_ext_part = os.path.splitext(file_name_original.lower())[1]
                    file_type_char = 'o' if 'o' in file_ext_part else None
                    if not file_type_char:
                        aggregated_results_messages.append({'type': 'warning', 'text': f"Файл '{file_name_original}': неподдерживаемый тип, пропущен."})
                        continue
                    uploaded_file_instance = UploadedRinexFile.objects.create(file=rinex_file_from_request, file_type=file_type_char, file_hash=sha256_hash)
                
                created_count, parse_messages = parse_rinex_obs_file(text_stream, uploaded_file_instance)
                total_created_count_all_files += created_count
                for msg in parse_messages:
                    msg_type = 'info'
                    if "ошибка" in msg.lower(): msg_type = 'danger'
                    elif "создан" in msg.lower() or "добавлено" in msg.lower(): msg_type = 'success'
                    aggregated_results_messages.append({'type': msg_type, 'text': f"Файл '{file_name_original}': {msg}"})
            except Exception as e:
                traceback.print_exc()
                overall_success_flag = False
                aggregated_results_messages.append({'type': 'danger', 'text': f"Файл '{file_name_original}': Критическая ошибка: {str(e)}"})

        return JsonResponse({
            'success': overall_success_flag, 
            'messages': aggregated_results_messages,
            'total_created_count': total_created_count_all_files
        })

def _parse_kml_description(description_text):
    """
    Вспомогательная функция для извлечения данных из поля description в KML.
    """
    data = {'network_class': None, 'index_name': None, 'center_type': None, 'mark_number': None, 'point_type': 'default'}
    patterns = {
        'index_name': r'индекс:\s*([^,]+)',
        'network_class': r'класс:\s*([^,]+)',
        'center_type': r'центр:\s*([^,]+)',
        'mark_number': r'номер марки:\s*([^,]+)',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, description_text, re.IGNORECASE)
        if match:
            data[key] = match.group(1).strip()
    
    if data.get('network_class'):
        nc_norm = data['network_class'].lower().replace(' ', '').replace('-', '')
        if any(s in nc_norm for s in ['вгс', 'фагс', 'сгс1']):
            data['point_type'] = 'astro'
        elif 'ггс' in nc_norm:
            data['point_type'] = 'ggs'
        elif 'городская' in nc_norm:
            data['point_type'] = 'survey'
        elif any(s in nc_norm for s in ['гнс', 'нивелирная']):
            data['point_type'] = 'leveling'
    return data

class KMLUploadApiView(APIView):
    """
    API для обработки загрузки KML-файлов и обогащения данных существующих точек.
    Доступно только для пользователей с правами 'Uploader'.
    """
    permission_classes = [IsAuthenticated, IsUploader]

    def post(self, request, *args, **kwargs):
        kml_files = request.FILES.getlist('kml_files')
        if not kml_files:
            return JsonResponse({'success': False, 'messages': [{'type': 'danger', 'text': 'KML файлы не предоставлены.'}]}, status=400)

        total_updated, total_skipped, total_not_found = 0, 0, 0
        
        try:
            search_radius = int(request.POST.get('radius', 3))
        except (ValueError, TypeError):
            search_radius = 3

        for kml_file in kml_files:
            try:
                # Убираем namespace для простоты парсинга
                it = ET.iterparse(kml_file)
                for _, el in it:
                    if '}' in el.tag:
                        el.tag = el.tag.split('}', 1)[1]
                root = it.root

                for placemark in root.findall('.//Placemark'):
                    name_tag = placemark.find('name')
                    point_name = name_tag.text.strip() if name_tag is not None and name_tag.text else None
                    
                    coords_tag = placemark.find('.//coordinates')
                    if not (coords_tag is not None and coords_tag.text):
                        total_skipped += 1
                        continue
                    
                    try:
                        lon, lat, *_ = coords_tag.text.strip().split(',')
                        kml_point = DjangoPoint(float(lon), float(lat), srid=4326)
                    except (ValueError, TypeError):
                        total_skipped += 1
                        continue
                    
                    nearby_points = GeodeticPoint.objects.annotate(
                        location_mercator=Transform('location', 3857)
                    ).filter(location_mercator__dwithin=(kml_point, D(m=search_radius)))
                    
                    if nearby_points.count() == 1:
                        point = nearby_points.first()
                        desc_tag = placemark.find('description')
                        if desc_tag is not None and desc_tag.text:
                            data = _parse_kml_description(desc_tag.text)
                            point.network_class = data.get('network_class', point.network_class)
                            point.index_name = data.get('index_name', point.index_name)
                            point.center_type = data.get('center_type', point.center_type)
                            point.mark_number = data.get('mark_number', point.mark_number)
                            if data.get('point_type') != 'default':
                                point.point_type = data.get('point_type')
                        
                        if not point.station_name and point_name:
                            point.station_name = point_name

                        if point_name:
                            StationDirectoryName.objects.get_or_create(name=point_name)
                            
                        point.save()
                        total_updated += 1
                    elif nearby_points.count() == 0:
                        total_not_found += 1
                    else:
                        total_skipped += 1

            except ET.ParseError as e:
                 return JsonResponse({'success': False, 'messages': [{'type': 'danger', 'text': f'Ошибка парсинга XML в файле {kml_file.name}: {e}'}]}, status=400)
            except Exception as e:
                traceback.print_exc()
                return JsonResponse({'success': False, 'messages': [{'type': 'danger', 'text': f'Критическая ошибка при обработке файла {kml_file.name}: {e}'}]}, status=500)
        
        message = f'Обработка завершена. Обновлено точек: {total_updated}, не найдено в радиусе {search_radius}м: {total_not_found}, пропущено (неоднозначно): {total_skipped}.'
        return JsonResponse({'success': True, 'messages': [{'type': 'success', 'text': message}], 'updated_count': total_updated})
    
def get_csrf_token_view(request):
    """
    Простой view для получения CSRF-токена.
    """
    return JsonResponse({'csrfToken': get_token(request)})