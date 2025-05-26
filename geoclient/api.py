# geoclient/api.py
from rest_framework import viewsets
from rest_framework_gis import filters as gis_filters # Для bbox фильтрации, если понадобится

from .models import Point
from .serializers import PointSerializer

class PointViewSet(viewsets.ReadOnlyModelViewSet): # ReadOnly, так как создание через загрузку файлов
    queryset = Point.objects.all().order_by('-timestamp')
    serializer_class = PointSerializer
    # Для фильтрации по видимой области карты (bbox)
    bbox_filter_field = 'location'
    filter_backends = (gis_filters.InBBoxFilter,)
    # Если хотите, чтобы bbox передавался как ?in_bbox=xmin,ymin,xmax,ymax
    # bbox_filter_include_overlapping = True # по умолчанию False (только полностью внутри)