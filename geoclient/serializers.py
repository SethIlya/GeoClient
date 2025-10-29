# geoclient/serializers.py

from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from .models import GeodeticPoint, Observation, StationDirectoryName

class ObservationSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Observation."""
    latitude = serializers.FloatField(source='location.y', read_only=True)
    longitude = serializers.FloatField(source='location.x', read_only=True)
    timestamp_display = serializers.DateTimeField(source='timestamp', format="%Y-%m-%d %H:%M:%S", read_only=True)
    source_file_url = serializers.FileField(source='source_file.file', read_only=True)
    duration_display = serializers.SerializerMethodField()

    class Meta:
        model = Observation
        fields = (
            'id', 'timestamp', 'timestamp_display', 
            'duration', 'duration_display',
            'location', 'latitude', 'longitude',
            'receiver_number', 'antenna_height',
            'source_file_url'
        )

    def get_duration_display(self, obj):
        """
        Возвращает человекочитаемое представление длительности.
        """
        if not obj.duration:
            return None
        
        total_seconds = int(obj.duration.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days} дн")
        if hours > 0:
            parts.append(f"{hours} ч")
        if minutes > 0:
            parts.append(f"{minutes} мин")
        if seconds > 0 or not parts:
             parts.append(f"{seconds} сек")
             
        return " ".join(parts)


class GeodeticPointSerializer(GeoFeatureModelSerializer):
    """
    Сериализатор для модели GeodeticPoint.
    Включает в себя вложенный список всех наблюдений (observations).
    """
    observations = ObservationSerializer(many=True, read_only=True)
    latitude = serializers.FloatField(source='location.y', read_only=True)
    longitude = serializers.FloatField(source='location.x', read_only=True)
    point_type_display = serializers.CharField(source='get_point_type_display', read_only=True)
    
    latest_observation_data = serializers.SerializerMethodField()

    class Meta:
        model = GeodeticPoint
        geo_field = "location"
        fields = (
            'id', 'station_name', 'description', 'point_type', 'point_type_display',
            'latitude', 'longitude', 'observations',
            'network_class', 'index_name', 'center_type', 'status', 'mark_number',
            'latest_observation_data'
        )
        # <-- ИЗМЕНЕНИЕ: Убрали поля KML из read_only_fields -->
        # Теперь их можно редактировать через PATCH/PUT запросы.
        read_only_fields = (
            'id', 'latitude', 'longitude', 'point_type_display', 'observations',
            'latest_observation_data'
        )
        
    def get_latest_observation_data(self, obj):
        """
        Возвращает данные из самого свежего наблюдения.
        """
        latest_obs = obj.observations.order_by('-timestamp').first()
        if latest_obs:
            serializer = ObservationSerializer(latest_obs)
            return serializer.data
        return None 

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if 'properties' in representation:
            if 'id' not in representation['properties']:
                 representation['properties']['id'] = instance.id
            representation['properties']['latest_observation_data'] = self.get_latest_observation_data(instance)
        return representation


class StationDirectoryNameSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели StationDirectoryName (справочник имен станций).
    """
    class Meta:
        model = StationDirectoryName
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        name_stripped = value.strip()
        if not name_stripped:
            raise serializers.ValidationError("Имя станции в справочнике не может быть пустым.")
        if len(name_stripped) > 255:
            raise serializers.ValidationError("Имя станции в справочнике слишком длинное (макс. 255 символов).")
        
        queryset = StationDirectoryName.objects.filter(name__iexact=name_stripped)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(f"Имя станции '{name_stripped}' уже существует в справочнике (без учета регистра).")
            
        return name_stripped