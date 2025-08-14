from rest_framework import viewsets, mixins, status, views
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

from django.http import FileResponse, Http404
import os

from .models import GeodeticPoint, StationDirectoryName, Observation
from .serializers import GeodeticPointSerializer, StationDirectoryNameSerializer, ObservationSerializer
from .permissions import IsUploader, CanDownloadOrView # <-- Импортируем наши права

# --- API для Аутентификации ---

class LoginView(ObtainAuthToken):
    """
    Принимает POST запрос с 'username' и 'password'.
    Возвращает токен, ID пользователя, имя и список его групп.
    """
    permission_classes = [AllowAny] # Разрешить доступ всем для логина

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        groups = list(user.groups.values_list('name', flat=True))

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'groups': groups
        })

class LogoutView(views.APIView):
    """
    Принимает POST запрос и удаляет токен текущего пользователя.
    """
    permission_classes = [IsAuthenticated] # Только для аутентифицированных

    def post(self, request, *args, **kwargs):
        try:
            # Просто удаляем токен пользователя, который делает запрос
            request.user.auth_token.delete()
        except (AttributeError, Token.DoesNotExist):
            # Если токена нет, ничего страшного
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

class UserStatusView(views.APIView):
    """
    Принимает GET запрос и возвращает информацию о текущем пользователе.
    Используется для проверки валидности токена на фронтенде.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        groups = list(user.groups.values_list('name', flat=True))
        return Response({
            'is_authenticated': True,
            'user_id': user.pk,
            'username': user.username,
            'groups': groups
        })

# --- API для данных ---

class PointViewSet(viewsets.ModelViewSet):
    queryset = GeodeticPoint.objects.all().prefetch_related('observations__source_file').order_by('id')
    serializer_class = GeodeticPointSerializer
    lookup_field = 'id' # Используем 'id' (Marker Name) для поиска

    def get_permissions(self):
        """
        Динамически определяем права в зависимости от действия.
        """
        # На изменение, удаление - только для Uploader
        if self.action in ['update', 'partial_update', 'destroy', 'delete_multiple']:
            return [IsUploader()]
        # На просмотр - для Uploader или Viewer
        return [CanDownloadOrView()]

    @action(detail=False, methods=['post'], url_path='delete-multiple')
    def delete_multiple(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({"detail": "Не предоставлены ID для удаления."}, status=status.HTTP_400_BAD_REQUEST)
        
        points_to_delete = GeodeticPoint.objects.filter(id__in=ids)
        count = points_to_delete.count()
        points_to_delete.delete()
        
        return Response({"message": f"Успешно удалено {count} точек."}, status=status.HTTP_200_OK)


class StationDirectoryNameViewSet(viewsets.ModelViewSet):
    queryset = StationDirectoryName.objects.all().order_by('name')
    serializer_class = StationDirectoryNameSerializer
    # Управлять справочником может только Uploader
    permission_classes = [IsUploader]

class ObservationViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Observation.objects.select_related('source_file').all()
    serializer_class = ObservationSerializer
    # Просматривать и скачивать могут обе роли
    permission_classes = [CanDownloadOrView]

    @action(detail=True, methods=['get'], url_path='download')
    def download_file(self, request, pk=None):
        try:
            observation = self.get_object()
            if not observation.source_file or not observation.source_file.file:
                raise Http404("Для этого наблюдения нет исходного файла.")
            
            file_path = observation.source_file.file.path
            if not os.path.exists(file_path):
                 raise Http404("Файл не найден на диске.")

            return FileResponse(open(file_path, 'rb'), as_attachment=True)
        except Http404 as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"detail": "Ошибка сервера при скачивании файла."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)