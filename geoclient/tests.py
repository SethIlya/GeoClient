from django.contrib.auth.models import User, Group
from rest_framework.test import APITestCase
from rest_framework import status
from .models import StationDirectoryName

class StationDirectoryNameAPITests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        # --- ВОТ ПРАВИЛЬНЫЙ ВАРИАНТ ---
        cls.uploader_group, _ = Group.objects.get_or_create(name='Uploader')
        cls.viewer_group, _ = Group.objects.get_or_create(name='Viewer')
        
        # --- Дальше все остается как было, и теперь это сработает! ---
        
        # Создаем пользователей
        cls.uploader_user = User.objects.create_user(username='testuploader', password='password123')
        # Теперь cls.uploader_group - это чистый объект группы, а не кортеж
        cls.uploader_user.groups.add(cls.uploader_group)
        
        cls.viewer_user = User.objects.create_user(username='testviewer', password='password123')
        cls.viewer_user.groups.add(cls.viewer_group)
        
        cls.no_group_user = User.objects.create_user(username='nogroupuser', password='password123')

        # Создаем тестовые данные
        StationDirectoryName.objects.create(name="Alpha")
        StationDirectoryName.objects.create(name="Bravo")

    # --- Тесты для НЕАУТЕНТИФИЦИРОВАННОГО (анонимного) пользователя ---
    
    def test_list_unauthenticated(self):
        """
        Проверяем, что анонимный пользователь НЕ может получить список имен.
        Ожидаем ошибку 401 Unauthorized.
        """
        # self.client - это виртуальный "браузер" или "Postman" для тестов
        response = self.client.get('/api/station-names/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_unauthenticated(self):
        """
        Проверяем, что анонимный пользователь НЕ может создать новое имя.
        Ожидаем ошибку 401 Unauthorized.
        """
        response = self.client.post('/api/station-names/', {'name': 'Charlie'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    # --- Тесты для пользователя с ролью 'Viewer' (только просмотр) ---

    def test_list_as_viewer(self):
        """
        Проверяем, что 'Viewer' МОЖЕТ получить список имен.
        Ожидаем успешный ответ 200 OK.
        """
        # "Логиним" нашего пользователя-просмотрщика в тестовом клиенте
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get('/api/station-names/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Проверяем, что в ответе пришло ровно 2 записи, которые мы создали в setUpTestData
        self.assertEqual(len(response.data['results']), 2)

    def test_create_as_viewer(self):
        """
        Проверяем, что 'Viewer' НЕ может создать новое имя.
        Ожидаем ошибку 403 Forbidden (Доступ запрещен).
        """
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.post('/api/station-names/', {'name': 'Charlie'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Убедимся, что запись НЕ была создана в базе данных
        self.assertFalse(StationDirectoryName.objects.filter(name="Charlie").exists())
        
    # --- Тесты для пользователя с ролью 'Uploader' (полные права) ---

    def test_list_as_uploader(self):
        """
        Проверяем, что 'Uploader' МОЖЕТ получить список имен.
        """
        self.client.force_authenticate(user=self.uploader_user)
        response = self.client.get('/api/station-names/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_create_as_uploader(self):
        """
        Проверяем, что 'Uploader' МОЖЕТ создать новое имя.
        Ожидаем успешный ответ 201 Created.
        """
        self.client.force_authenticate(user=self.uploader_user)
        response = self.client.post('/api/station-names/', {'name': 'Charlie'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Убедимся, что запись ДЕЙСТВИТЕЛЬНО была создана в базе данных
        self.assertTrue(StationDirectoryName.objects.filter(name="Charlie").exists())
        
    def test_delete_as_uploader(self):
        """
        Проверяем, что 'Uploader' МОЖЕТ удалить существующее имя.
        """
        self.client.force_authenticate(user=self.uploader_user)
        # Получаем ID одной из существующих записей
        bravo_entry = StationDirectoryName.objects.get(name="Bravo")
        
        # Отправляем DELETE запрос на URL этой записи
        response = self.client.delete(f'/api/station-names/{bravo_entry.pk}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Убедимся, что запись исчезла из базы
        self.assertFalse(StationDirectoryName.objects.filter(name="Bravo").exists())