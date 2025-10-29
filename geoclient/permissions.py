# geoclient/permissions.py
from rest_framework import permissions

class IsUploader(permissions.BasePermission):
    """
    Разрешает доступ только пользователям из группы 'Uploader'.python manage.py migrate
    Это право дает возможность изменять и удалять данные.
    """
    message = "У вас нет прав для выполнения этого действия (требуется роль 'Uploader')."
    
    def has_permission(self, request, view):
        # Проверяем, что пользователь аутентифицирован и состоит в группе 'Uploader'
        return request.user and request.user.is_authenticated and request.user.groups.filter(name='Uploader').exists()

class CanDownloadOrView(permissions.BasePermission):
    """
    Разрешает доступ пользователям из групп 'Uploader' ИЛИ 'Viewer'.
    Это право дает возможность только просматривать и скачивать данные.
    """
    message = "У вас нет прав для просмотра этого контента."

    def has_permission(self, request, view):
        # Проверяем, что пользователь аутентифицирован и состоит хотя бы в одной из нужных групп
        return request.user and request.user.is_authenticated and request.user.groups.filter(name__in=['Uploader', 'Viewer']).exists()