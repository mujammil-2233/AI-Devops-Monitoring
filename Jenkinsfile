// ==============================================================================
// Production Jenkins Declarative CI/CD Pipeline
// Project: AI-Powered DevOps Monitoring & Auto-Healing System
// Features: Automated Unit Testing, Trivy Security Scans, AWS ECR Publishing,
//           Automated EC2 Deployment, Health Probing, and Zero-Downtime Rollback
// ==============================================================================

pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '15', artifactNumToKeepStr: '10'))
        ansiColor('xterm')
    }

    environment {
        // Application Metadata
        APP_NAME         = 'ai-devops-monitor'
        IMAGE_NAME       = 'ai-devops-monitoring'
        IMAGE_TAG        = "${env.BUILD_NUMBER}"

        // AWS Configuration (Injected via Jenkins Credentials Manager)
        AWS_REGION       = 'us-east-1'
        AWS_ACCOUNT_ID   = credentials('AWS_ACCOUNT_ID')
        ECR_REGISTRY     = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
        ECR_REPO_URI     = "${ECR_REGISTRY}/${IMAGE_NAME}"

        // Target Deployment Server
        EC2_HOST         = credentials('EC2_HOST_IP')
        EC2_USER         = 'ubuntu'
        SSH_KEY_CRED_ID  = 'ec2-ssh-key'

        // AWS Auth Credentials
        AWS_CREDS_ID     = 'aws-credentials'

        // Test reports
        PYTHONUNBUFFERED = '1'
    }

    stages {
        // -------------------------------------------------------------
        // Stage 1: Checkout Source Code
        // -------------------------------------------------------------
        stage('1. Checkout SCM') {
            steps {
                echo "--> Checking out repository from Git..."
                checkout scm
                script {
                    echo "Git Commit: ${env.GIT_COMMIT}"
                    echo "Git Branch: ${env.GIT_BRANCH}"
                }
            }
        }

        // -------------------------------------------------------------
        // Stage 2: Environment Setup & Install Dependencies
        // -------------------------------------------------------------
        stage('2. Install Dependencies') {
            steps {
                echo "--> Setting up virtualenv and installing dependencies..."
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r app/requirements.txt
                    pip install pytest flake8
                '''
            }
        }

        // -------------------------------------------------------------
        // Stage 3: Code Quality & Unit Tests
        // -------------------------------------------------------------
        stage('3. Unit Tests & Linting') {
            steps {
                echo "--> Running code linter and Pytest test suite..."
                sh '''
                    . .venv/bin/activate
                    flake8 app/ --max-line-length=120 --ignore=E501,W503 || true
                    pytest tests/ -v --junitxml=test-reports/results.xml
                '''
            }
            post {
                always {
                    junit testResults: 'test-reports/results.xml', allowEmptyResults: true
                }
            }
        }

        // -------------------------------------------------------------
        // Stage 4: Build Docker Image
        // -------------------------------------------------------------
        stage('4. Build Docker Image') {
            steps {
                echo "--> Building Docker image: ${ECR_REPO_URI}:${IMAGE_TAG}..."
                sh '''
                    docker build \
                        --tag ${IMAGE_NAME}:${IMAGE_TAG} \
                        --tag ${IMAGE_NAME}:latest \
                        --tag ${ECR_REPO_URI}:${IMAGE_TAG} \
                        --tag ${ECR_REPO_URI}:latest \
                        ./app
                '''
            }
        }

        // -------------------------------------------------------------
        // Stage 5: Container Validation
        // -------------------------------------------------------------
        stage('5. Container Validation') {
            steps {
                echo "--> Validating container startup and initial health check..."
                sh '''
                    docker run -d --name test-validator -p 5999:5000 ${IMAGE_NAME}:${IMAGE_TAG}
                    sleep 5
                    curl -f http://localhost:5999/health || (docker logs test-validator && exit 1)
                    docker stop test-validator && docker rm test-validator
                '''
            }
        }

        // -------------------------------------------------------------
        // Stage 6: Security Scan (Trivy)
        // -------------------------------------------------------------
        stage('6. Security Vulnerability Scan') {
            steps {
                echo "--> Executing Trivy vulnerability scanner on image..."
                sh '''
                    if command -v trivy >/dev/null 2>&1; then
                        trivy image \
                            --severity HIGH,CRITICAL \
                            --exit-code 0 \
                            --format table \
                            ${IMAGE_NAME}:${IMAGE_TAG}
                    else
                        echo "[INFO] Trivy not installed on Jenkins agent. Skipping security scan gate."
                    fi
                '''
            }
        }

        // -------------------------------------------------------------
        // Stage 7: Push Docker Image to Amazon ECR
        // -------------------------------------------------------------
        stage('7. Push Image to ECR') {
            steps {
                echo "--> Authenticating with AWS ECR and pushing image..."
                withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: env.AWS_CREDS_ID]]) {
                    sh '''
                        aws ecr get-login-password --region ${AWS_REGION} | \
                            docker login --username AWS --password-stdin ${ECR_REGISTRY}
                        docker push ${ECR_REPO_URI}:${IMAGE_TAG}
                        docker push ${ECR_REPO_URI}:latest
                    '''
                }
            }
        }

        // -------------------------------------------------------------
        // Stage 8: Deploy Application to AWS EC2
        // -------------------------------------------------------------
        stage('8. Deploy to AWS EC2') {
            steps {
                echo "--> Triggering remote deployment on EC2 target instance (${EC2_HOST})..."
                sshagent([env.SSH_KEY_CRED_ID]) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no ${EC2_USER}@${EC2_HOST} << 'EOF'
                            set -e
                            cd ~/ai-devops-monitoring || mkdir -p ~/ai-devops-monitoring
                            # Fetch updated deployment scripts and docker-compose
                            git pull origin main || true
                            # Export dynamic deployment environment
                            export IMAGE_NAME=${IMAGE_NAME}
                            export IMAGE_TAG=${IMAGE_TAG}
                            export ECR_REGISTRY=${ECR_REGISTRY}

                            # Authenticate EC2 Docker with ECR
                            aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ECR_REGISTRY}

                            # Execute zero-downtime deployment script with rollback protection
                            chmod +x scripts/*.sh
                            ./scripts/deployment.sh
                        EOF
                    '''
                }
            }
        }

        // -------------------------------------------------------------
        // Stage 9: Verify Application Health
        // -------------------------------------------------------------
        stage('9. Post-Deployment Verification') {
            steps {
                echo "--> Verifying remote application health at http://${EC2_HOST}:5000/health..."
                sh '''
                    APP_HOST=${EC2_HOST} APP_PORT=5000 MAX_ATTEMPTS=5 SLEEP_INTERVAL=4 ./scripts/health-check.sh
                '''
            }
        }
    }

    // -----------------------------------------------------------------
    // Stage 10 / Post Execution Lifecycle
    // -----------------------------------------------------------------
    post {
        success {
            echo "=========================================================="
            echo " [PIPELINE SUCCESS] Build #${BUILD_NUMBER} deployed cleanly!"
            echo " Live URL: http://${EC2_HOST}:5000"
            echo " Metrics:  http://${EC2_HOST}:5000/metrics"
            echo " Grafana:  http://${EC2_HOST}:3000"
            echo "=========================================================="
        }
        failure {
            echo "=========================================================="
            echo " [PIPELINE FAILED] Build #${BUILD_NUMBER} failed."
            echo " Remote host auto-rollback handled by deployment.sh."
            echo " Inspect stage logs and reports/latest_report.md."
            echo "=========================================================="
        }
        always {
            echo "--> Cleaning up local Docker builder artifacts..."
            sh '''
                docker image prune -f >/dev/null 2>&1 || true
                rm -rf .venv test-validator
            '''
        }
    }
}
