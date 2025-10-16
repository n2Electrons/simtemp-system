// Jenkins Pipeline Stage for QEMU i.MX6UL Testing
// This Groovy script can be included in the main Jenkinsfile

def runQemuTests() {
    stage('QEMU i.MX6UL Tests') {
        timeout(time: 10, unit: 'MINUTES') {
            try {
                echo "🚀 Starting QEMU tests for i.MX6UL kernel..."
                
                // Ensure kernel is built
                echo "📋 Checking kernel build artifacts..."
                sh '''
                    if [ ! -f "deployment/qemu/build/install/boot/zImage" ]; then
                        echo "❌ Kernel not found, building now..."
                        cd deployment/qemu/scripts
                        ./build-imx6ul-kernel.sh
                    else
                        echo "✅ Kernel found, proceeding with tests"
                    fi
                '''
                
                // Run QEMU tests
                echo "🔬 Executing QEMU tests..."
                sh '''
                    cd deployment/qemu/scripts
                    ./jenkins-qemu-test.sh
                '''
                
                // Archive test results
                echo "📦 Archiving test results..."
                archiveArtifacts artifacts: 'test-results/*', fingerprint: true, allowEmptyArchive: true
                
                // Publish JUnit results
                publishTestResults testResultsPattern: 'test-results/junit-results.xml'
                
                // Set build status
                echo "✅ QEMU tests completed successfully"
                
            } catch (Exception e) {
                echo "❌ QEMU tests failed: ${e.getMessage()}"
                
                // Still archive results for debugging
                archiveArtifacts artifacts: 'test-results/*', fingerprint: true, allowEmptyArchive: true
                
                // Mark as unstable rather than failed to continue pipeline
                currentBuild.result = 'UNSTABLE'
                
                throw e
            }
        }
    }
}

def publishQemuTestResults() {
    stage('Publish QEMU Results') {
        echo "📊 Publishing QEMU test results..."
        
        // Read test results
        def testResults = [:]
        if (fileExists('test-results/test-results.json')) {
            def jsonContent = readFile('test-results/test-results.json')
            testResults = readJSON text: jsonContent
        }
        
        // Create test summary
        def testSummary = """
        ## 🔬 QEMU i.MX6UL Test Results
        
        **Build:** ${env.BUILD_NUMBER}
        **Status:** ${testResults.status ?: 'Unknown'}
        **Test Suite:** ${testResults.test_suite ?: 'F-K1-TC-002'}
        **Message:** ${testResults.message ?: 'No message available'}
        **Machine:** ${testResults.qemu_machine ?: 'mcimx6ul-evk'}
        **Kernel:** ${testResults.kernel_version ?: 'linux-imx-lf-6.6.52-2.2.1'}
        
        ### 📁 Available Artifacts
        - JUnit XML results for test integration
        - QEMU execution logs
        - Detailed JSON test results
        - Test execution summary
        
        ### 🎯 Test Details
        This test verifies Device Tree overlay support in the compiled i.MX6UL kernel
        running in QEMU mcimx6ul-evk machine emulation.
        """
        
        // Add to global test results for PR comment
        if (binding.hasVariable('globalTestResults')) {
            globalTestResults['qemu-imx6ul'] = [
                status: testResults.status ?: 'Unknown',
                message: testResults.message ?: 'QEMU test executed',
                details: testSummary
            ]
        }
        
        echo "📋 QEMU test results published"
    }
}

// Helper function to check QEMU prerequisites
def checkQemuPrerequisites() {
    echo "🔍 Checking QEMU prerequisites..."
    
    sh '''
        echo "Checking QEMU ARM system emulator..."
        qemu-system-arm --version || (echo "❌ QEMU ARM not found" && exit 1)
        
        echo "Checking cross-compilation tools..."
        arm-linux-gnueabihf-gcc --version || (echo "❌ ARM GCC not found" && exit 1)
        
        echo "Checking build tools..."
        make --version > /dev/null || (echo "❌ Make not found" && exit 1)
        
        echo "✅ All prerequisites satisfied"
    '''
}

// Export functions for use in main Jenkinsfile
return [
    runQemuTests: this.&runQemuTests,
    publishQemuTestResults: this.&publishQemuTestResults,
    checkQemuPrerequisites: this.&checkQemuPrerequisites
]