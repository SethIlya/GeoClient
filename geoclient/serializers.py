# geoclient/serializers.py
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from .models import Point # Убедитесь, что модель Point импортирована

class PointSerializer(GeoFeatureModelSerializer):
    """
    Сериализатор для модели Point, преобразует данные в формат GeoJSON Feature.
    С кастомным to_representation для гарантии наличия ключевых полей в properties.
    """
    # Вычисляемые поля только для чтения
    latitude = serializers.FloatField(source='location.y', read_only=True, allow_null=True)
    longitude = serializers.FloatField(source='location.x', read_only=True, allow_null=True)
    timestamp_display = serializers.DateTimeField(
        source='timestamp', 
        format="%Y-%m-%d %H:%M:%S", 
        read_only=True,
        allow_null=True 
    )
    point_type_display = serializers.CharField(source='get_point_type_display', read_only=True)

    class Meta:
        model = Point
        geo_field = "location"
        
        # Поля, которые мы хотим видеть в 'properties'.
        # GeoFeatureModelSerializer использует их для формирования properties.
        fields = (
            'id',                 # Включаем сюда, чтобы to_representation мог его обработать
            'name',
            'description',
            'point_type',
            'point_type_display', 
            'timestamp',          
            'timestamp_display',  
            'latitude',           
            'longitude',          
            'raw_x',
            'raw_y',
            'raw_z',
            'source_file_id'      
        )
        
        read_only_fields = (
            'id', 
            'timestamp_display', 
            'latitude', 
            'longitude', 
            'point_type_display',
            'raw_x', 
            'raw_y',
            'raw_z',
            'source_file_id'
        )

    def validate_name(self, value):
        name = value.strip() if isinstance(value, str) else ""
        if not name:
            raise serializers.ValidationError("Имя точки не может быть пустым.")
        if len(name) > 255:
            raise serializers.ValidationError("Имя точки слишком длинное (макс. 255 символов).")
        return name

    def validate_description(self, value):
        return value.strip() if isinstance(value, str) else ""

    def validate_point_type(self, value):
        valid_types = [pt[0] for pt in Point.POINT_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Недопустимый тип точки: '{value}'. Доступные типы: {', '.join(valid_types)}"
            )
        return value

    def to_representation(self, instance):
        """
        Кастомизация представления GeoJSON Feature.
        Гарантируем, что все поля из Meta.fields (кроме geo_field) 
        и 'id' присутствуют в 'properties'.
        """
        representation = super().to_representation(instance) # Получаем базовый GeoJSON

        # Гарантируем наличие 'properties'
        if 'properties' not in representation or not isinstance(representation['properties'], dict):
            representation['properties'] = {}

        # Добавляем/обновляем все поля из Meta.fields в 'properties'
        # Это должно включать 'id', 'name', 'description', 'point_type' и т.д.
        for field_name in self.Meta.fields:
            if field_name == self.Meta.geo_field: # 'location' идет в 'geometry'
                continue

            # Если поле является вычисляемым в сериализаторе (как latitude, longitude, *_display)
            if field_name in self.fields and isinstance(self.fields[field_name], serializers.Field) and self.fields[field_name].read_only:
                # Для вычисляемых полей берем значение из уже сформированного representation['properties']
                # или вычисляем заново, если его там нет
                if field_name not in representation['properties']:
                     try:
                        # Пытаемся получить значение через get_attribute, если это поле сериализатора
                        representation['properties'][field_name] = self.fields[field_name].get_attribute(instance)
                     except AttributeError:
                        # Если это простое поле модели, которое read_only, но не вычисляемое в сериализаторе
                        if hasattr(instance, field_name):
                           representation['properties'][field_name] = getattr(instance, field_name)
            # Для обычных полей модели
            elif hasattr(instance, field_name):
                representation['properties'][field_name] = getattr(instance, field_name)
        
        # Особое внимание к 'id', так как он критичен
        if hasattr(instance, 'id'):
            representation['properties']['id'] = instance.id # Гарантируем, что ID есть в properties
            if 'id' not in representation: # Гарантируем, что ID есть на верхнем уровне
                representation['id'] = instance.id
        
        # print(f"[PointSerializer to_representation] для instance ID {getattr(instance, 'id', 'N/A')}: {representation['properties']}")
        return representation