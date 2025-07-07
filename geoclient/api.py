# geoclient/api.py
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework_gis import filters as gis_filters 
from rest_framework.decorators import action 
from .models import GeodeticPoint, StationDirectoryName 
from .serializers import GeodeticPointSerializer, StationDirectoryNameSerializer
import traceback

# --- НОВЫЕ ИМПОРТЫ ---
from django.http import FileResponse, Http404, HttpResponse
import os
# --- КОНЕЦ НОВЫХ ИМПОРТОВ ---

class PointViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet  
):
    queryset = GeodeticPoint.objects.all().order_by('id')
    serializer_class = GeodeticPointSerializer
    lookup_field = 'id' 
    bbox_filter_field = 'location'
    # filter_backends = (gis_filters.InBBoxFilter,)

    # --- НОВЫЙ ЭКШЕН (ACTION) ДЛЯ СКАЧИВАНИЯ ФАЙЛА ---
    @action(detail=True, methods=['get'], url_path='download-source-file')
    def download_source_file(self, request, id=None):
        """
        Позволяет скачать исходный RINEX файл для указанной точки.
        """
        try:
            point = self.get_object()
            if not point.source_file or not point.source_file.file:
                raise Http404("Для этой точки нет исходного файла.")

            source_file = point.source_file.file
            
            # Проверяем, существует ли файл на диске
            if not source_file.storage.exists(source_file.name):
                raise Http404("Файл не найден в хранилище.")
            
            # Открываем файл и возвращаем его как FileResponse
            # FileResponse автоматически установит нужные заголовки
            response = FileResponse(source_file.open('rb'), as_attachment=True)
            
            # Можно явно указать имя файла для скачивания
            # response['Content-Disposition'] = f'attachment; filename="{os.path.basename(source_file.name)}"'

            return response

        except Http404 as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            traceback.print_exc()
            return Response({"detail": "Внутренняя ошибка сервера при попытке отдать файл."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    # --- КОНЕЦ НОВОГО ЭКШЕНА ---

    def partial_update(self, request, *args, **kwargs):
        point_id = kwargs.get('id') # Используем lookup_field
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True) 
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            self.perform_update(serializer)
        except Exception as e:
            print(f"[Django PointViewSet] CRITICAL ERROR during perform_update/save for instance ID '{instance.id}':")
            traceback.print_exc()
            return Response({"detail": f"Server error during save: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
            
        response_data = serializer.data
        return Response(response_data)

    @action(detail=False, methods=['post'], url_path='delete-multiple')
    def delete_multiple(self, request):
        ids_to_delete_raw = request.data.get('ids', [])
        if not isinstance(ids_to_delete_raw, list) or not ids_to_delete_raw:
            return Response(
                {"detail": "Поле 'ids' должно быть непустым списком ID точек (строк)."},
                status=status.HTTP_400_BAD_REQUEST
            )
        valid_ids = []
        invalid_ids_format = []
        for point_id_raw in ids_to_delete_raw:
            id_str = str(point_id_raw).strip().upper() 
            if id_str:
                valid_ids.append(id_str)
            elif point_id_raw is not None :
                invalid_ids_format.append(str(point_id_raw))
        
        if invalid_ids_format:
             return Response(
                {"detail": f"Некоторые ID являются пустыми строками или имеют неверный формат: {', '.join(invalid_ids_format)}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not valid_ids:
             return Response({"detail": "Не предоставлено корректных ID для удаления."}, status=status.HTTP_400_BAD_REQUEST)

        existing_points_to_delete_qs = Point.objects.filter(id__in=valid_ids)
        existing_ids_before_delete = list(existing_points_to_delete_qs.values_list('id', flat=True))

        if not existing_ids_before_delete:
            return Response({
                    "message": "Ни одна из указанных точек не найдена в базе данных. Удаление не произведено.",
                    "deleted_ids": [], "requested_ids_count": len(valid_ids),
                    "deleted_count": 0, "errors": []
                }, status=status.HTTP_200_OK)
        
        actual_deleted_count, _ = existing_points_to_delete_qs.delete()
        response_data = {
            "message": f"Запрос на удаление обработан. Удалено точек: {actual_deleted_count}.",
            "deleted_ids": existing_ids_before_delete, 
            "requested_ids_count": len(valid_ids),
            "deleted_count": actual_deleted_count,
            "errors": []
        }
        
        ids_not_found = set(valid_ids) - set(existing_ids_before_delete)
        if ids_not_found:
            response_data["message"] += f" Точки с ID: {', '.join(map(str, ids_not_found))} не были найдены или уже удалены."
            for nid in ids_not_found:
                response_data["errors"].append({"id": nid, "error": "Точка не найдена или уже была удалена."})

        return Response(response_data, status=status.HTTP_200_OK)


class StationDirectoryNameViewSet(viewsets.ModelViewSet):
    queryset = StationDirectoryName.objects.all().order_by('name')
    serializer_class = StationDirectoryNameSerializer

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()