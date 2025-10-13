// Jenkinsfile for SimTemp System
// Uses infra_ext Jenkins pipeline infrastructure
// 
// This Jenkinsfile integrates with the n2Electrons-Infra pipeline configuration
// to build and test the simtemp kernel module according to simtemp/pipeline_config.yml
//
// Copyright (c) Jorge Rodriguez Moreno

// Simple Jenkins pipeline for simtemp system
pipeline {
    agent any
    
    // Repository configuration
    options {
        // Checkout configuration - explicit for validating GitHub connectivity
        checkoutToSubdirectory('simtemp-system')
    }
    
    // Add credentials and repository information
    environment {
        // Repository information
        REPO_URL = 'https://github.com/n2Electrons/simtemp-system.git'
        REPO_BRANCH = "${env.BRANCH_NAME ?: 'main'}"
        
        // GitHub credentials - set in Jenkins credentials manager
        GITHUB_CREDENTIALS = credentials('github-credentials')
        
        // Define configuration paths
        PIPELINE_CONFIG_PATH = 'simtemp/pipeline_config.yml'
        TEST_CONFIG_PATH = 'simtemp/tests/config/simtemp_tests.yml'
    }
    
    stages {
        // Explicit checkout to validate repository access
        stage('Repository Validation') {
            steps {
                echo "Validating repository access: ${REPO_URL}"
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "${REPO_BRANCH}"]],
                    doGenerateSubmoduleConfigurations: false,
                    extensions: [[$class: 'CleanBeforeCheckout']],
                    submoduleCfg: [],
                    userRemoteConfigs: [[
                        credentialsId: 'github-credentials',
                        url: "${REPO_URL}"
                    ]]
                ])
                echo "Repository validation successful"
            }
        }
    
        stage('Initialize') {
            steps {
                echo "Starting SimTemp system build pipeline"
                sh "echo Using config: ${PIPELINE_CONFIG_PATH}"
                sh "echo Using tests config: ${TEST_CONFIG_PATH}"
                sh "echo Repository branch: ${REPO_BRANCH}"
            }
        }
        
        stage('Build') {
            steps {
                dir('simtemp/kernel') {
                    sh 'make clean && make all'
                }
            }
        }
        
        stage('Test') {
            steps {
                dir('simtemp/tests') {
                    sh 'python3 -m pytest -v .'
                }
            }
        }
        
    }
    
    // Fallback in case something goes wrong with infrastructure execution
    post {
        always {
            script {
                // Basic cleanup regardless of infrastructure pipeline success
                sh 'sudo rmmod nxp_simtemp 2>/dev/null || true'
            }
        }
        
        success {
            echo "SimTemp system build and tests completed successfully"
        }
        
        failure {
            echo "SimTemp system build or tests failed - check logs for details"
        }
    }
}