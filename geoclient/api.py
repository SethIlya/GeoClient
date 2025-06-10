# geoclient/api.py
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework_gis import filters as gis_filters 
from rest_framework.decorators import action 
from .models import Point, StationDirectoryName 
from .serializers import PointSerializer, StationDirectoryNameSerializer
import traceback

class PointViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet  # Используем GenericViewSet и явно добавляем нужные mixins
):
    queryset = Point.objects.all().order_by('id')
    serializer_class = PointSerializer
    lookup_field = 'id' 
    bbox_filter_field = 'location'
    # filter_backends = (gis_filters.InBBoxFilter,)

    def partial_update(self, request, *args, **kwargs):
        point_id = kwargs.get('id') # Используем lookup_field
        # print(f"\n[Django PointViewSet] PATCH request for partial_update.")
        # print(f"[Django PointViewSet] id='{point_id}', request.data: {request.data}")
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True) 
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            # print("[Django PointViewSet] Validation error:", e)
            # if hasattr(serializer, 'errors'): print("[Django PointViewSet] Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # print("[Django PointViewSet] Serializer valid. Performing update...")
        try:
            self.perform_update(serializer)
            # print(f"[Django PointViewSet] perform_update for instance ID '{instance.id}' successful.")
        except Exception as e:
            print(f"[Django PointViewSet] CRITICAL ERROR during perform_update/save for instance ID '{instance.id}':")
            traceback.print_exc()
            return Response({"detail": f"Server error during save: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
            
        response_data = serializer.data
        # print("[Django PointViewSet] Serializer.data AFTER save (response to client):", response_data)
        # print(f"[Django PointViewSet] Sending 200 OK response for id='{point_id}'.")
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
            # ID точек теперь строки и могут содержать буквы, поэтому приводим к строке и убираем пробелы
            # Также приводим к верхнему регистру, если ID в БД хранятся так (модель Point.id)
            id_str = str(point_id_raw).strip().upper() 
            if id_str: # Проверяем, что строка не пустая после strip
                valid_ids.append(id_str)
            elif point_id_raw is not None : # Если исходное значение не None, но стало пустым после strip
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


# --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
class StationDirectoryNameViewSet(viewsets.ModelViewSet): # ModelViewSet уже включает все CRUD mixins
    """
    ViewSet для CRUD-операций со справочником имен станций.
    ModelViewSet предоставляет 'list', 'create', 'retrieve', 'update', 
    'partial_update', и 'destroy' actions.
    """
    queryset = StationDirectoryName.objects.all().order_by('name')
    serializer_class = StationDirectoryNameSerializer

    def perform_create(self, serializer):
        # print(f"[StationDirectoryNameViewSet] Создание записи: {serializer.validated_data.get('name')}")
        serializer.save()

    def perform_update(self, serializer):
        # print(f"[StationDirectoryNameViewSet] Обновление ID {serializer.instance.id}: {serializer.validated_data.get('name')}")
        serializer.save()

    def perform_destroy(self, instance):
        # print(f"[StationDirectoryNameViewSet] Удаление ID {instance.id}: {instance.name}")
        instance.delete()

    # Убрали action 'clear_all_names', так как он был не нужен