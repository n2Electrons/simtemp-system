// Jenkins Pipeline Stage for QEMU Integration Tests
// This groovy script shows how to use the enhanced QEMU configuration
//
// Copyright (c) Jorge Rodriguez Moreno

def runQemuIntegrationTests() {
    stage('QEMU Integration Tests') {
        timeout(time: 15, unit: 'MINUTES') {
            try {
                echo "🚀 Starting QEMU Integration Tests..."
                
                // Load test configuration to identify QEMU test suites
                echo "📋 Loading test configuration..."
                def testConfig = readYaml file: 'simtemp/tests/config/simtemp_tests.yml'
                
                // Find QEMU test suites
                def qemuTestSuites = [:]
                testConfig.tests.each { suiteName, suiteConfig ->
                    if (suiteConfig.execution_environment?.type == 'qemu') {
                        qemuTestSuites[suiteName] = suiteConfig
                        echo "🔍 Found QEMU test suite: ${suiteName}"
                    }
                }
                
                if (qemuTestSuites.isEmpty()) {
                    echo "ℹ️  No QEMU test suites found, skipping QEMU tests"
                    return
                }
                
                // Execute each QEMU test suite
                qemuTestSuites.each { suiteName, suiteConfig ->
                    echo "🖥️  Executing QEMU test suite: ${suiteName}"
                    echo "📝 Description: ${suiteConfig.description}"
                    
                    // Get execution configuration
                    def executionEnv = suiteConfig.execution_environment
                    def qemuConfig = suiteConfig.qemu_config
                    def resultsConfig = suiteConfig.results_collection
                    
                    echo "⚙️  QEMU Platform: ${executionEnv.platform}"
                    echo "🏗️  Machine Type: ${executionEnv.machine}"
                    echo "💾 Memory: ${executionEnv.memory}"
                    echo "⏱️  Timeout: ${executionEnv.timeout_minutes} minutes"
                    
                    // Prepare results directory
                    def resultsDir = resultsConfig.results_base_path ?: 'simtemp/tests/results'
                    sh "mkdir -p ${resultsDir}"
                    
                    // Execute QEMU test using the configured runner script
                    def runnerScript = qemuConfig.runner_script
                    echo "🏃 Running QEMU test with script: ${runnerScript}"
                    
                    def qemuExitCode = 0
                    try {
                        timeout(time: executionEnv.timeout_minutes, unit: 'MINUTES') {
                            // Use the Jenkins QEMU integration script
                            sh """
                                echo "🚀 Starting QEMU execution for suite: ${suiteName}"
                                cd ${WORKSPACE}
                                
                                # Execute using the Jenkins QEMU integration handler
                                python3 simtemp/tests/jenkins_qemu_integration.py execute ${suiteName}
                                QEMU_EXIT_CODE=\$?
                                
                                echo "📊 QEMU execution completed with exit code: \$QEMU_EXIT_CODE"
                                exit \$QEMU_EXIT_CODE
                            """
                        }
                        echo "✅ QEMU test suite '${suiteName}' completed successfully"
                        
                    } catch (Exception e) {
                        echo "❌ QEMU test suite '${suiteName}' failed: ${e.getMessage()}"
                        qemuExitCode = 1
                        
                        // Don't fail the entire pipeline, mark as unstable
                        currentBuild.result = 'UNSTABLE'
                    }
                    
                    // Collect and publish results regardless of test outcome
                    echo "📊 Collecting test results for suite: ${suiteName}"
                    
                    // Collect results using the integration handler
                    sh """
                        cd ${WORKSPACE}
                        python3 simtemp/tests/jenkins_qemu_integration.py collect ${suiteName} > ${resultsDir}/collection-report-${suiteName}.json
                    """
                    
                    // Publish JUnit XML results for Jenkins
                    def junitPattern = resultsConfig.patterns?.junit_xml ?: '*-qemu-results.xml'
                    def junitPath = "${resultsDir}/${junitPattern}"
                    
                    if (fileExists("${resultsDir}") && 
                        sh(script: "ls ${junitPath} 2>/dev/null | wc -l", returnStdout: true).trim() != "0") {
                        
                        echo "📋 Publishing JUnit results: ${junitPath}"
                        publishTestResults(
                            testResultsPattern: junitPath,
                            allowEmptyResults: true,
                            keepLongStdio: true
                        )
                    } else {
                        echo "⚠️  No JUnit XML results found for pattern: ${junitPath}"
                    }
                    
                    // Archive JSON reports and console logs
                    def jsonPattern = resultsConfig.patterns?.json_report ?: '*-qemu-report.json'
                    def consolePattern = resultsConfig.patterns?.console_log ?: '*-qemu-console.log'
                    def artifactsPattern = resultsConfig.patterns?.artifacts ?: 'test-results/*'
                    
                    echo "📦 Archiving artifacts..."
                    archiveArtifacts(
                        artifacts: "${resultsDir}/${jsonPattern},${resultsDir}/${consolePattern},${artifactsPattern},${resultsDir}/collection-report-*.json",
                        fingerprint: true,
                        allowEmptyArchive: true
                    )
                    
                    // Generate Jenkins artifacts info for downstream processing
                    sh """
                        cd ${WORKSPACE}
                        python3 simtemp/tests/jenkins_qemu_integration.py jenkins_info ${suiteName} > ${resultsDir}/jenkins-artifacts-${suiteName}.json
                    """
                    
                    echo "✅ Results collection completed for suite: ${suiteName}"
                }
                
                echo "🎯 All QEMU Integration Tests completed"
                
            } catch (Exception e) {
                echo "❌ QEMU Integration Tests failed: ${e.getMessage()}"
                
                // Still try to archive any available results
                archiveArtifacts(
                    artifacts: 'simtemp/tests/results/*',
                    fingerprint: true,
                    allowEmptyArchive: true
                )
                
                // Mark as unstable rather than failed to continue pipeline
                currentBuild.result = 'UNSTABLE'
                throw e
            }
        }
    }
}

def setupQemuTestEnvironment() {
    stage('Setup QEMU Test Environment') {
        echo "🛠️  Setting up QEMU test environment..."
        
        // Check QEMU installation
        sh '''
            echo "🔍 Checking QEMU installation..."
            qemu-system-arm --version || {
                echo "❌ QEMU ARM not found. Installing..."
                sudo apt-get update
                sudo apt-get install -y qemu-system-arm qemu-utils
            }
            echo "✅ QEMU ARM available"
        '''
        
        // Verify required QEMU components
        sh '''
            echo "🔍 Verifying QEMU components..."
            
            # Check for kernel images
            if [ ! -f "deployment/qemu/images/system/kernel-arm.img" ]; then
                echo "⚠️  ARM kernel image not found, may need to build"
            else
                echo "✅ ARM kernel image found"
            fi
            
            # Check for device tree blobs
            if [ ! -f "deployment/qemu/dtb/imx6ul-simtemp.dtb" ]; then
                echo "⚠️  Device tree blob not found, may need to build"
            else
                echo "✅ Device tree blob found"
            fi
            
            # Check for initrd
            if [ ! -f "deployment/qemu/images/system/initrd.img" ]; then
                echo "⚠️  InitRD image not found, may need to build"
            else
                echo "✅ InitRD image found"
            fi
        '''
        
        // Setup Python dependencies for QEMU integration
        sh '''
            echo "🐍 Setting up Python dependencies..."
            pip3 install --user pyyaml || echo "PyYAML may already be installed"
            echo "✅ Python dependencies ready"
        '''
        
        echo "✅ QEMU test environment setup completed"
    }
}

// Example of how to integrate into main pipeline
def integrateQemuTestsInPipeline() {
    pipeline {
        agent any
        
        stages {
            stage('Checkout') {
                steps {
                    checkout scm
                }
            }
            
            stage('Build') {
                steps {
                    // Build kernel module and other components
                    echo "Building kernel module..."
                    sh 'make -C simtemp/kernel clean all'
                }
            }
            
            stage('Setup QEMU Environment') {
                steps {
                    script {
                        setupQemuTestEnvironment()
                    }
                }
            }
            
            stage('QEMU Integration Tests') {
                steps {
                    script {
                        runQemuIntegrationTests()
                    }
                }
            }
            
            stage('Generate Test Reports') {
                steps {
                    echo "📊 Generating comprehensive test reports..."
                    sh '''
                        cd simtemp/tests
                        python3 create_test_report.py --include-qemu-results
                    '''
                    
                    // Archive final reports
                    archiveArtifacts(
                        artifacts: 'simtemp/tests/reports/*',
                        fingerprint: true,
                        allowEmptyArchive: true
                    )
                }
            }
        }
        
        post {
            always {
                // Ensure QEMU processes are cleaned up
                sh '''
                    echo "🧹 Cleaning up QEMU processes..."
                    pkill -f qemu-system-arm || echo "No QEMU processes to kill"
                    
                    echo "📊 Final results summary:"
                    find simtemp/tests/results -name "*.xml" -o -name "*.json" | head -10
                '''
            }
            success {
                echo "🎉 Pipeline completed successfully with QEMU tests"
            }
            unstable {
                echo "⚠️  Pipeline completed with some QEMU test failures"
            }
            failure {
                echo "❌ Pipeline failed"
            }
        }
    }
}

// Return the main functions for use in other pipeline scripts
return [
    runQemuIntegrationTests: this.&runQemuIntegrationTests,
    setupQemuTestEnvironment: this.&setupQemuTestEnvironment,
    integrateQemuTestsInPipeline: this.&integrateQemuTestsInPipeline
]