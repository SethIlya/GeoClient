# geoclient/serializers.py
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from .models import Point, StationDirectoryName

class PointSerializer(GeoFeatureModelSerializer):
    # Вычисляемые поля для удобства фронтенда
    latitude = serializers.FloatField(source='location.y', read_only=True, allow_null=True)
    longitude = serializers.FloatField(source='location.x', read_only=True, allow_null=True)
    timestamp_display = serializers.DateTimeField(
        source='timestamp',
        format="%Y-%m-%d %H:%M:%S", # Формат отображения времени
        read_only=True,
        allow_null=True
    )
    point_type_display = serializers.CharField(source='get_point_type_display', read_only=True)
    
    # ID теперь CharField и является первичным ключом
    # При создании новой точки через API (если бы это было разрешено), ID нужно было бы предоставлять.
    # Но мы создаем точки через парсер, а API используется для чтения/обновления/удаления.
    # Для обновления `id` будет в URL, а не в теле запроса.
    # Мы не даем изменять id через API.
    id = serializers.CharField(read_only=True)


    class Meta:
        model = Point
        geo_field = "location" # Поле геометрии для GeoJSON
        fields = (
            'id', 'station_name', 'description', 'point_type', 'point_type_display',
            'timestamp', 'timestamp_display', 'latitude', 'longitude',
            'raw_x', 'raw_y', 'raw_z', 'source_file_id',
            'receiver_number', 'antenna_height' # Новые поля
        )
        # Поля, которые можно только читать через API
        read_only_fields = (
            'id', 'timestamp_display', 'latitude', 'longitude',
            'point_type_display', 'raw_x', 'raw_y', 'raw_z', 'source_file_id',
            'receiver_number', 'antenna_height' # Новые поля из файла тоже только для чтения через API
        )
        # Если вы хотите разрешить редактирование receiver_number и antenna_height через API,
        # уберите их из read_only_fields и добавьте в fields без read_only=True.
        # Но т.к. они парсятся из файла, логичнее их не менять вручную.

    # Валидаторы для полей, которые можно изменять через API (PUT/PATCH)
    # ID теперь не name, а id. Валидировать его на пустоту не нужно, если он PK.
    # Но если бы он не был PK и мог быть изменен, валидатор был бы здесь.
    
    def validate_station_name(self, value):
        name_str = value.strip() if isinstance(value, str) else ""
        # Может быть пустым, если null=True, blank=True в модели
        # if not name_str:
        #     raise serializers.ValidationError("Имя станции не может быть пустым.")
        if len(name_str) > 255:
            raise serializers.ValidationError("Имя станции слишком длинное (макс. 255 символов).")
        return name_str

    def validate_description(self, value):
        return value.strip() if isinstance(value, str) else ""

    def validate_point_type(self, value):
        valid_types = [pt[0] for pt in Point.POINT_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Недопустимый тип точки: '{value}'. Доступные типы: {', '.join(valid_types)}"
            )
        return value
    
    # Кастомный to_representation для GeoJSON
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Убедимся, что все не-гео поля из Meta.fields находятся в 'properties'
        # GeoFeatureModelSerializer уже делает это, но мы можем добавить свои кастомные поля.
        
        if 'properties' not in representation or not isinstance(representation['properties'], dict):
            representation['properties'] = {}

        # Явное добавление полей в properties, если они не попали туда автоматически
        # или если нужно переопределить их представление
        
        # GeoFeatureModelSerializer автоматически помещает 'id' на верхний уровень.
        # Дублируем его в properties для удобства клиента, если нужно.
        if 'id' not in representation['properties'] and hasattr(instance, 'id'):
             representation['properties']['id'] = instance.id
        
        # Добавляем все остальные поля, которые могут быть не добавлены автоматически
        # или если мы хотим быть уверены в их наличии
        for field_name in self.Meta.fields:
            if field_name == self.Meta.geo_field or field_name == 'id': # id уже на верхнем уровне и в properties
                continue
            
            if field_name not in representation['properties']:
                # Используем поля сериализатора, если они определены (например, _display поля)
                if hasattr(self, 'fields') and field_name in self.fields and \
                   isinstance(self.fields[field_name], serializers.Field) and \
                   self.fields[field_name].source and self.fields[field_name].source != '*': # Проверяем, что есть source
                    try:
                        representation['properties'][field_name] = self.fields[field_name].get_attribute(instance)
                    except AttributeError: # Если get_attribute не сработало, пробуем getattr
                        if hasattr(instance, field_name):
                            representation['properties'][field_name] = getattr(instance, field_name)
                        elif hasattr(instance, self.fields[field_name].source): # Пробуем по source
                             representation['properties'][field_name] = getattr(instance, self.fields[field_name].source)

                elif hasattr(instance, field_name): # Если поле есть в модели
                    representation['properties'][field_name] = getattr(instance, field_name)
        
        # Убедимся, что вычисляемые поля (_display) присутствуют
        if 'point_type_display' not in representation['properties'] and hasattr(instance, 'get_point_type_display'):
            representation['properties']['point_type_display'] = instance.get_point_type_display()
        if 'timestamp_display' not in representation['properties'] and instance.timestamp:
             representation['properties']['timestamp_display'] = instance.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        if 'latitude' not in representation['properties'] and instance.location :
            representation['properties']['latitude'] = instance.location.y
        if 'longitude' not in representation['properties'] and instance.location:
            representation['properties']['longitude'] = instance.location.x


        # Гарантируем, что на верхнем уровне GeoJSON есть 'id', если его нет
        if 'id' not in representation and hasattr(instance, 'id'):
            representation['id'] = instance.id
            
        return representation
    

class StationDirectoryNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationDirectoryName
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at'] # ID и даты только для чтения

    def validate_name(self, value):
        # Приводим к одному регистру для проверки уникальности, если нужно,
        # но unique=True на уровне БД обычно учитывает регистр (зависит от collation БД).
        # Здесь просто базовая валидация.
        name_stripped = value.strip()
        if not name_stripped:
            raise serializers.ValidationError("Имя станции не может быть пустым.")
        if len(name_stripped) > 255:
            raise serializers.ValidationError("Имя станции слишком длинное (макс. 255 символов).")
        
        # Проверка на уникальность без учета регистра (если БД делает это с учетом регистра)
        # queryset = StationDirectoryName.objects.filter(name__iexact=name_stripped)
        # if self.instance: # Если это обновление, исключаем текущий экземпляр из проверки
        #     queryset = queryset.exclude(pk=self.instance.pk)
        # if queryset.exists():
        #     raise serializers.ValidationError(f"Имя станции '{name_stripped}' уже существует в справочнике (без учета регистра).")
            
        return name_stripped # Возвращаем очищенное имя