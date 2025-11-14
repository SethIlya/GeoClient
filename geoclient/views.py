# geoclient/views.py

import json
import os
import traceback
import hashlib
import io
import re
import uuid
import zipfile
from collections import defaultdict

from django.views.generic import TemplateView
from django.urls import reverse, NoReverseMatch
from django.contrib.gis.geos import Point as DjangoPoint
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Transform
from django.http import JsonResponse, HttpResponse
from django.middleware.csrf import get_token

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .permissions import IsUploader
from .models import UploadedRinexFile
from .parsers import parse_rinex_obs_file

# ==============================================================================
# VIEW ДЛЯ ОТОБРАЖЕНИЯ VUE ПРИЛОЖЕНИЯ
# ==============================================================================
class VueAppContainerView(TemplateView):
    template_name = "geoclient/base_vue.html"

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
                'apiCsrfUrl': '/api/get-csrf-token/',
            }

        context["django_settings_json"] = json.dumps(settings_dict)
        return context

# ==============================================================================
# API VIEWS ДЛЯ ЗАГРУЗКИ ФАЙЛОВ
# ==============================================================================

class RinexUploadApiView(APIView):
    permission_classes = [IsAuthenticated, IsUploader]

    def post(self, request, *args, **kwargs):
        uploaded_files_list = request.FILES.getlist('rinex_files')
        if not uploaded_files_list:
            return JsonResponse({'success': False, 'message': 'Файлы не были предоставлены.'}, status=400)

        files_by_base_name = defaultdict(list)
        unparsable_files = []

        for file in uploaded_files_list:
            if re.search(r'\.\d{2}[ogn]$', file.name, re.IGNORECASE):
                base_name = re.sub(r'\.\d{2}[ogn]$', '', file.name, flags=re.IGNORECASE)
                files_by_base_name[base_name].append(file)
            else:
                unparsable_files.append(file.name)

        aggregated_results_messages = []
        total_created_count_all_files = 0
        overall_success_flag = True
        
        if unparsable_files:
            msg = f"Проигнорированы файлы с неверным форматом имени: {', '.join(unparsable_files)}"
            aggregated_results_messages.append({'type': 'warning', 'text': msg})

        for base_name, file_group in files_by_base_name.items():
            try:
                # --- ИЗМЕНЕННАЯ ЛОГИКА: ПОИСК СУЩЕСТВУЮЩЕЙ ГРУППЫ ---
                upload_group_id = None
                
                # Ищем любой файл в БД, который относится к этому же комплекту (base_name)
                # Мы используем регулярное выражение, чтобы найти файлы вида /base_name.YY[ogn]
                # Это надежно работает с нашей функцией rinex_file_path
                existing_file_in_group = UploadedRinexFile.objects.filter(
                    file__iregex=f'/{re.escape(base_name)}\\.\\d{{2}}[ogn]$'
                ).first()

                if existing_file_in_group:
                    upload_group_id = existing_file_in_group.upload_group
                    msg = f"Комплект '{base_name}': Найден существующий комплект. Файлы будут добавлены к нему."
                    aggregated_results_messages.append({'type': 'info', 'text': msg})
                else:
                    upload_group_id = uuid.uuid4()

                # --- Обработка и сохранение файлов ---
                primary_file_in_request = None
                
                for file_from_request in file_group:
                    file_from_request.seek(0)
                    file_content_bytes = file_from_request.read()
                    sha256_hash = hashlib.sha256(file_content_bytes).hexdigest()
                    
                    if UploadedRinexFile.objects.filter(file_hash=sha256_hash).exists():
                        msg = f"Файл '{file_from_request.name}' уже существует в базе, пропущен."
                        aggregated_results_messages.append({'type': 'info', 'text': msg})
                        continue

                    file_ext = os.path.splitext(file_from_request.name.lower())[1]
                    file_type_char = re.sub(r'[\d.]', '', file_ext)
                    
                    UploadedRinexFile.objects.create(
                        file=file_from_request,
                        file_type=file_type_char,
                        file_hash=sha256_hash,
                        upload_group=upload_group_id # Используем найденный или новый ID
                    )
                    
                    if file_type_char == 'o':
                        primary_file_in_request = file_from_request

                # --- Парсинг и создание/обновление наблюдения ---
                # Нам нужен основной .o файл для парсинга. Он может быть в текущей загрузке или уже в БД.
                primary_file_to_parse = None
                primary_file_instance = None

                if primary_file_in_request:
                    primary_file_to_parse = primary_file_in_request
                    primary_file_to_parse.seek(0)
                    hash_of_primary = hashlib.sha256(primary_file_to_parse.read()).hexdigest()
                    primary_file_instance = UploadedRinexFile.objects.get(file_hash=hash_of_primary)
                else:
                    # Ищем .o файл в уже существующей группе в БД
                    existing_o_file = UploadedRinexFile.objects.filter(upload_group=upload_group_id, file_type='o').first()
                    if existing_o_file:
                        primary_file_instance = existing_o_file
                        primary_file_to_parse = existing_o_file.file

                if primary_file_to_parse:
                    primary_file_to_parse.seek(0)
                    text_stream = io.StringIO(primary_file_to_parse.read().decode('ascii', errors='ignore'))
                    created_count, parse_messages = parse_rinex_obs_file(text_stream, primary_file_instance)

                    total_created_count_all_files += created_count
                    for msg in parse_messages:
                        aggregated_results_messages.append({'type': 'success', 'text': f"Комплект '{base_name}': {msg}"})
                else:
                    msg = f"Комплект '{base_name}': Файлы сохранены, но основной файл (*.YYo) для создания наблюдения не найден ни в текущей загрузке, ни в базе."
                    aggregated_results_messages.append({'type': 'warning', 'text': msg})

                # --- Финальная проверка на полноту комплекта ---
                all_files_in_group = UploadedRinexFile.objects.filter(upload_group=upload_group_id)
                found_types = set(all_files_in_group.values_list('file_type', flat=True))
                if len(found_types) < 3:
                    missing_types = {'o', 'n', 'g'} - found_types
                    missing_str = ", ".join([f"*.{t}" for t in missing_types])
                    msg = f"Комплект '{base_name}': Внимание, комплект все еще неполный. Отсутствуют файлы: {missing_str}."
                    aggregated_results_messages.append({'type': 'warning', 'text': msg})

            except Exception as e:
                traceback.print_exc()
                overall_success_flag = False
                msg = f"Комплект '{base_name}': Критическая ошибка: {str(e)}"
                aggregated_results_messages.append({'type': 'danger', 'text': msg})

        return JsonResponse({'success': overall_success_flag, 'messages': aggregated_results_messages, 'total_created_count': total_created_count_all_files})

# --- Остальная часть файла без изменений ---

def _parse_kml_description(description_text):
    data = {'network_class': None, 'index_name': None, 'center_type': None, 'mark_number': None, 'point_type': 'default'}
    patterns = { 'index_name': r'индекс:\s*([^,]+)', 'network_class': r'класс:\s*([^,]+)', 'center_type': r'центр:\s*([^,]+)', 'mark_number': r'номер марки:\s*([^,]+)', }
    for key, pattern in patterns.items():
        match = re.search(pattern, description_text, re.IGNORECASE)
        if match: data[key] = match.group(1).strip()
    if data.get('network_class'):
        nc_norm = data['network_class'].lower().replace(' ', '').replace('-', '')
        if any(s in nc_norm for s in ['вгс', 'фагс', 'сгс1']): data['point_type'] = 'astro'
        elif 'ггс' in nc_norm: data['point_type'] = 'ggs'
        elif 'городская' in nc_norm: data['point_type'] = 'survey'
        elif any(s in nc_norm for s in ['гнс', 'нивелирная']): data['point_type'] = 'leveling'
    return data

class KMLUploadApiView(APIView):
    permission_classes = [IsAuthenticated, IsUploader]
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

def get_csrf_token_view(request):
    return JsonResponse({'csrfToken': get_token(request)})

class RinexDownloadApiView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, group_id, *args, **kwargs):
        rinex_files = UploadedRinexFile.objects.filter(upload_group=group_id)
        if not rinex_files.exists():
            return HttpResponse("Файлы не найдены.", status=404)
        first_file_db_name = os.path.basename(rinex_files.first().file.name)
        # Для имени архива берем имя файла без расширения
        zip_filename_base = re.sub(r'\.\d{2}[ogn]$', '', first_file_db_name, flags=re.IGNORECASE)
        zip_filename = f"{zip_filename_base}.zip"
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for rinex_file in rinex_files:
                arcname = os.path.basename(rinex_file.file.name)
                with rinex_file.file.open('rb') as f:
                    zf.writestr(arcname, f.read())
        memory_file.seek(0)
        response = HttpResponse(memory_file.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        return response