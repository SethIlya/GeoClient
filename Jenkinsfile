// Jenkinsfile для Django проекта
pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                git branch: 'dev', 
                    url: 'https://github.com/SethIlya/GeoClient.git', 
                    credentialsId: 'github_token3'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh 'python -m venv venv' 
                sh '. venv/bin/activate && pip install -r requirements.txt' 
            }
        }
        stage('Test') {
            steps {
                sh '. venv/bin/activate && python manage.py test'
            }
        }

        stage('Deploy') {
            when {
                branch 'dev'
            }
            steps {

            }
        }
    }
}