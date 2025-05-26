# geoclient/views.py
from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.middleware.csrf import get_token as django_get_csrf_token # Переименовал, чтобы не путать с вашей функцией
from django.urls import reverse, NoReverseMatch
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import UploadedRinexFile
from .parsers import parse_rinex_obs_file, parse_rinex_nav_file
import os
import traceback # Для детального вывода ошибок

# Функция для получения CSRF токена (если вы выберете этот метод вместо csrf_exempt)
def get_csrf_token_view(request): # <--- ЭТА ФУНКЦИЯ ОПРЕДЕЛЕНА ЗДЕСЬ
    return JsonResponse({'csrfToken': django_get_csrf_token(request)})

class VueAppContainerView(TemplateView):
    template_name = "geoclient/vue_app_container.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['csrf_token'] = django_get_csrf_token(self.request) # Используем переименованный импорт
        
        try:
            context['api_points_url'] = reverse('point-list') 
        except NoReverseMatch:
            print("ПРЕДУПРЕЖДЕНИЕ: Не удалось найти URL 'point-list'. Используется запасной.")
            context['api_points_url'] = "/api/points/" 

        try:
            context['api_upload_url'] = reverse('geoclient:api_upload_rinex')
        except NoReverseMatch:
            print("ПРЕДУПРЕЖДЕНИЕ: Не удалось найти URL 'geoclient:api_upload_rinex'. Используется запасной.")
            context['api_upload_url'] = "/api/upload-rinex/" 
        return context

@method_decorator(csrf_exempt, name='dispatch') # Для временного отключения CSRF в разработке
class RinexUploadApiView(View):
    def post(self, request, *args, **kwargs):
        if not request.FILES.get('rinex_file'):
            return JsonResponse({'success': False, 'message': 'Файл не был предоставлен.'}, status=400)

        rinex_file = request.FILES['rinex_file']
        
        file_name_lower = rinex_file.name.lower()
        file_ext_part = os.path.splitext(file_name_lower)[1]
        
        file_type_char = None
        if 'o' in file_ext_part or (file_ext_part == '.rnx' and 'O' in rinex_file.name.upper()):
            file_type_char = 'o'
        elif 'n' in file_ext_part or (file_ext_part == '.rnx' and 'N' in rinex_file.name.upper()):
            file_type_char = 'n'
        elif 'g' in file_ext_part or (file_ext_part == '.rnx' and 'G' in rinex_file.name.upper()):
            file_type_char = 'g'
        else:
            return JsonResponse({
                'success': False, 
                'message': f"Не удалось определить тип файла: {rinex_file.name}"
            }, status=400)

        uploaded_file_instance = UploadedRinexFile.objects.create(
            file=rinex_file,
            file_type=file_type_char,
            remarks=f"Загружен через API: {rinex_file.name}"
        )
        
        file_path_on_disk = uploaded_file_instance.file.path

        created_count = 0
        parse_errors = []
        log_messages = []

        try:
            if file_type_char == 'o':
                created_count, parse_errors = parse_rinex_obs_file(file_path_on_disk, uploaded_file_instance)
                if created_count > 0:
                    log_messages.append({'type': 'success', 'text': f"Файл '{rinex_file.name}' обработан. Добавлено точек: {created_count}."})
                elif not parse_errors:
                     log_messages.append({'type': 'info', 'text': f"Файл '{rinex_file.name}' обработан, новых точек не создано."})
            
            elif file_type_char in ['n', 'g']:
                created_count, parse_errors = parse_rinex_nav_file(file_path_on_disk, file_type_char, uploaded_file_instance)
                log_messages.append({'type': 'info', 'text': f"Файл навигации '{rinex_file.name}' загружен (точки из NAV не создаются)."})
            
            for err_msg in parse_errors:
                log_messages.append({'type': 'warning', 'text': f"Проблема с файлом '{rinex_file.name}': {err_msg}"})

            if not log_messages and not parse_errors:
                 log_messages.append({'type': 'info', 'text': f"Обработка файла '{rinex_file.name}' завершена."})

            return JsonResponse({'success': True, 'messages': log_messages, 'created_count': created_count})

        except Exception as e:
            print(f"Критическая ошибка при обработке файла {rinex_file.name}: {e}")
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': f"Критическая ошибка обработки файла. См. логи сервера."}, status=500)