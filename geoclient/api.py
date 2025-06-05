# geoclient/api.py
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework_gis import filters as gis_filters # Для InBBoxFilter
from rest_framework.decorators import action # Для кастомных actions
from .models import Point
from .serializers import PointSerializer
import traceback

class PointViewSet(
    mixins.RetrieveModelMixin,  # GET /api/points/<pk>/
    mixins.UpdateModelMixin,    # PUT /api/points/<pk>/, PATCH /api/points/<pk>/
    mixins.ListModelMixin,      # GET /api/points/
    mixins.DestroyModelMixin,   # DELETE /api/points/<pk>/
    viewsets.GenericViewSet
):
    """
    ViewSet для управления точками на карте.
    Поддерживает получение списка, получение одной точки, обновление и удаление.
    Также включает кастомный action для пакетного удаления точек.
    """
    queryset = Point.objects.all().order_by('-timestamp') # Сортировка по умолчанию
    serializer_class = PointSerializer
    
    # Настройки для гео-фильтрации (если используется)
    bbox_filter_field = 'location' # Поле модели, по которому будет фильтрация по bbox
    # Можно включить InBBoxFilter, если он нужен:
    # filter_backends = (gis_filters.InBBoxFilter,) 
    # filter_backends = (filters.DjangoFilterBackend, gis_filters.InBBoxFilter,) # Если есть и другие фильтры

    # Метод partial_update для обработки PATCH запросов (обновление части полей)
    # Он наследуется от UpdateModelMixin, но если нужна кастомная логика, можно переопределить.
    # Ваша предыдущая версия partial_update с отладочными print:
    def partial_update(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        print(f"\n[Django PointViewSet] PATCH request for partial_update.")
        print(f"[Django PointViewSet] pk={pk}, request.data: {request.data}")
        
        instance = self.get_object()
        # partial=True означает, что не все поля обязательны в запросе
        serializer = self.get_serializer(instance, data=request.data, partial=True) 
        
        print("[Django PointViewSet] Serializer created. Data for validation:", serializer.initial_data)
        try:
            serializer.is_valid(raise_exception=True) # Валидируем данные
        except Exception as e: # Это может быть serializers.ValidationError
            print("[Django PointViewSet] Validation error:", e)
            if hasattr(serializer, 'errors'): 
                print("[Django PointViewSet] Serializer errors:", serializer.errors)
            # raise_exception=True уже выбросит ошибку, которая будет обработана DRF
            # и вернет 400 Bad Request с ошибками. Этот raise можно убрать.
            # raise 
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) # Явный возврат ошибки

        print("[Django PointViewSet] Serializer valid. Performing update...")
        try:
            self.perform_update(serializer) # Сохраняет изменения
            print(f"[Django PointViewSet] perform_update for instance ID {instance.id} successful.")
        except Exception as e:
            print(f"[Django PointViewSet] CRITICAL ERROR during perform_update/save for instance ID {instance.id}:")
            traceback.print_exc()
            return Response({"detail": f"Server error during save: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Сброс кеша prefetch, если он есть (хорошая практика)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
            
        response_data = serializer.data # Сериализованные данные обновленного объекта
        
        # Отладочный вывод структуры ответа
        print("[Django PointViewSet] Serializer.data AFTER save (response to client):")
        if isinstance(response_data, dict) and response_data.get('properties'):
            print(f"  ID in properties: {response_data['properties'].get('id')}")
            print(f"  point_type in properties: {response_data['properties'].get('point_type')}")
            print(f"  name in properties: {response_data['properties'].get('name')}")
        else: 
            print(f"  Response data structure: {response_data}")
            
        print(f"[Django PointViewSet] Sending 200 OK response for pk={pk}.")
        return Response(response_data)

    # Кастомный action для пакетного удаления точек
    # Доступен по POST на /api/points/delete-multiple/
    @action(detail=False, methods=['post'], url_path='delete-multiple')
    def delete_multiple(self, request):
        """
        Удаляет несколько точек по списку их ID.
        Ожидает POST-запрос с JSON-телом: {"ids": [id1, id2, ...]}
        """
        ids_to_delete_raw = request.data.get('ids', [])

        if not isinstance(ids_to_delete_raw, list):
            return Response(
                {"detail": "Поле 'ids' должно быть списком (массивом) ID точек."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not ids_to_delete_raw:
             return Response(
                {"detail": "Список ID для удаления ('ids') не может быть пустым."},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_ids = []
        invalid_ids_format = []
        for point_id_raw in ids_to_delete_raw:
            try:
                # Убедимся, что ID - это целое число
                valid_ids.append(int(point_id_raw))
            except (ValueError, TypeError):
                invalid_ids_format.append(str(point_id_raw))
        
        if invalid_ids_format:
             return Response(
                {"detail": f"Некоторые ID имеют неверный формат (должны быть целыми числами): {', '.join(invalid_ids_format)}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not valid_ids: # Если все ID были невалидными
             return Response(
                {"detail": "Не предоставлено корректных ID для удаления."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Находим ID точек, которые действительно существуют в базе данных из предоставленного списка
        existing_points_to_delete_qs = Point.objects.filter(id__in=valid_ids)
        existing_ids_before_delete = list(existing_points_to_delete_qs.values_list('id', flat=True))

        if not existing_ids_before_delete:
            return Response(
                {
                    "message": "Ни одна из указанных точек не найдена в базе данных. Удаление не произведено.",
                    "deleted_ids": [],
                    "requested_ids_count": len(valid_ids),
                    "deleted_count": 0,
                    "errors": []
                },
                status=status.HTTP_200_OK # Или 404, если считать это ошибкой "не найдено"
            )
        
        # Производим удаление
        actual_deleted_count, _ = existing_points_to_delete_qs.delete()
        # .delete() возвращает кортеж: (общее_кол-во_удаленных_объектов, словарь_с_кол-вом_по_типам)

        response_data = {
            "message": f"Запрос на удаление обработан. Удалено точек: {actual_deleted_count}.",
            "deleted_ids": existing_ids_before_delete, # ID точек, которые были найдены и удалены
            "requested_ids_count": len(valid_ids),
            "deleted_count": actual_deleted_count,
            "errors": [] # Сюда можно добавлять информацию об ID, которые не удалось удалить по другим причинам (например, права доступа)
        }
        
        ids_not_found_or_not_deleted = set(valid_ids) - set(existing_ids_before_delete)
        if ids_not_found_or_not_deleted:
            response_data["message"] += f" Точки с ID: {', '.join(map(str, ids_not_found_or_not_deleted))} не были найдены или уже удалены."
            for nid in ids_not_found_or_not_deleted:
                response_data["errors"].append({"id": nid, "error": "Точка не найдена или уже была удалена."})


        print(f"[PointViewSet/delete_multiple] Запрошено удаление ID: {ids_to_delete_raw}. "
              f"Найдены и предпринята попытка удаления для ID: {existing_ids_before_delete}. "
              f"Фактически удалено: {actual_deleted_count}.")
              
        return Response(response_data, status=status.HTTP_200_OK)