from django.contrib.auth.models import User, Group
from rest_framework.test import APITestCase
from rest_framework import status
from .models import StationDirectoryName

#dsdsdsdsdsfdsfыфыф

class StationDirectoryNameAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uploader_group, _ = Group.objects.get_or_create(name='Uploader')
        cls.viewer_group, _ = Group.objects.get_or_create(name='Viewer')
        cls.uploader_user = User.objects.create_user(username='testuploader', password='password123')
        cls.uploader_user.groups.add(cls.uploader_group)
        cls.viewer_user = User.objects.create_user(username='testviewer', password='password123')
        cls.viewer_user.groups.add(cls.viewer_group)
        cls.no_group_user = User.objects.create_user(username='nogroupuser', password='password123')
        StationDirectoryName.objects.create(name="Alpha")
        StationDirectoryName.objects.create(name="Bravo")


    
    def test_list_unauthenticated(self):
        """
        Анонимный пользователь НЕ может получить список имен.
        Ожидаем ошибку 401 Unauthorized.
        """
        response = self.client.get('/api/station-names/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_unauthenticated(self):
        """
        Анонимный пользователь не может создать новое имя.
        Ожидаем ошибку 401 Unauthorized.
        """
        response = self.client.post('/api/station-names/', {'name': 'Charlie'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        

    def test_list_as_viewer(self):
        """
        'Viewer' МОЖЕТ получить список имен.
        Ожидаем успешный ответ 200 OK.
        """
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get('/api/station-names/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_create_as_viewer(self):
        """
        'Viewer' не может создать новое имя.
        Ожидаем ошибку 403 Forbidden (Доступ запрещен).
        """
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.post('/api/station-names/', {'name': 'Charlie'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(StationDirectoryName.objects.filter(name="Charlie").exists())
        

    def test_list_as_uploader(self):
        """
        Проверяем, что 'Uploader' может получить список имен.
        """
        self.client.force_authenticate(user=self.uploader_user)
        response = self.client.get('/api/station-names/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_create_as_uploader(self):
        """
        'Uploader' может создать новое имя.
        Ожидаем успешный ответ 201 Created.
        """
        self.client.force_authenticate(user=self.uploader_user)
        response = self.client.post('/api/station-names/', {'name': 'Charlie'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(StationDirectoryName.objects.filter(name="Charlie").exists())
        
    def test_delete_as_uploader(self):
        """
         'Uploader' может удалить существующее имя.
        """
        self.client.force_authenticate(user=self.uploader_user)
        bravo_entry = StationDirectoryName.objects.get(name="Bravo")

        response = self.client.delete(f'/api/station-names/{bravo_entry.pk}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(StationDirectoryName.objects.filter(name="Bravo").exists())