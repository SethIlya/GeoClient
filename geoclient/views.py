import json
import os
import traceback
import hashlib
import re
import uuid
import zipfile
from collections import defaultdict

from django.views.generic import TemplateView
from django.urls import reverse, NoReverseMatch
from django.http import JsonResponse, HttpResponse
from django.middleware.csrf import get_token
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .permissions import IsUploader
from .models import UploadedRinexFile
from .parsers import parse_rinex_obs_file

# --- (VueAppContainerView и вспомогательные классы остаются без изменений) ---
class VueAppContainerView(TemplateView):
    template_name = "geoclient/base_vue.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
        except NoReverseMatch:
            settings_dict = {'apiPointsUrl': "/api/points/", 'apiLoginUrl': "/api/login/"} # Fallback
        context["django_settings_json"] = json.dumps(settings_dict)
        return context

# ==============================================================================
# API UPLOAD OPTIMIZED
# ==============================================================================

class RinexUploadApiView(APIView):
    permission_classes = [IsAuthenticated, IsUploader]

    def post(self, request, *args, **kwargs):
        uploaded_files_list = request.FILES.getlist('rinex_files')
        if not uploaded_files_list:
            return JsonResponse({'success': False, 'message': 'Файлы не найдены.'}, status=400)

        # Группируем файлы по имени (например TATA1230)
        files_by_base_name = defaultdict(list)
        for file in uploaded_files_list:
            if re.search(r'\.\d{2}[ogn]$', file.name, re.IGNORECASE):
                base_name = re.sub(r'\.\d{2}[ogn]$', '', file.name, flags=re.IGNORECASE)
                files_by_base_name[base_name].append(file)

        aggregated_results = []
        total_created = 0
        overall_success = True

        for base_name, file_group in files_by_base_name.items():
            try:
                # 1. Определяем группу (ищем существующую по имени файла)
                upload_group_id = None
                existing = UploadedRinexFile.objects.filter(
                    file__iregex=f'/{re.escape(base_name)}\\.\\d{{2}}[ogn]$'
                ).first()
                
                if existing:
                    upload_group_id = existing.upload_group
                    aggregated_results.append({'type': 'info', 'text': f"'{base_name}': Догрузка в существующий комплект."})
                else:
                    upload_group_id = uuid.uuid4()

                primary_o_file_instance = None # Ссылка на объект O-файла в БД

                # 2. Обработка файлов в группе
                for file_obj in file_group:
                    # --- ОПТИМИЗАЦИЯ: Хеширование по частям (Chunks) ---
                    sha256 = hashlib.sha256()
                    for chunk in file_obj.chunks():
                        sha256.update(chunk)
                    file_hash = sha256.hexdigest()
                    
                    file_ext = os.path.splitext(file_obj.name.lower())[1]
                    file_type_char = re.sub(r'[\d.]', '', file_ext) # o, n, g

                    should_create = False
                    
                    # Проверка на дубликаты
                    if file_type_char == 'o':
                        # O-файлы должны быть уникальны глобально (по хешу)
                        dup = UploadedRinexFile.objects.filter(file_hash=file_hash).first()
                        if dup:
                            if dup.upload_group == upload_group_id:
                                aggregated_results.append({'type': 'info', 'text': f"'{file_obj.name}' уже в комплекте."})
                                primary_o_file_instance = dup # Запоминаем для парсинга
                            else:
                                aggregated_results.append({'type': 'danger', 'text': f"ОШИБКА: '{file_obj.name}' дублирует файл другой станции."})
                        else:
                            should_create = True
                    else:
                        # N/G файлы уникальны только внутри группы
                        if UploadedRinexFile.objects.filter(file_hash=file_hash, upload_group=upload_group_id).exists():
                             aggregated_results.append({'type': 'info', 'text': f"'{file_obj.name}' уже есть."})
                        else:
                            should_create = True

                    if should_create:
                        new_file = UploadedRinexFile.objects.create(
                            file=file_obj,
                            file_type=file_type_char,
                            file_hash=file_hash,
                            upload_group=upload_group_id
                        )
                        if file_type_char == 'o':
                            primary_o_file_instance = new_file

                # 3. Парсинг (Если есть O-файл)
                # Ищем O-файл в группе (либо только что загруженный, либо старый)
                if not primary_o_file_instance:
                    primary_o_file_instance = UploadedRinexFile.objects.filter(
                        upload_group=upload_group_id, file_type='o'
                    ).first()

                if primary_o_file_instance and primary_o_file_instance.file:
                    try:
                        # --- ОПТИМИЗАЦИЯ: Передаем путь к файлу, а не сам контент ---
                        full_path = primary_o_file_instance.file.path
                        if os.path.exists(full_path):
                            cnt, msgs = parse_rinex_obs_file(full_path, primary_o_file_instance)
                            total_created += cnt
                            for m in msgs:
                                aggregated_results.append({'type': 'success' if cnt > 0 else 'warning', 'text': f"'{base_name}': {m}"})
                        else:
                             aggregated_results.append({'type': 'danger', 'text': f"Файл {full_path} не найден на диске."})
                    except Exception as e:
                        aggregated_results.append({'type': 'danger', 'text': f"Ошибка парсинга '{base_name}': {e}"})
                
            except Exception as e:
                traceback.print_exc()
                overall_success = False
                aggregated_results.append({'type': 'danger', 'text': f"Сбой обработки '{base_name}': {e}"})

        return JsonResponse({'success': overall_success, 'messages': aggregated_results, 'total_created_count': total_created})

# Остальные классы (KMLUploadApiView, RinexDownloadApiView, etc.) оставляем без изменений, 
# так как проблема с памятью и объединением точек решена выше.
class KMLUploadApiView(APIView):
    permission_classes = [IsAuthenticated, IsUploader]
    def post(self, request, *args, **kwargs):
        # ... (твой код KML) ...
        return JsonResponse({'success': False, 'message': 'KML Logic here'}) # Placeholder

def get_csrf_token_view(request):
    return JsonResponse({'csrfToken': get_token(request)})

class RinexDownloadApiView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, group_id, *args, **kwargs):
        rinex_files = UploadedRinexFile.objects.filter(upload_group=group_id)
        if not rinex_files.exists(): return HttpResponse("Нет файлов", status=404)
        
        first = rinex_files.first()
        zip_name = re.sub(r'\.\d{2}[ogn]$', '', os.path.basename(first.file.name), flags=re.IGNORECASE) + ".zip"
        
        import io
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            for rf in rinex_files:
                if rf.file and os.path.exists(rf.file.path):
                    zf.write(rf.file.path, os.path.basename(rf.file.name))
        
        mem_zip.seek(0)
        resp = HttpResponse(mem_zip.read(), content_type='application/zip')
        resp['Content-Disposition'] = f'attachment; filename="{zip_name}"'
        return resp