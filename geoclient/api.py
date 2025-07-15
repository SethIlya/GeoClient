# geoclient/api.py

from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import GeodeticPoint, StationDirectoryName, Observation
from .serializers import GeodeticPointSerializer, StationDirectoryNameSerializer, ObservationSerializer
import traceback
import os
from django.http import FileResponse, Http404

class PointViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    queryset = GeodeticPoint.objects.all().prefetch_related('observations__source_file').order_by('id')
    serializer_class = GeodeticPointSerializer
    lookup_field = 'id'
    
    # ... (весь остальной код PointViewSet остается без изменений) ...
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True) 
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
        except Exception as e:
            traceback.print_exc()
            error_details = getattr(e, 'detail', str(e))
            return Response(
                {"detail": f"Ошибка при сохранении: {error_details}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        updated_instance = self.get_queryset().get(id=instance.id)
        response_serializer = self.get_serializer(updated_instance)
        return Response(response_serializer.data)

    @action(detail=False, methods=['post'], url_path='delete-multiple')
    def delete_multiple(self, request):
        ids_to_delete_raw = request.data.get('ids', [])
        if not isinstance(ids_to_delete_raw, list) or not ids_to_delete_raw:
            return Response(
                {"detail": "Поле 'ids' должно быть непустым списком ID точек."},
                status=status.HTTP_400_BAD_REQUEST
            )
        valid_ids = [str(pid).strip().upper() for pid in ids_to_delete_raw if pid]
        
        if not valid_ids:
             return Response({"detail": "Не предоставлено корректных ID для удаления."}, status=status.HTTP_400_BAD_REQUEST)

        points_to_delete = GeodeticPoint.objects.filter(id__in=valid_ids)
        deleted_count, _ = points_to_delete.delete()

        return Response({
            "message": f"Удалено точек: {deleted_count}.",
            "deleted_count": deleted_count,
        }, status=status.HTTP_200_OK)


class StationDirectoryNameViewSet(viewsets.ModelViewSet):
    queryset = StationDirectoryName.objects.all().order_by('name')
    serializer_class = StationDirectoryNameSerializer


# --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: СОЗДАЕМ VIEWSET ДЛЯ СКАЧИВАНИЯ ---
class ObservationViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Этот ViewSet нужен только для одной цели:
    предоставить защищенный endpoint для скачивания файлов.
    """
    queryset = Observation.objects.select_related('source_file').all()
    serializer_class = ObservationSerializer # Используется для swagger/docs

    @action(detail=True, methods=['get'], url_path='download')
    def download_file(self, request, pk=None):
        """
        Находит наблюдение по его ID, затем находит связанный с ним файл
        и отдает его браузеру для скачивания.
        """
        try:
            observation = self.get_object()
            
            # Проверяем, что у наблюдения есть ссылка на файл
            if not observation.source_file or not observation.source_file.file:
                raise Http404("Для этого наблюдения нет исходного файла.")

            source_file_field = observation.source_file.file
            
            # Проверяем, что файл физически существует в хранилище
            if not source_file_field.storage.exists(source_file_field.name):
                raise Http404("Файл не найден в хранилище. Возможно, он был удален с диска.")
            
            # Открываем файл и возвращаем его как FileResponse.
            # `as_attachment=True` говорит браузеру, что файл надо скачать.
            # `filename` указывает имя, под которым файл сохранится.
            response = FileResponse(
                source_file_field.open('rb'), 
                as_attachment=True, 
                filename=os.path.basename(source_file_field.name)
            )
            return response

        except Http404 as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            traceback.print_exc()
            return Response({"detail": "Внутренняя ошибка сервера при попытке отдать файл."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)