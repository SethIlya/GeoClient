# geoclient/serializers.py
from rest_framework_gis.serializers import GeoFeatureModelSerializer, GeometrySerializerMethodField
from rest_framework import serializers
from .models import Point, StationDirectoryName # Добавляем импорт StationDirectoryName

class PointSerializer(GeoFeatureModelSerializer):
    """
    Сериализатор для модели Point.
    Преобразует экземпляры Point в формат GeoJSON и обратно (если разрешено).
    """


    # Вычисляемые поля для удобства фронтенда (только для чтения)
    latitude = serializers.FloatField(source='location.y', read_only=True, allow_null=True)
    longitude = serializers.FloatField(source='location.x', read_only=True, allow_null=True)
    
    timestamp_display = serializers.DateTimeField(
        source='timestamp', 
        format="%Y-%m-%d %H:%M:%S", # Или любой другой нужный формат
        read_only=True, 
        allow_null=True 
    )
    point_type_display = serializers.CharField(source='get_point_type_display', read_only=True)

    class Meta:
        model = Point
        geo_field = "location" # Указываем поле геометрии
        
        # Поля, которые будут включены в сериализацию.
        # Поле, указанное в `geo_field`, будет в `geometry`.
        # Остальные поля из этого списка попадут в `properties` GeoJSON.
        # `id` (первичный ключ модели) автоматически будет на верхнем уровне GeoJSON.
        fields = (
            'id',                 # Первичный ключ (бывшее имя, MARKER NAME)
            'station_name',       # Новое поле для присвоенного имени
            'description',
            'point_type',
            'timestamp',          # Оригинальный timestamp (может быть нужен клиенту)
            
            # Новые поля из файла RINEX
            'receiver_number',
            'antenna_height',

            # Связанные и вычисляемые поля для удобства (обычно read_only)
            'source_file',        # Будет сериализован как ID UploadedRinexFile
            'raw_x', 'raw_y', 'raw_z', # Если они нужны клиенту
            
            # Дополнительные поля, которые мы определили в сериализаторе
            'latitude', 
            'longitude',
            'timestamp_display',
            'point_type_display',

            'network_class', 
            'index_name', 
            'center_type', 
            'status', 
            'mark_number',
        )
        
        # Поля, которые клиент не может изменять через API (например, при PATCH/PUT)
        # ID (PK) и поля, заполняемые из RINEX файла или вычисляемые, обычно read_only.
        read_only_fields = (
            'id', 
            'raw_x', 'raw_y', 'raw_z',
            'receiver_number', 
            'antenna_height',
            'source_file', # Обычно не меняется через этот API
            'latitude', 
            'longitude',
            'timestamp_display', # Вычисляемое
            'point_type_display', # Вычисляемое
            'network_class', 'index_name', 'center_type', 'status', 'mark_number',
            # 'timestamp' тоже может быть read_only, если он устанавливается только из файла
        )
        # Если вы хотите разрешить редактирование 'timestamp' через API, уберите его из read_only_fields.

    # Валидаторы для полей, которые МОЖНО изменять через API (PUT/PATCH)
    # Например, 'station_name', 'description', 'point_type'
    
    def validate_station_name(self, value):
        # station_name может быть пустым (blank=True, null=True в модели)
        name_str = value.strip() if isinstance(value, str) else ""
        if len(name_str) > 255:
            raise serializers.ValidationError("Присвоенное имя точки слишком длинное (макс. 255 символов).")
        return name_str # Возвращаем очищенное значение или пустую строку

    def validate_description(self, value):
        # description может быть пустым (blank=True, null=True в модели)
        return value.strip() if isinstance(value, str) else ""

    def validate_point_type(self, value):
        # point_type обязателен и должен быть из списка POINT_TYPES
        if not value:
            raise serializers.ValidationError("Тип точки не может быть пустым.")
        valid_types = [pt[0] for pt in Point.POINT_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Недопустимый тип точки: '{value}'. Доступные типы: {', '.join(valid_types)}"
            )
        return value

    # Кастомный to_representation для GeoJSON, если стандартного поведения GeoFeatureModelSerializer недостаточно
    # Обычно GeoFeatureModelSerializer хорошо справляется с размещением полей.
    # Этот метод можно использовать для более тонкой настройки вывода.
    def to_representation(self, instance):
        # Получаем стандартное представление GeoJSON от родительского класса
        representation = super().to_representation(instance)

        # GeoFeatureModelSerializer уже должен поместить PK в `representation['id']`
        # и остальные поля из `Meta.fields` (кроме `geo_field`) в `representation['properties']`.
        # Нам нужно убедиться, что все кастомные и вычисляемые поля тоже там.

        # Убедимся, что `id` (наш строковый PK) есть и в `properties`
        if 'properties' not in representation:
            representation['properties'] = {}
        
        # Явно добавляем id в properties, если его там нет (хотя DRF-GIS обычно это делает)
        # или если мы хотим его там видеть под определенным ключом.
        if 'id' not in representation['properties'] and hasattr(instance, 'id'):
            representation['properties']['id'] = instance.id # Используем PK модели

        # Добавим остальные не-гео поля из Meta.fields в properties, если их там нет
        # Это больше для контроля, т.к. GeoFeatureModelSerializer должен это делать
        for field_name in self.Meta.fields:
            if field_name == self.Meta.geo_field or field_name == 'id': # id уже есть, geo_field в geometry
                continue
            
            # Если поле определено в сериализаторе (например, вычисляемое или с кастомным source)
            if field_name in self.fields:
                serializer_field = self.fields[field_name]
                # Получаем значение поля, используя его source, если он есть
                # или просто имя поля, если source не указан или '*'
                source = serializer_field.source if serializer_field.source and serializer_field.source != '*' else field_name
                if hasattr(instance, source):
                    representation['properties'][field_name] = serializer_field.to_representation(getattr(instance, source))
                elif callable(getattr(instance, source, None)): # для @property или методов
                    representation['properties'][field_name] = serializer_field.to_representation(getattr(instance, source)())

            # Если поле не определено в сериализаторе, но есть в Meta.fields и в инстансе
            elif field_name not in representation['properties'] and hasattr(instance, field_name):
                representation['properties'][field_name] = getattr(instance, field_name)


        # Гарантируем наличие вычисляемых полей, если они не были добавлены через Meta.fields
        if 'latitude' not in representation['properties'] and instance.location:
            representation['properties']['latitude'] = instance.latitude
        if 'longitude' not in representation['properties'] and instance.location:
            representation['properties']['longitude'] = instance.longitude
        if 'timestamp_display' not in representation['properties'] and instance.timestamp:
            representation['properties']['timestamp_display'] = instance.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        if 'point_type_display' not in representation['properties'] and hasattr(instance, 'get_point_type_display'):
            representation['properties']['point_type_display'] = instance.get_point_type_display()

        return representation


class StationDirectoryNameSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели StationDirectoryName (справочник имен станций).
    """
    class Meta:
        model = StationDirectoryName
        fields = ['id', 'name', 'created_at', 'updated_at'] # Поля для API
        read_only_fields = ['id', 'created_at', 'updated_at'] # ID и даты только для чтения через API

    def validate_name(self, value):
        name_stripped = value.strip()
        if not name_stripped:
            raise serializers.ValidationError("Имя станции в справочнике не может быть пустым.")
        if len(name_stripped) > 255:
            raise serializers.ValidationError("Имя станции в справочнике слишком длинное (макс. 255 символов).")
        
        # Проверка на уникальность без учета регистра (если БД делает это с учетом регистра)
        # Model unique=True уже должен это обрабатывать, но можно добавить кастомную проверку
        queryset = StationDirectoryName.objects.filter(name__iexact=name_stripped)
        if self.instance: # Если это обновление (PATCH/PUT), исключаем текущий экземпляр из проверки
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(f"Имя станции '{name_stripped}' уже существует в справочнике (без учета регистра).")
            
        return name_stripped # Возвращаем очищенное имя