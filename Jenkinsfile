// Jenkinsfile for SimTemp System
// Uses infra_ext Jenkins pipeline infrastructure
// 
// This Jenkinsfile integrates with the n2Electrons-Infra pipeline configuration
// to build and test the simtemp kernel module according to simtemp/pipeline_config.yml
//
// Copyright (c) Jorge Rodriguez Moreno

// Jenkins pipeline for simtemp system with GitHub integration
pipeline {
    // Use specific agent with Git capabilities
    agent {
        // Can be replaced with a more specific agent configuration if needed
        docker {
            image 'n2electrons/kernel-build:latest'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    
    // Configure build triggers (when using GitHub webhooks)
    triggers {
        // Trigger build on GitHub push
        githubPush()
    }
    
    // Repository configuration
    options {
        // Checkout configuration - explicit for validating GitHub connectivity
        checkoutToSubdirectory('simtemp-system')
        // Discard old builds
        buildDiscarder(logRotator(numToKeepStr: '10'))
        // Enable timestamps in logs
        timestamps()
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
                
                // Verify GitHub credentials
                withCredentials([usernamePassword(credentialsId: 'github-credentials', 
                                                usernameVariable: 'GITHUB_USER', 
                                                passwordVariable: 'GITHUB_TOKEN')]) {
                    sh 'echo "GitHub credentials available for user: $GITHUB_USER"'
                }
                
                // Perform explicit checkout to validate repo connection
                checkout([
                    $class: 'GitSCM',
                    branches: [[name: "${REPO_BRANCH}"]],
                    doGenerateSubmoduleConfigurations: false,
                    extensions: [
                        [$class: 'CleanBeforeCheckout'],
                        [$class: 'CheckoutOption', timeout: 30],
                        [$class: 'CloneOption', depth: 0, noTags: false, reference: '', shallow: false, timeout: 30]
                    ],
                    submoduleCfg: [],
                    userRemoteConfigs: [[
                        credentialsId: 'github-credentials',
                        url: "${REPO_URL}"
                    ]]
                ])
                
                // Get repository information
                script {
                    // Get the current commit info
                    env.GIT_COMMIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.GIT_COMMITTER_NAME = sh(script: 'git log -1 --pretty=format:%cn', returnStdout: true).trim()
                    env.GIT_COMMITTER_EMAIL = sh(script: 'git log -1 --pretty=format:%ce', returnStdout: true).trim()
                    
                    // Display repository info
                    echo "Repository validation successful"
                    echo "Branch: ${REPO_BRANCH}"
                    echo "Commit: ${env.GIT_COMMIT_SHORT}"
                    echo "Committer: ${env.GIT_COMMITTER_NAME} <${env.GIT_COMMITTER_EMAIL}>"
                }
            }
        }
    
        stage('Initialize') {
            steps {
                echo "Starting SimTemp system build pipeline"
                sh "echo Using config: ${PIPELINE_CONFIG_PATH}"
                sh "echo Using tests config: ${TEST_CONFIG_PATH}"
                sh "echo Repository branch: ${REPO_BRANCH}"
                
                // Update GitHub commit status
                githubNotify context: 'Jenkins/Build', 
                             description: 'Pipeline initialized', 
                             status: 'PENDING'
            }
        }
        
        stage('Build') {
            steps {
                // Update GitHub commit status
                githubNotify context: 'Jenkins/Build', 
                             description: 'Building kernel module', 
                             status: 'PENDING'
                             
                // Build the kernel module
                dir('simtemp/kernel') {
                    sh 'make clean && make all'
                }
                
                // Archive build artifacts
                archiveArtifacts artifacts: 'simtemp/kernel/*.ko', 
                                 allowEmptyArchive: true, 
                                 fingerprint: true
                                 
                // Update GitHub status
                githubNotify context: 'Jenkins/Build', 
                             description: 'Build completed successfully', 
                             status: 'SUCCESS'
            }
            
            post {
                failure {
                    githubNotify context: 'Jenkins/Build', 
                                 description: 'Build failed', 
                                 status: 'FAILURE'
                }
            }
        }
        
        stage('Test') {
            steps {
                // Update GitHub commit status
                githubNotify context: 'Jenkins/Test', 
                             description: 'Running tests', 
                             status: 'PENDING'
                             
                // Run the tests
                dir('simtemp/tests') {
                    sh 'python3 -m pytest -v . --junitxml=test-results.xml'
                }
                
                // Publish test results
                junit 'simtemp/tests/test-results.xml'
                
                // Update GitHub status
                githubNotify context: 'Jenkins/Test', 
                             description: 'Tests passed', 
                             status: 'SUCCESS'
            }
            
            post {
                failure {
                    githubNotify context: 'Jenkins/Test', 
                                 description: 'Tests failed', 
                                 status: 'FAILURE'
                }
            }
        }
        
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                echo 'Deploying only on main branch'
                // Add your deployment steps here
            }
        }
        
    }
    
    // Post-build actions and notifications
    post {
        always {
            // Clean workspace and unload kernel module
            script {
                // Basic cleanup regardless of infrastructure pipeline success
                sh 'sudo rmmod nxp_simtemp 2>/dev/null || true'
                
                // Clean workspace if needed
                cleanWs(cleanWhenNotBuilt: false,
                        deleteDirs: true,
                        disableDeferredWipeout: true,
                        notFailBuild: true)
            }
        }
        
        success {
            // Update GitHub status to success
            githubNotify context: 'Jenkins/Pipeline', 
                         description: 'Build succeeded', 
                         status: 'SUCCESS'
                         
            echo "SimTemp system build and tests completed successfully"
            
            // Optional: send success notification
            // emailext (
            //     subject: "Build Successful: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            //     body: "Build completed successfully: ${env.BUILD_URL}",
            //     recipientProviders: [developers(), requestor()]
            // )
        }
        
        failure {
            // Update GitHub status to failure
            githubNotify context: 'Jenkins/Pipeline', 
                         description: 'Build failed', 
                         status: 'FAILURE'
                         
            echo "SimTemp system build or tests failed - check logs for details"
            
            // Optional: send failure notification
            // emailext (
            //     subject: "Build Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            //     body: "Build failed: ${env.BUILD_URL}",
            //     recipientProviders: [developers(), culprits()]
            // )
        }
        
        unstable {
            // Update GitHub status to unstable
            githubNotify context: 'Jenkins/Pipeline', 
                         description: 'Build unstable', 
                         status: 'FAILURE'
                         
            echo "SimTemp system build is unstable - check warnings in logs"
        }
    }
}