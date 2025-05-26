# geoclient/serializers.py
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from .models import Point

class PointSerializer(GeoFeatureModelSerializer):
    # Дополнительные поля, которые не являются частью GeoJSON properties по умолчанию
    latitude = serializers.FloatField(source='location.y', read_only=True)
    longitude = serializers.FloatField(source='location.x', read_only=True)
    timestamp_display = serializers.DateTimeField(source='timestamp', format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = Point
        geo_field = "location"  # Поле с геометрией
        fields = ('id', 'name', 'timestamp_display', 'description', 'latitude', 'longitude') # 'location' будет в feature.geometry
        # Если вы хотите, чтобы 'location' (PointField) было также в properties как WKT или что-то еще,
        # то добавьте его в fields и, возможно, кастомный SerializerMethodField.
        # Но для Leaflet обычно достаточно GeoJSON структуры.