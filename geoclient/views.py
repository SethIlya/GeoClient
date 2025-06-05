# geoclient/views.py
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.middleware.csrf import get_token as django_get_csrf_token
from django.urls import reverse, NoReverseMatch
# from django.utils.decorators import method_decorator # Если будете использовать csrf_exempt
# from django.views.decorators.csrf import csrf_exempt # Рекомендуется убрать для production
import os
import traceback

from .models import UploadedRinexFile # Убедитесь, что модель импортируется
from .parsers import parse_rinex_obs_file, parse_rinex_nav_file # Убедитесь, что парсеры импортируются

class VueAppContainerView(TemplateView):
    template_name = "geoclient/vue_app_container.html" # Путь к вашему главному HTML-шаблону для Vue

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем и передаем CSRF-токен. Это должно помочь CsrfViewMiddleware установить cookie.
        context['csrf_token'] = django_get_csrf_token(self.request)
        
        # Передаем URL-адреса API в контекст, чтобы Vue мог их использовать
        try:
            context['api_points_url'] = reverse('point-list') # 'point-list' - это имя из router.register DRF
        except NoReverseMatch:
            context['api_points_url'] = "/api/points/" # Запасной URL
            print("ПРЕДУПРЕЖДЕНИЕ (VueAppContainerView): Не удалось получить URL для 'point-list' через reverse. Используется запасной '/api/points/'.")

        try:
            context['api_upload_url'] = reverse('geoclient:api_upload_rinex') # 'geoclient:api_upload_rinex' - имя из geoclient/urls.py
        except NoReverseMatch:
            context['api_upload_url'] = "/api/upload-rinex/" # Запасной URL
            print("ПРЕДУПРЕЖДЕНИЕ (VueAppContainerView): Не удалось получить URL для 'geoclient:api_upload_rinex' через reverse. Используется запасной '/api/upload-rinex/'.")
        
        try:
            context['api_csrf_url'] = reverse('geoclient:get_csrf_token') # 'geoclient:get_csrf_token' - имя из geoclient/urls.py
        except NoReverseMatch:
            context['api_csrf_url'] = "/api/get-csrf-token/" # Запасной URL
            print("ПРЕДУПРЕЖДЕНИЕ (VueAppContainerView): Не удалось получить URL для 'geoclient:get_csrf_token' через reverse. Используется запасной '/api/get-csrf-token/'.")
            
        print(f"[VueAppContainerView] Контекст для шаблона: csrf_token='{context['csrf_token']}', api_points_url='{context['api_points_url']}', api_upload_url='{context['api_upload_url']}', api_csrf_url='{context['api_csrf_url']}'")
        return context

# Если вы используете CSRF_TRUSTED_ORIGINS в settings.py (что рекомендуется),
# то csrf_exempt обычно не нужен, и его лучше убрать.
# @method_decorator(csrf_exempt, name='dispatch')
class RinexUploadApiView(View):
    def post(self, request, *args, **kwargs):
        # Получаем список всех файлов, отправленных с ключом 'rinex_files'
        uploaded_files_list = request.FILES.getlist('rinex_files')

        if not uploaded_files_list:
            return JsonResponse({'success': False, 'message': 'Файлы не были предоставлены.'}, status=400)

        aggregated_results_messages = [] # Собираем все сообщения для фронтенда
        total_created_count_all_files = 0
        overall_success_flag = True # Станет False, если хотя бы один файл вызовет критическую ошибку

        for rinex_file in uploaded_files_list:
            file_name_original = rinex_file.name
            # file_name_lower = file_name_original.lower() # Не используется напрямую, но может быть полезно
            file_ext_part = os.path.splitext(file_name_original.lower())[1] # Используем lower для расширения
            file_type_char = None

            # Определение типа файла
            # Учитываем, что имя файла может содержать тип в верхнем регистре, например, 'BRDC00GNI_R_20240010000_01D_GN.rnx'
            if 'o' in file_ext_part or ('.rnx' in file_ext_part and 'O' in file_name_original.upper()):
                file_type_char = 'o'
            elif 'n' in file_ext_part or ('.rnx' in file_ext_part and 'N' in file_name_original.upper()):
                file_type_char = 'n'
            elif 'g' in file_ext_part or ('.rnx' in file_ext_part and 'G' in file_name_original.upper()):
                file_type_char = 'g'
            else:
                aggregated_results_messages.append({
                    'type': 'danger',
                    'text': f"Файл '{file_name_original}': Не удалось определить тип файла по расширению '{file_ext_part}' или имени."
                })
                overall_success_flag = False
                continue

            # Создаем запись в БД для загруженного файла
            uploaded_file_instance = UploadedRinexFile.objects.create(file=rinex_file, file_type=file_type_char)
            
            created_count_this_file = 0
            parse_messages_this_file = []

            try:
                # Передаем file-like объект (uploaded_file_instance.file) в парсеры
                if file_type_char == 'o':
                    created_count_this_file, parse_messages_this_file = parse_rinex_obs_file(
                        uploaded_file_instance.file, uploaded_file_instance
                    )
                elif file_type_char in ['n', 'g']:
                    created_count_this_file, parse_messages_this_file = parse_rinex_nav_file(
                        uploaded_file_instance.file, file_type_char, uploaded_file_instance
                    )
                
                total_created_count_all_files += created_count_this_file

                # Формируем сообщения для этого файла на основе результатов парсера
                for item_msg in parse_messages_this_file:
                    if isinstance(item_msg, str):
                        msg_type_parsed = 'info' # По умолчанию
                        lower_item_msg = item_msg.lower()
                        if "ошибка" in lower_item_msg or "критическая" in lower_item_msg:
                            msg_type_parsed = 'warning'
                        elif "пропущена (дубликат)" in lower_item_msg:
                            msg_type_parsed = 'info'
                        elif "создана" in lower_item_msg: # Успешное создание точки
                            msg_type_parsed = 'success'
                        aggregated_results_messages.append({'type': msg_type_parsed, 'text': f"Файл '{file_name_original}': {item_msg}"})
                    elif isinstance(item_msg, dict) and 'text' in item_msg and 'type' in item_msg:
                        aggregated_results_messages.append({'type': item_msg['type'], 'text': f"Файл '{file_name_original}': {item_msg['text']}"})

                # Если для OBS файла не было сообщений от парсера и не создано точек, добавляем общее инфо
                if file_type_char == 'o' and not parse_messages_this_file and created_count_this_file == 0:
                     aggregated_results_messages.append({
                        'type': 'info',
                        'text': f"Файл '{file_name_original}' обработан, новых точек не создано (возможно, файл пуст, все точки дубликаты или парсер не вернул сообщений)."
                    })
                # Для NAV/GLO, если парсер не вернул сообщений (например, его заглушка просто вернула пустой список)
                elif file_type_char != 'o' and not parse_messages_this_file:
                     aggregated_results_messages.append({
                        'type': 'info',
                        'text': f"Файл '{file_name_original}' (тип: {file_type_char.upper()}) обработан (парсер не вернул сообщений)."
                    })

            except Exception as e:
                traceback.print_exc() 
                overall_success_flag = False 
                aggregated_results_messages.append({
                    'type': 'danger',
                    'text': f"Файл '{file_name_original}': Критическая ошибка во время обработки на сервере: {str(e)}"
                })
        
        return JsonResponse({
            'success': overall_success_flag, 
            'messages': aggregated_results_messages, # <--- Вот этот массив сообщений
            'total_created_count': total_created_count_all_files
        })

def get_csrf_token_view(request):
    """
    Возвращает CSRF-токен в JSON-ответе.
    Используется фронтендом, если начальный CSRF-токен не был получен из шаблона.
    """
    token = django_get_csrf_token(request)
    print(f"[get_csrf_token_view] Возвращаемый токен: {token}")
    return JsonResponse({'csrfToken': token})