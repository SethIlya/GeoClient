# geoclient/api.py

from rest_framework import viewsets, mixins, status, views
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.urls import reverse
from django.http import FileResponse, Http404
import os
import traceback

from .models import GeodeticPoint, StationDirectoryName, Observation, UploadedRinexFile
from .serializers import GeodeticPointSerializer, StationDirectoryNameSerializer, ObservationSerializer
from .permissions import IsUploader, CanDownloadOrView

# --- API для Аутентификации (без изменений) ---

class LoginView(ObtainAuthToken):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        groups = list(user.groups.values_list('name', flat=True))
        return Response({ 'token': token.key, 'user_id': user.pk, 'username': user.username, 'groups': groups })

class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        try:
            request.user.auth_token.delete()
        except (AttributeError, Token.DoesNotExist):
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

class UserStatusView(views.APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        user = request.user
        groups = list(user.groups.values_list('name', flat=True))
        return Response({ 'is_authenticated': True, 'user_id': user.pk, 'username': user.username, 'groups': groups })

# --- API для Файлов (без изменений) ---

class UploadedRinexFileViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = UploadedRinexFile.objects.all()
    permission_classes = [CanDownloadOrView]
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        try:
            rinex_file = self.get_object()
            if not rinex_file.file: raise Http404("Запись о файле есть, но сам файл отсутствует.")
            if not os.path.exists(rinex_file.file.path): raise Http404("Файл не найден на диске.")
            return FileResponse(open(rinex_file.file.path, 'rb'), as_attachment=True)
        except Http404 as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"detail": "Ошибка сервера при скачивании файла."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- API для данных (ИЗМЕНЕНИЯ ЗДЕСЬ) ---

class PointViewSet(viewsets.ModelViewSet):
    queryset = GeodeticPoint.objects.all().prefetch_related('observations__source_file').order_by('id')
    serializer_class = GeodeticPointSerializer
    lookup_field = 'id'

    def get_permissions(self):
        # Применяем строгие права для всех действий, изменяющих данные
        if self.action in ['update', 'partial_update', 'destroy', 'delete_points']:
            return [IsUploader()]
        return [CanDownloadOrView()]

    # --- НОВЫЙ УЛУЧШЕННЫЙ МЕТОД УДАЛЕНИЯ ---
    # Он заменит старый `delete_multiple` и стандартный `destroy`
    @action(detail=False, methods=['post'], url_path='delete-points')
    def delete_points(self, request):
        """
        Принимает список ID пунктов и полностью удаляет их,
        а также все связанные наблюдения и все комплекты RINEX файлов.
        """
        point_ids = request.data.get('ids', [])

        if not isinstance(point_ids, list) or not point_ids:
            return Response(
                {'error': 'Пожалуйста, предоставьте список ID пунктов в поле "ids".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Находим все группы файлов, которые нужно удалить.
        upload_groups_to_delete = set()
        observations = Observation.objects.filter(point_id__in=point_ids).select_related('source_file')
        for obs in observations:
            if obs.source_file and obs.source_file.upload_group:
                upload_groups_to_delete.add(obs.source_file.upload_group)

        # 2. Находим все объекты UploadedRinexFile, принадлежащие этим группам.
        files_to_delete = UploadedRinexFile.objects.filter(upload_group__in=upload_groups_to_delete)
        deleted_file_count = files_to_delete.count()

        # 3. Удаляем каждый файл по отдельности, чтобы сработал метод .delete() модели
        # и удалил физический файл с диска.
        for rinex_file in files_to_delete:
            rinex_file.delete() # Эта команда удаляет физический файл

        # 4. Наконец, удаляем сами геодезические пункты.
        # Связанные с ними наблюдения удалятся автоматически из-за CASCADE.
        points_to_delete = GeodeticPoint.objects.filter(id__in=point_ids)
        deleted_points_count = points_to_delete.count()
        deleted_point_ids = list(points_to_delete.values_list('id', flat=True))
        points_to_delete.delete()

        return Response({
            'message': f'Успешно удалено {deleted_points_count} пунктов и {deleted_file_count} связанных файлов.',
            'deleted_point_ids': deleted_point_ids
        }, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        # Перенаправляем стандартное удаление одного объекта на наш новый метод
        # Это не самый элегантный способ, но гарантирует, что DELETE /api/points/ID/
        # тоже будет работать правильно.
        self.delete_points(self.request._request)


class StationDirectoryNameViewSet(viewsets.ModelViewSet):
    queryset = StationDirectoryName.objects.all().order_by('name')
    serializer_class = StationDirectoryNameSerializer
    permission_classes = [IsUploader]


class ObservationViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Observation.objects.select_related('source_file').all()
    serializer_class = ObservationSerializer
    permission_classes = [CanDownloadOrView]

    def get_file_group(self, observation):
        if not observation.source_file:
            raise Http404("Для этого наблюдения нет исходного файла.")
        group_id = observation.source_file.upload_group
        if not group_id:
            # Для старых файлов без группы возвращаем только сам файл
            return [observation.source_file]
        
        files = UploadedRinexFile.objects.filter(upload_group=group_id).order_by('file')
        if not files:
            raise Http404("Не найдено файлов для скачивания для этой группы.")
        return files

    @action(detail=True, methods=['get'], url_path='download-set')
    def download_set(self, request, pk=None):
        try:
            observation = self.get_object()
            group_id = observation.source_file.upload_group
            if not group_id:
                raise Http404("Для этого наблюдения нет группы файлов.")

            zip_download_url = request.build_absolute_uri(
                reverse('api_download_rinex_group', kwargs={'group_id': group_id})
            )
            return Response({'zip_download_url': zip_download_url})
        except Http404 as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"detail": "Ошибка сервера."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- НОВЫЙ ЭНДПОИНТ ДЛЯ ИНДИВИДУАЛЬНОГО СКАЧИВАНИЯ ---
    @action(detail=True, methods=['get'], url_path='get-individual-urls')
    def get_individual_urls(self, request, pk=None):
        try:
            observation = self.get_object()
            files_in_group = self.get_file_group(observation)
            
            urls = [{
                'filename': os.path.basename(file_obj.file.name),
                'url': request.build_absolute_uri(
                    reverse('rinex-file-download', kwargs={'pk': file_obj.pk})
                )
            } for file_obj in files_in_group]
            
            return Response({'files': urls})
        except Http404 as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"detail": "Ошибка сервера."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)