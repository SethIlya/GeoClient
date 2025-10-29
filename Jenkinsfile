// Jenkinsfile для Django проекта
pipeline {
    // 1. Запускать на любой доступной 
    agent any

    // 2. Этапы работы
    stages {
        // Этап 1: Скачивание кода из GitHub
        stage('Checkout') {
            steps {
                git branch: 'dev', 
                    url: 'https://github.com/SethIlya/GeoClient.git', 
                    credentialsId: 'github_token3'
            }
        }

        // Этап 2: Установка зависимостей Python
        stage('Install Dependencies') {
            steps {
                sh 'python -m venv venv' // Создаем виртуальное окружение
                sh '. venv/bin/activate && pip install -r requirements.txt' // Активируем его и ставим зависимости
            }
        }

        // ЭТАП 3: ЗАПУСК UNIT-ТЕСТОВ 
        stage('Test') {
            steps {
                sh '. venv/bin/activate && python manage.py test'
            }
        }
        
        // Этап 4: Деплой (доставка)
        stage('Deploy') {
            when {
                // Условие: выполнять только для ветки 'dev' (или замени на 'main')
                branch 'dev'
            }
            steps {

            }
        }
    }
}