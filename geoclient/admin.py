# geoclient/admin.py
from django.contrib.gis import admin # Важно использовать admin из gis
from .models import Point, UploadedRinexFile

@admin.register(Point)
class PointAdmin(admin.GISModelAdmin): # Используем GISModelAdmin
    list_display = ('name', 'timestamp', 'source_file_link', 'latitude', 'longitude')
    search_fields = ('name', 'description')
    list_filter = ('timestamp', 'source_file')
    # Поле location будет отображаться на карте OpenStreetMap в админке
    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 10,
            'default_lat': 55.75, # Примерные координаты центра
            'default_lon': 37.61,
        },
    }

    def source_file_link(self, obj):
        if obj.source_file:
            from django.urls import reverse
            from django.utils.html import format_html
            link = reverse("admin:geoclient_uploadedrinexfile_change", args=[obj.source_file.id])
            return format_html('<a href="{}">{}</a>', link, obj.source_file.file.name.split('/')[-1])
        return "-"
    source_file_link.short_description = 'Исходный файл'


@admin.register(UploadedRinexFile)
class UploadedRinexFileAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'uploaded_at', 'file_type', 'points_count')
    list_filter = ('uploaded_at', 'file_type')
    readonly_fields = ('uploaded_at',)

    def file_name(self, obj):
        return obj.file.name.split('/')[-1]
    file_name.short_description = 'Имя файла'

    def points_count(self, obj):
        return obj.points.count()
    points_count.short_description = 'Кол-во точек'