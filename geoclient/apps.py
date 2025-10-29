# geoclient/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate

def setup_groups_and_permissions(sender, **kwargs):
    """
    Создает группы 'Uploader' и 'Viewer' и назначает им
    соответствующие права доступа к моделям.
    Запускается после миграций.
    """
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType
    from .models import GeodeticPoint, UploadedRinexFile, Observation, StationDirectoryName

    # --- Получаем все необходимые модели ---
    point_ct = ContentType.objects.get_for_model(GeodeticPoint)
    rinex_ct = ContentType.objects.get_for_model(UploadedRinexFile)
    obs_ct = ContentType.objects.get_for_model(Observation)
    name_dir_ct = ContentType.objects.get_for_model(StationDirectoryName)

    # --- Получаем все необходимые права ---
    permissions = {
        'view_point': Permission.objects.get(content_type=point_ct, codename='view_geodeticpoint'),
        'change_point': Permission.objects.get(content_type=point_ct, codename='change_geodeticpoint'),
        'delete_point': Permission.objects.get(content_type=point_ct, codename='delete_geodeticpoint'),
        
        'add_rinex': Permission.objects.get(content_type=rinex_ct, codename='add_uploadedrinexfile'),
        'view_rinex': Permission.objects.get(content_type=rinex_ct, codename='view_uploadedrinexfile'),
        
        'view_obs': Permission.objects.get(content_type=obs_ct, codename='view_observation'),

        'add_name': Permission.objects.get(content_type=name_dir_ct, codename='add_stationdirectoryname'),
        'change_name': Permission.objects.get(content_type=name_dir_ct, codename='change_stationdirectoryname'),
        'delete_name': Permission.objects.get(content_type=name_dir_ct, codename='delete_stationdirectoryname'),
        'view_name': Permission.objects.get(content_type=name_dir_ct, codename='view_stationdirectoryname'),
    }

    # --- Создание и настройка группы "Uploader" ---
    uploader_group, created = Group.objects.get_or_create(name='Uploader')
    if created:
        print("Создана группа 'Uploader'")
    
    uploader_perms = [
        permissions['view_point'], permissions['change_point'], permissions['delete_point'],
        permissions['add_rinex'], permissions['view_rinex'],
        permissions['view_obs'],
        permissions['add_name'], permissions['change_name'], permissions['delete_name'], permissions['view_name'],
    ]
    uploader_group.permissions.set(uploader_perms)
    
    # --- Создание и настройка группы "Viewer" ---
    viewer_group, created = Group.objects.get_or_create(name='Viewer')
    if created:
        print("Создана группа 'Viewer'")
        
    viewer_perms = [
        permissions['view_point'],
        permissions['view_rinex'],
        permissions['view_obs'],
        permissions['view_name'],
    ]
    viewer_group.permissions.set(viewer_perms)

    print("Проверка и настройка ролей завершена.")


class GeoclientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'geoclient'
    verbose_name = "ГеоКлиент"

    def ready(self):
        # Подключаем наш сигнал к `post_migrate`
        post_migrate.connect(setup_groups_and_permissions, sender=self)