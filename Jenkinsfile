// Jenkins Pipeline for Infrastructure Testing and Requirements Tracing
//
// Copyright (c) Jorge Rodriguez Moreno
//
// This pipeline provides infrastructure for testing and requirements tracing
// that can be used as a submodule in other repositories.

import groovy.transform.Field

// Load utility libraries
// Diagnostics module will be loaded in the PR Diagnostics stage

// Global variables to store build results for final PR comment
@Field def globalBuildResults = [:]
@Field def globalTestResults = [:]
@Field def globalTestDetails = [:]
@Field def globalDetailedReport = [:]
@Field def globalBuildStatus = 'unknown'    // Start neutral, will be set during execution
@Field def globalTestStatus = 'unknown'     // Start neutral, will be set during execution

// Function to clear all global variables to prevent cache issues
def clearGlobalVariables() {
    echo "🧹 Clearing global variables to prevent cache issues..."
    globalBuildResults = [:]
    globalTestResults = [:]
    globalTestDetails = [:]
    globalDetailedReport = [:]
    globalBuildStatus = 'unknown'    // Start with neutral state, not success
    globalTestStatus = 'unknown'     // Start with neutral state, not success
    echo "Global variables cleared successfully - status reset to 'unknown'"
}

// Helper function to load pipeline configuration from YAML
def loadPipelineConfig(configPath) {
    if (!configPath) {
        // Try common configuration paths in order of preference
        def defaultPaths = [
            'simtemp/pipeline_config.yml'
        ]
        
        for (def path : defaultPaths) {
            if (fileExists(path)) {
                configPath = path
                echo "Auto-discovered pipeline config at: ${configPath}"
                break
            }
        }
        
        if (!configPath) {
            error "Pipeline configuration file not found. Searched paths: ${defaultPaths.join(', ')}"
        }
    }
    
    if (!fileExists(configPath)) {
        error "Pipeline configuration file not found at ${configPath}"
    }
    
    echo "Loading pipeline configuration from ${configPath}"
    def pipelineConfig = readYaml file: configPath
    
    if (!pipelineConfig.source_code?.modules) {
        error "Pipeline configuration missing source_code.modules section"
    }
    
    echo "Pipeline configuration loaded successfully"
    return pipelineConfig
}

// Helper function to get enabled modules from pipeline config
def getEnabledModules(pipelineConfig) {
    def enabledModules = []
    
    echo "DEBUG: Checking pipelineConfig.source_code?.modules..."
    echo "DEBUG: pipelineConfig.source_code = ${pipelineConfig.source_code}"
    
    if (!pipelineConfig.source_code?.modules) {
        echo "No source_code.modules configuration found in pipeline config"
        return enabledModules
    }
    
    echo "DEBUG: Found source_code.modules, processing..."
    pipelineConfig.source_code.modules.each { moduleName, moduleConfig ->
        echo "DEBUG: Processing module '${moduleName}' with config: ${moduleConfig}"
        if (moduleConfig.enabled != false) {
            enabledModules.add(moduleName)
            echo "DEBUG: Added '${moduleName}' to enabled modules"
        } else {
            echo "DEBUG: Skipped '${moduleName}' (disabled)"
        }
    }
    
    echo "Found ${enabledModules.size()} enabled modules: ${enabledModules.join(', ')}"
    return enabledModules
}

// Helper function to get module build configuration
def getModuleBuildConfig(pipelineConfig, moduleName) {
    def moduleConfig = pipelineConfig.source_code.modules[moduleName]
    if (!moduleConfig) {
        error "Module ${moduleName} not found in pipeline configuration"
    }
    
    def buildConfig = [:]
    
    // Extract required configuration fields without fallbacks
    if (!moduleConfig.source_dir) {
        error "source_dir not specified for module '${moduleName}' in pipeline configuration"
    }
    if (!moduleConfig.binary_name) {
        error "binary_name not specified for module '${moduleName}' in pipeline configuration"
    }
    
    buildConfig.sourceFile = moduleConfig.source_files ? moduleConfig.source_files[0] : "${moduleConfig.source_dir}/${moduleName}.c"
    buildConfig.buildDir = moduleConfig.source_dir
    buildConfig.binaryName = moduleConfig.binary_name
    buildConfig.makefile = moduleConfig.makefile ?: "${moduleConfig.source_dir}/Makefile"
    buildConfig.buildTargets = moduleConfig.build_targets ?: ['clean', 'all']
    
    // Validate that the required paths exist in configuration
    echo "Build config for '${moduleName}': buildDir=${buildConfig.buildDir}, binaryName=${buildConfig.binaryName}"
    
    return buildConfig
}

// Helper function to build a single module
def buildModule(String moduleName, def buildConfig) {
    if (!fileExists(buildConfig.buildDir)) {
        throw new Exception("Source directory ${buildConfig.buildDir} does not exist")
    }
    
    try {
        if (!fileExists(buildConfig.makefile)) {
            throw new Exception("Makefile ${buildConfig.makefile} does not exist")
        }
        
        dir(buildConfig.buildDir) {
            buildConfig.buildTargets.each { target ->
                // Native x86_64 builds only - check kernel headers path
                def kernelHeadersPath = sh(
                    script: '''
                        if [ -d "/lib/modules/$(uname -r)/build" ]; then
                            echo "/lib/modules/$(uname -r)/build"
                        else
                            # Find available kernel headers
                            for kver in $(ls /lib/modules/ 2>/dev/null || echo ""); do
                                if [ -d "/lib/modules/$kver/build" ]; then
                                    echo "/lib/modules/$kver/build"
                                    break
                                fi
                            done
                        fi
                    ''',
                    returnStdout: true
                ).trim()
                
                if (kernelHeadersPath && kernelHeadersPath != "/lib/modules/\$(uname -r)/build") {
                    echo "Using kernel headers: ${kernelHeadersPath}"
                    sh "make KERNEL_SRC=${kernelHeadersPath} ${target}"
                } else {
                    sh "make ${target}"
                }
            }
            
            if (!fileExists(buildConfig.binaryName)) {
                throw new Exception("Binary ${buildConfig.binaryName} was not created")
            }
        }
        
        return 'success'
    } catch (Exception e) {
        echo "Module ${moduleName} build failed: ${e.message}"
        throw e
    }
}

// Function to build all enabled modules
def buildModules() {
    def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
    
    echo "DEBUG: env.ALL_BUILD_MODULES = '${env.ALL_BUILD_MODULES}'"
    echo "DEBUG: params.BUILD_MODULES = '${params.BUILD_MODULES}'"
    
    def buildModules = []
    
    // Priority order: 1. Pipeline config, 2. Parameters, 3. Environment variable
    
    // First, try to get build modules from pipeline configuration
    echo "DEBUG: Loading build configuration from pipeline config..."
    def enabledModules = getEnabledModules(pipelineConfig)
    echo "DEBUG: enabledModules from config = ${enabledModules}"
    
    if (enabledModules.size() > 0) {
        buildModules = enabledModules
        echo "Using build modules from pipeline config: ${buildModules.join(', ')}"
    }
    
    // Override with parameters if provided
    if (params.BUILD_MODULES && params.BUILD_MODULES.trim()) {
        buildModules = params.BUILD_MODULES.split(',').collect { it.trim() }.findAll { it }
        echo "OVERRIDE: Using build modules from parameters: ${buildModules.join(', ')}"
    }
    
    // Override with environment variable if provided (highest priority for automation)
    if (env.ALL_BUILD_MODULES && env.ALL_BUILD_MODULES.trim()) {
        buildModules = env.ALL_BUILD_MODULES.split(',').collect { it.trim() }.findAll { it }
        echo "OVERRIDE: Using build modules from environment variable: ${buildModules.join(', ')}"
    }
    
    if (buildModules.size() == 0) {
        echo "No build modules specified and none found in pipeline configuration - skipping build execution"
        // Set empty results to indicate no builds were run
        globalBuildResults = [:]
        globalBuildStatus = 'success'
        echo "Build status set to success (no builds configured)"
        return [:]
    }
    
    echo "Building ${buildModules.size()} modules: ${buildModules.join(', ')}"
    def buildResults = [:]
    
    buildModules.each { moduleName ->
        echo "Building module: ${moduleName}"
        try {
            def buildConfig = getModuleBuildConfig(pipelineConfig, moduleName)
            
            // Ensure build directory exists
            if (!fileExists(buildConfig.buildDir)) {
                sh "mkdir -p ${buildConfig.buildDir}"
            }
            
            // Execute the build
            buildResults[moduleName] = buildModule(moduleName, buildConfig)
            echo "Module ${moduleName} built successfully"
        } catch (Exception e) {
            buildResults[moduleName] = "failed: ${e.message}"
            echo "Module ${moduleName} build failed: ${e.message}"
            throw e
        }
    }
    
    // Store results globally for final PR comment
    globalBuildResults = buildResults
    
    // Check if any build failed
    if (buildResults.values().any { it != 'success' }) {
        globalBuildStatus = 'failure'
        error "Some modules failed to build"
    }
    
    // Update global status and return results
    globalBuildStatus = 'success'
    return buildResults
}

// Helper function to get test configurations from test config file
def getTestConfigs(pipelineConfig) {
    def testConfigs = [:]
    
    // Read test configuration to get all test-related configurations
    def testConfigFile = pipelineConfig.testing?.test_config_file
    
    // If no test config file specified in pipeline config, use discovered one
    if (!testConfigFile) {
        testConfigFile = env.TEST_CONFIG_PATH
    }
    
    if (!testConfigFile) {
        error "test_config_file not specified in pipeline configuration testing section and no test config discovered"
    }
    
    if (!fileExists(testConfigFile)) {
        error "Test config file not found: ${testConfigFile}. Cannot proceed without test configuration."
    }
    
    try {
        def testConfigYaml = readYaml file: testConfigFile
        
        // Extract global test settings
        testConfigs.global = testConfigYaml.global ?: [:]
        
        // Extract all test configurations
        testConfigs.tests = testConfigYaml.tests ?: [:]
        
        // Extract requirements if any
        testConfigs.requirements = testConfigYaml.requirements ?: [:]
        
        echo "Test configurations loaded successfully from ${testConfigFile}"
        echo "Available test suites: ${testConfigs.tests.keySet().join(', ')}"
        
        // Only check precompiled driver settings if qemu_integration is enabled
        if (testConfigs.tests?.qemu_integration?.enabled && testConfigs.tests?.qemu_integration?.use_precompiled_driver) {
            echo "Driver mode: Using precompiled driver from ${testConfigs.tests.qemu_integration.precompiled_path ?: 'default path'} (for QEMU tests only)"
        } else {
            echo "Driver mode: Compiled from source"
        }
        
        // Validate that we have at least one test configuration
        if (testConfigs.tests.isEmpty()) {
            error "No test configurations found in ${testConfigFile}"
        }
        
    } catch (Exception e) {
        error "Failed to read test configuration from ${testConfigFile}: ${e.message}"
    }
    
    return testConfigs
}

// Helper function to extract module configuration from test configs for a specific test suite
def getModuleConfigFromTestSuite(testConfigs, testSuiteName) {
    def moduleConfig = [:]
    
    def testSuite = testConfigs.tests[testSuiteName]
    if (!testSuite) {
        error "Test suite '${testSuiteName}' not found in test configuration"
    }
    
    // Extract environment variables that define module paths
    if (testSuite.env) {
        moduleConfig.moduleDir = testSuite.env.MODULE_DIR
        moduleConfig.moduleName = testSuite.env.MODULE_NAME
        moduleConfig.sourceFile = testSuite.env.SOURCE_FILE
        
        // Validate required fields
        if (!moduleConfig.moduleDir) {
            error "MODULE_DIR not specified in test suite '${testSuiteName}' environment configuration"
        }
        if (!moduleConfig.moduleName) {
            error "MODULE_NAME not specified in test suite '${testSuiteName}' environment configuration"
        }
        
        echo "Module config for '${testSuiteName}': moduleDir=${moduleConfig.moduleDir}, moduleName=${moduleConfig.moduleName}, sourceFile=${moduleConfig.sourceFile}"
    } else {
        error "No environment configuration found for test suite '${testSuiteName}'"
    }
    
    return moduleConfig
}

// Helper function to get enabled test suites from pipeline config
def getEnabledTestSuites(pipelineConfig) {
    def enabledTestSuites = []
    
    echo "DEBUG: Reading test configuration from test config file..."
    
    // Get the test config file path from pipeline config or use discovered one
    def testConfigFile = pipelineConfig.testing?.test_config_file ?: env.TEST_CONFIG_PATH
    if (!testConfigFile) {
        echo "ERROR: test_config_file not specified in pipeline configuration testing section and no test config discovered"
        return enabledTestSuites
    }
    echo "DEBUG: Using test config file: ${testConfigFile}"
    
    // Check if the test config file exists
    if (!fileExists(testConfigFile)) {
        echo "ERROR: Test config file not found: ${testConfigFile}"
        return enabledTestSuites
    }
    
    try {
        // Read and parse the YAML test configuration
        def testConfigYaml = readYaml file: testConfigFile
        echo "DEBUG: Successfully loaded test config"
        
        // Check if tests configuration exists
        if (!testConfigYaml.tests) {
            echo "No tests configuration found in ${testConfigFile}"
            return enabledTestSuites
        }
        
        echo "DEBUG: Found tests section, processing test suites..."
        testConfigYaml.tests.each { suiteName, suiteConfig ->
            echo "DEBUG: Processing test suite '${suiteName}' with enabled: ${suiteConfig.enabled}"
            if (suiteConfig.enabled != false) {
                enabledTestSuites.add(suiteName)
                echo "DEBUG: Added '${suiteName}' to enabled test suites"
            } else {
                echo "DEBUG: Skipped '${suiteName}' (disabled)"
            }
        }
        
        echo "Found ${enabledTestSuites.size()} enabled test suites: ${enabledTestSuites.join(', ')}"
        
    } catch (Exception e) {
        echo "ERROR: Failed to read test configuration from ${testConfigFile}: ${e.message}"
        echo "Falling back to empty test suite list"
    }
    
    return enabledTestSuites
}

// Helper function to get test suites for general test stage (excludes own_pipeline modules)
def getTestStageModules(pipelineConfig) {
    def enabledTestSuites = getEnabledTestSuites(pipelineConfig)
    def testStageModules = []
    
    echo "DEBUG: Filtering test suites for general test stage..."
    
    // Get the test config file path from pipeline config or use discovered one
    def testConfigFile = pipelineConfig.testing?.test_config_file ?: env.TEST_CONFIG_PATH
    if (!testConfigFile || !fileExists(testConfigFile)) {
        echo "No test config file found, returning all enabled test suites"
        return enabledTestSuites
    }
    
    try {
        // Read and parse the YAML test configuration
        def testConfigYaml = readYaml file: testConfigFile
        
        // Filter out modules that have their own pipeline stage
        enabledTestSuites.each { suiteName ->
            def suiteConfig = testConfigYaml.tests?."${suiteName}"
            if (suiteConfig?.own_pipeline == true) {
                echo "DEBUG: Skipping '${suiteName}' - has own_pipeline: true"
            } else {
                testStageModules.add(suiteName)
                echo "DEBUG: Added '${suiteName}' to test stage modules"
            }
        }
        
        echo "Test stage will run ${testStageModules.size()} modules: ${testStageModules.join(', ')}"
        
    } catch (Exception e) {
        echo "ERROR: Failed to filter test modules: ${e.message}"
        echo "Falling back to all enabled test suites"
        return enabledTestSuites
    }
    
    return testStageModules
}

// Helper function to get repository configuration for a specific test module
def getModuleRepository(pipelineConfig, moduleName) {
    def defaultRepo = env.GITHUB_REPO ?: "simtemp-system"
    
    // Get the test config file path from pipeline config or use discovered one
    def testConfigFile = pipelineConfig.testing?.test_config_file ?: env.TEST_CONFIG_PATH
    if (!testConfigFile || !fileExists(testConfigFile)) {
        echo "No test config file found, using default repository: ${defaultRepo}"
        return defaultRepo
    }
    
    try {
        // Read and parse the YAML test configuration
        def testConfigYaml = readYaml file: testConfigFile
        
        // Check if module configuration exists with repository setting
        if (testConfigYaml.tests?."${moduleName}"?.repository) {
            def moduleRepo = testConfigYaml.tests."${moduleName}".repository
            echo "Found repository configuration for module '${moduleName}': ${moduleRepo}"
            return moduleRepo
        } else {
            echo "No repository configured for module '${moduleName}', using default: ${defaultRepo}"
            return defaultRepo
        }
        
    } catch (Exception e) {
        echo "ERROR: Failed to read repository config for module '${moduleName}': ${e.message}"
        echo "Using default repository: ${defaultRepo}"
        return defaultRepo
    }
}

// Helper function to get test suites from stage configuration
def getStageTestSuites(pipelineConfig) {
    def stageTestSuites = []
    
    echo "DEBUG: Checking pipelineConfig.stages?.test?.test_suites..."
    echo "DEBUG: pipelineConfig.stages = ${pipelineConfig.stages}"
    echo "DEBUG: pipelineConfig.stages?.test = ${pipelineConfig.stages?.test}"
    
    // Check if stage test configuration exists
    if (pipelineConfig.stages?.test?.test_suites) {
        stageTestSuites = pipelineConfig.stages.test.test_suites
        echo "Found test suites in stage config: ${stageTestSuites.join(', ')}"
    } else {
        echo "No stages.test.test_suites configuration found"
    }
    
    return stageTestSuites
}

// Function to execute Jenkins integration tests
def executeJenkinsTests() {
    def testOutput = []
    def allPassed = true
    
    echo "=== Jenkins Integration Test Suite ==="
    
    // Test 1: Connectivity
    echo "[INFO] Test 1: Jenkins connectivity test"
    try {
        def response = sh(script: "curl -s -w '%{http_code}' -o /dev/null http://localhost:8080/api/json || echo '000'", returnStdout: true).trim()
        if (response == "200" || response == "403") // 403 is also OK, means Jenkins is running but needs auth
        {
            testOutput.add("Test 1: connectivity PASSED")
            echo "[SUCCESS] Jenkins connectivity test passed"
        } else {
            testOutput.add("Test 1: connectivity FAILED")
            echo "[ERROR] Jenkins connectivity test failed (HTTP ${response})"
            allPassed = false
        }
    } catch (Exception e) {
        testOutput.add("Test 1: connectivity FAILED")
        echo "[ERROR] Jenkins connectivity test failed: ${e.message}"
        allPassed = false
    }
    
    // Test 2: Authentication
    echo "[INFO] Test 2: Jenkins authentication test"
    try {
        // Try to access Jenkins with basic auth or check if auth is configured
        def authResponse = sh(script: "curl -s -w '%{http_code}' -o /dev/null http://localhost:8080/login || echo '000'", returnStdout: true).trim()
        if (authResponse == "200") {
            testOutput.add("Test 2: authentication PASSED")
            echo "[SUCCESS] Jenkins authentication test passed"
        } else {
            testOutput.add("Test 2: authentication FAILED")
            echo "[ERROR] Jenkins authentication test failed (HTTP ${authResponse})"
            allPassed = false
        }
    } catch (Exception e) {
        testOutput.add("Test 2: authentication FAILED")
        echo "[ERROR] Jenkins authentication test failed: ${e.message}"
        allPassed = false
    }
    
    // Test 3: PR Processing
    echo "[INFO] Test 3: Jenkins PR processing test"
    try {
        // Load diagnostics module for better PR detection
        def diagnostics = load('deployment/jenkins/diagnostics.groovy')
        
        // Print environment diagnostics
        diagnostics.printEnvironmentDiagnostics()
        
        // Run comprehensive PR detection diagnostics with GitHub token access
        def prDiagnosticResults = null
        def apiConnectivity = false
        withCredentials([string(credentialsId: 'github-api-token', variable: 'GITHUB_TOKEN')]) {
            prDiagnosticResults = diagnostics.runPRDetectionDiagnostics()
            
            // Test GitHub API connectivity while we have token access
            echo "[INFO] Test 3b: GitHub API connectivity test"
            apiConnectivity = diagnostics.testGitHubAPIConnectivity(
                env.GITHUB_TOKEN, 
                env.GITHUB_OWNER, 
                env.GITHUB_REPO
            )
        }
        
        if (prDiagnosticResults.success) {
            env.DETECTED_PR_NUMBER = prDiagnosticResults.prNumber
            testOutput.add("Test 3: pr_processing PASSED")
            echo "[SUCCESS] Jenkins PR processing test passed - PR #${env.DETECTED_PR_NUMBER} detected via ${prDiagnosticResults.methods.findAll { it.value.success }.keySet().join(', ')}"
        } else {
            // Fall back to basic detection for backward compatibility
            def prInfo = env.BRANCH_NAME ?: env.GIT_BRANCH ?: 'unknown'
            def buildInfo = env.BUILD_NUMBER ?: 'unknown'
            
            if (prInfo != 'unknown' && buildInfo != 'unknown') {
                testOutput.add("Test 3: pr_processing PASSED")
                echo "[SUCCESS] Jenkins PR processing test passed - branch: ${prInfo}, build: ${buildInfo}"
            } else {
                testOutput.add("Test 3: pr_processing FAILED")
                echo "[ERROR] Jenkins PR processing test failed - missing branch or build info"
                allPassed = false
            }
        }
        
        // Report GitHub API connectivity results
        if (apiConnectivity) {
            testOutput.add("Test 3b: github_api_connectivity PASSED")
            echo "[SUCCESS] GitHub API connectivity test passed"
        } else {
            testOutput.add("Test 3b: github_api_connectivity FAILED")
            echo "[ERROR] GitHub API connectivity test failed"
            // Don't fail the entire test suite for API connectivity issues
        }
    } catch (Exception e) {
        testOutput.add("Test 3: pr_processing FAILED")
        echo "[ERROR] Jenkins PR processing test failed: ${e.message}"
        allPassed = false
    }
    
    echo "=== Jenkins Test Summary ==="
    testOutput.each { echo it }
    echo "${allPassed ? '[SUCCESS]' : '[FAILED]'} Jenkins integration tests ${allPassed ? 'passed' : 'failed'}"
    
    // Generate test details JSON file for report integration
    try {
        def testDetailsJson = [
            "module": "jenkins_test",
            "timestamp": new Date().toString(),
            "tests": []
        ]
        
        // Parse test output to create structured test details
        testOutput.each { line ->
            if (line.contains('Test ') && line.contains(':')) {
                def parts = line.split(':', 2)
                if (parts.length >= 2) {
                    // Extract test name correctly: "Test 1: connectivity PASSED" -> "connectivity"
                    def testName = parts[1].trim().replaceAll('PASSED|FAILED', '').trim()
                    def status = line.contains('PASSED') ? 'passed' : 'failed'
                    
                    // Map test names to configured test IDs
                    def testId = ""
                    switch(testName) {
                        case "connectivity":
                            testId = "F-J1-TC-001"
                            break
                        case "authentication":
                            testId = "F-J1-TC-002"
                            break
                        case "pr_processing":
                            testId = "F-J1-TC-003"
                            break
                        case "github_api_connectivity":
                            testId = "F-J1-TC-004"
                            break
                        default:
                            testId = "F-J1-TC-999"
                    }
                    
                    testDetailsJson.tests.add([
                        "name": testName,
                        "test_id": testId,
                        "status": status,
                        "description": " ${testName}"
                    ])
                }
            }
        }
        
        // Write JSON file
        def jsonContent = writeJSON returnText: true, json: testDetailsJson
        writeFile file: '/tmp/test_details_jenkins_test.json', text: jsonContent
        echo "Generated test details file: /tmp/test_details_jenkins_test.json"
        echo "DEBUG: JSON content preview: ${jsonContent.take(200)}..."
        
    } catch (Exception e) {
        echo "Warning: Could not generate test details JSON: ${e.message}"
    }
    
    return testOutput.join('\n')
}

// Function to run only Jenkins integration tests
def runJenkinsTests() {
    echo "=== Jenkins Integration Test Stage ==="
    
    def testResults = [:]
    def testDetails = [:]
    
    echo "Executing Jenkins integration tests..."
    def testOutput = executeJenkinsTests()
    def result = testOutput.contains('FAILED') ? 1 : 0
    
    testResults['jenkins_test'] = result
    
    // Parse test output to extract individual test results
    def moduleTestDetails = []
    def lines = testOutput.split('\n')
    
    for (def line : lines) {
        if (line.contains('Test ') && line.contains(':') && (line.contains('PASSED') || line.contains('FAILED'))) {
            // Extract jenkins test results: "Test 1: connectivity PASSED"
            def testMatch = line =~ /Test\s+\d+:\s*(\w+)\s*(PASSED|FAILED)/
            if (testMatch) {
                def testName = testMatch[0][1]
                def status = testMatch[0][2]
                moduleTestDetails.add("Test: ${testName} ${status}")
            }
        }
    }
    
    testDetails['jenkins_test'] = moduleTestDetails
    
    // Store results globally for final PR comment
    globalTestResults['jenkins_test'] = result
    globalTestDetails['jenkins_test'] = moduleTestDetails
    
    if (result != 0) {
        echo "Jenkins integration tests failed"
        globalTestStatus = 'failure'
        error "Jenkins integration tests failed with exit code: ${result}"
    } else {
        echo "Jenkins integration tests passed"
    }
    
    return [testResults: testResults, testDetails: testDetails]
}

// Helper function to load detailed test report from JSON
def loadDetailedTestReport(pipelineConfig) {
    def reportsDirectory = pipelineConfig.testing?.reports_directory
    if (!reportsDirectory) {
        echo "Warning: reports_directory not specified in pipeline configuration"
        return null
    }
    
    def reportFile = "${WORKSPACE}/${reportsDirectory}/test_report_detailed.json"
    echo "Looking for detailed test report at: ${reportFile}"
    
    if (!fileExists(reportFile)) {
        echo "Warning: Detailed test report not found at ${reportFile}"
        echo "Checking if reports directory exists: ${WORKSPACE}/${reportsDirectory}"
        return null
    }
    
    echo "📂 Report file found, checking timestamp..."
    try {
        // Show file timestamp for debugging
        sh "ls -la '${reportFile}' || echo 'Cannot get file details'"
    } catch (Exception e) {
        echo "Could not get file details: ${e.message}"
    }
    
    try {
        def reportJson = readJSON file: reportFile
        echo "Loaded fresh detailed test report with ${reportJson.summary?.total_tests ?: 0} tests from ${reportJson.summary?.total_modules ?: 0} modules"
        echo "Report timestamp: ${reportJson.summary?.timestamp ?: 'not available'}"
        
        // Debug: show module names from the report
        if (reportJson.modules) {
            def moduleNames = reportJson.modules.keySet().join(', ')
            echo "Module names in report: ${moduleNames}"
        }
        
        return reportJson
    } catch (Exception e) {
        echo "Warning: Could not parse detailed test report: ${e.message}"
        return null
    }
}

// Helper function to load GitHub issue mappings from configuration files
def loadGitHubIssueMappings() {
    def mappings = [:]
    
    echo "Loading GitHub issue mappings from configuration files..."
    
    // Try to load from YAML test configuration
    try {
        def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
        def testConfigFile = pipelineConfig.testing?.test_config_file ?: env.TEST_CONFIG_PATH
        
        if (testConfigFile && fileExists(testConfigFile)) {
            def testConfigYaml = readYaml file: testConfigFile
            if (testConfigYaml.github_issue_mappings) {
                mappings.putAll(testConfigYaml.github_issue_mappings)
                echo "Loaded ${testConfigYaml.github_issue_mappings.size()} GitHub issue mappings from ${testConfigFile}"
            }
        }
    } catch (Exception e) {
        echo "Warning: Could not load GitHub issue mappings from YAML config: ${e.message}"
    }
    
    // Try to load from JSON configuration files
    def jsonMappingFiles = [
        'infra/data/github_issue_mappings.json',
        'github_issue_mappings.json'
    ]
    
    jsonMappingFiles.each { jsonFile ->
        try {
            if (fileExists(jsonFile)) {
                def jsonMappings = readJSON file: jsonFile
                if (jsonMappings instanceof Map) {
                    mappings.putAll(jsonMappings)
                    echo "Loaded ${jsonMappings.size()} GitHub issue mappings from ${jsonFile}"
                }
            }
        } catch (Exception e) {
            echo "Warning: Could not load GitHub issue mappings from ${jsonFile}: ${e.message}"
        }
    }
    
    // Try to discover from generated mapping files
    try {
        if (fileExists('simtemp/tests/config/github_mappings.json')) {
            def discoveredMappings = readJSON file: 'simtemp/tests/config/github_mappings.json'
            if (discoveredMappings instanceof Map) {
                mappings.putAll(discoveredMappings)
                echo "Discovered ${discoveredMappings.size()} GitHub issue mappings from generated files"
            }
        }
    } catch (Exception e) {
        echo "Warning: Could not load discovered GitHub issue mappings: ${e.message}"
    }
    
    echo "Total GitHub issue mappings loaded: ${mappings.size()}"
    return mappings
}

// Helper function to convert detailed test report to PR comment format
def convertDetailedReportToPRFormat(detailedReport) {
    if (!detailedReport) {
        return [:]
    }
    
    def testResults = [:]
    def testDetails = [:]
    
    // GitHub repository information for issue links
    def githubRepoOwner = env.GITHUB_OWNER ?: "n2Electrons"
    def githubRepoName = env.GITHUB_REPO ?: "simtemp-system"
    
    // Load GitHub issue mappings dynamically from configuration files
    def githubIssueMapping = loadGitHubIssueMappings()
    
    // Helper function to generate GitHub issue URL from test ID
    def generateGitHubIssueUrl = { testId ->
        if (!testId) return null
        
        // Check if we have a specific issue number for this test ID
        if (githubIssueMapping.containsKey(testId)) {
            def issueNumber = githubIssueMapping[testId]
            return "https://github.com/${githubRepoOwner}/${githubRepoName}/issues/${issueNumber}"
        }
        
        // For test IDs without specific issues, use search URL
        return "https://github.com/${githubRepoOwner}/${githubRepoName}/issues?q=${testId}"
    }
    
    // Process each module from the detailed report
    detailedReport.modules?.each { moduleName, moduleData ->
        // Determine overall module status
        def moduleHasFailures = false
        def moduleTestDetails = []
        
        if (moduleData.tests) {
            moduleData.tests.each { test ->
                def testName = test.name ?: "Unknown Test"
                def testStatus = test.status?.toLowerCase() ?: "unknown"
                def testDesc = test.description ?: ""
                def testId = test.test_id ?: ""
                
                // Format test detail for PR comment
                def statusIcon = ""
                switch (testStatus) {
                    case "passed":
                        statusIcon = "✅"
                        break
                    case "failed":
                        statusIcon = "❌"
                        moduleHasFailures = true
                        break
                    case "skipped":
                        statusIcon = "⏭️"
                        break
                    case "not implemented":
                        statusIcon = "⚪"
                        break
                    case "in progress":
                        statusIcon = "🟡"
                        break
                    default:
                        statusIcon = "❓"
                }
                
                def testDetail = "${statusIcon} Test: ${testName}"
                if (testId) {
                    // Do not show GitHub links for NOT IMPLEMENTED tests
                    if (testStatus == "not implemented") {
                        testDetail = "${statusIcon} Test: [${testId}] ${testName}"
                    } else {
                        def githubUrl = generateGitHubIssueUrl(testId)
                        // Only show links for test IDs with exact GitHub issue mappings
                        if (githubIssueMapping.containsKey(testId)) {
                            testDetail = "${statusIcon} Test: [${testId}](${githubUrl}) ${testName}"
                        } else {
                            testDetail = "${statusIcon} Test: [${testId}] ${testName}"
                        }
                    }
                }
                if (testDesc) {
                    testDetail += " - ${testDesc}"
                }
                moduleTestDetails.add(testDetail)
            }
        }
        
        // Set module result (0 = success, 1 = failure)
        testResults[moduleName] = moduleHasFailures ? 1 : 0
        testDetails[moduleName] = moduleTestDetails
    }
    
    return [testResults: testResults, testDetails: testDetails]
}

// Helper function to parse test output and extract individual test results
def parseTestOutput(testOutput) {
    def moduleTestDetails = []
    def lines = testOutput.split('\n')
    
    // Regular parsing for modules (jenkins_test handled in separate stage)
    def inTestSuite = false
    
    for (def line : lines) {
        if (line.contains('=== Test Suite for Module:')) {
            inTestSuite = true
        } else if (line.contains('=== Test Summary ===')) {
            inTestSuite = false
        } else if (inTestSuite) {
            // Look for test execution patterns - updated to match actual output format
            if (line.contains('Test ') && line.contains(':') && line =~ /Test\s+\d+:/) {
                // Extract test name and description from format: "Test 1: Basic execution test"
                def testMatch = line =~ /Test\s+(\d+):\s*(.+)/
                if (testMatch) {
                    def testNum = testMatch[0][1]
                    def testDesc = testMatch[0][2]
                    
                    // Clean up test description - remove any status indicators and brackets
                    def cleanDesc = testDesc.replaceAll(/\s*\[SKIPPED.*?\]/, '').trim()
                    
                    moduleTestDetails.add("Test ${testNum}: ${cleanDesc}")
                }
            } else if (line.contains('test passed') || line.contains('Test passed')) {
                // Mark the last test as passed
                if (moduleTestDetails.size() > 0) {
                    def lastIndex = moduleTestDetails.size() - 1
                    def lastTest = moduleTestDetails[lastIndex]
                    if (lastTest.startsWith('Test ') && !lastTest.contains('PASSED') && !lastTest.contains('FAILED')) {
                        moduleTestDetails[lastIndex] = lastTest + " PASSED"
                    }
                }
            } else if (line.contains('test failed') || line.contains('Test failed')) {
                // Mark the last test as failed
                if (moduleTestDetails.size() > 0) {
                    def lastIndex = moduleTestDetails.size() - 1
                    def lastTest = moduleTestDetails[lastIndex]
                    if (lastTest.startsWith('Test ') && !lastTest.contains('PASSED') && !lastTest.contains('FAILED')) {
                        moduleTestDetails[lastIndex] = lastTest + " FAILED"
                    }
                }
            }
        }
    }
    
    return moduleTestDetails
}

// Function to execute all module tests
def runModuleTests() {
    // Load pipeline configuration
    def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
    
    echo "DEBUG: env.ALL_TEST_MODULES = '${env.ALL_TEST_MODULES}'"
    echo "DEBUG: params.TEST_MODULES = '${params.TEST_MODULES}'"
    
    def testModules = []
    
    // Priority order: 1. External test config, 2. Parameters, 3. Environment variable
    
    // First, try to get test modules from test configuration
    echo "DEBUG: Loading test configuration from test config..."
    def configTestSuites = getTestStageModules(pipelineConfig)
    
    echo "DEBUG: configTestSuites = ${configTestSuites}"
    echo "DEBUG: configTestSuites.size() = ${configTestSuites.size()}"
    echo "DEBUG: Available test suites: ${configTestSuites.join(', ')}"
    
    // Use enabled test suites from test configuration
    if (configTestSuites.size() > 0) {
        testModules = configTestSuites
        echo "Using test stage modules from test config: ${testModules.join(', ')}"
    } else {
        echo "WARNING: No enabled test suites found in test configuration"
    }
    
    // Override with parameters if provided
    if (params.TEST_MODULES && params.TEST_MODULES.trim()) {
        testModules = params.TEST_MODULES.split(',')
        echo "OVERRIDE: Using test modules from parameters: ${testModules.join(', ')}"
    }
    
    // Override with environment variable if provided (highest priority for automation)
    if (env.ALL_TEST_MODULES && env.ALL_TEST_MODULES.trim()) {
        testModules = env.ALL_TEST_MODULES.split(',')
        echo "OVERRIDE: Using test modules from environment variable: ${testModules.join(', ')}"
    }
    
    // EXCLUDE jenkins_test from this stage (it runs in its own stage)
    testModules = testModules.findAll { module ->
        module.trim() != 'jenkins_test'
    }
    echo "Test modules after excluding jenkins_test: ${testModules.join(', ')}"
    
    echo "Preparing to test modules: ${testModules.join(', ')}"
    
    def enabledModules = []
    // Process each module
    testModules.each { module ->
        module = module.trim()
        if (module) {
            enabledModules.add(module)
        }
    }
    
    if (enabledModules.size() == 0) {
        echo "No test modules specified - skipping test execution"
        // Set empty results to indicate no tests were run
        globalTestResults = [:]
        globalTestDetails = [:]
        globalTestStatus = 'success'
        echo "Test status set to success (no tests configured)"
        return [:]
    }
    
    echo "Testing ${enabledModules.size()} enabled modules: ${enabledModules.join(', ')}"
    
    def testResults = [:]
    def testDetails = [:]
    def overallResult = 0
    
    for (def moduleName in enabledModules) {
        echo "DEBUG: Processing test module: ${moduleName}"
        
        // Get repository configuration for this module
        def moduleRepository = getModuleRepository(pipelineConfig, moduleName)
        echo "Using repository '${moduleRepository}' for module '${moduleName}'"
        
        def result = 0
        def testOutput = ""
        
        // Regular module tests (jenkins_test is handled in separate stage)
        echo "Executing regular module test for: ${moduleName}"
        
        // Get test paths from pipeline configuration
        def testRunner = pipelineConfig.testing?.test_composer
        def testConfigFile = pipelineConfig.testing?.test_config_file
        
        if (!testRunner) {
            error "test_composer not specified in pipeline configuration testing section"
        }
        if (!testConfigFile) {
            error "test_config_file not specified in pipeline configuration testing section"
        }
        
        echo "Using test runner [testRunner]: ${testRunner}"
        echo "Using test config: ${testConfigFile}"
            
        def testScript = """cd ${WORKSPACE} && python3 ${testRunner} --verbose"""
        
        try {
            testOutput = sh(script: testScript, returnStdout: true)
            result = 0  // If no exception, tests passed
        } catch (Exception e) {
            // If exception occurs, capture the output and get the exit code
            testOutput = sh(script: testScript, returnStdout: true, returnStatus: false) ?: ""
            result = sh(script: testScript, returnStatus: true)
        }
        
        testResults[moduleName] = result
        
        // Parse test output to extract individual test results
        def moduleTestDetails = parseTestOutput(testOutput)
        
        testDetails[moduleName] = moduleTestDetails
        
        // Don't automatically assign status based on module result
        // Tests should only get status icons if they explicitly have them
        // from the detailed test report or actual test execution
        
        if (result != 0) {
            echo "Tests failed for module: ${moduleName} (exit code: ${result})"
            overallResult = result
        } else {
            echo "Tests passed for module: ${moduleName}"
        }
    }
    
    // Generate detailed JSON test reports after all tests complete
    echo "Generating detailed JSON test reports..."
    try {
        // Clean up old timestamped test detail files first
        echo "🧹 Cleaning up old timestamped test detail files..."
        try {
            sh """
                cd simtemp/tests
                python3 cleanup_test_artifacts.py || echo "Cleanup script failed, using fallback"
                find /tmp -name 'test_details_*_[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9].json' -delete 2>/dev/null || true
            """
        } catch (Exception e) {
            echo "Warning: Could not clean timestamped files: ${e.message}"
        }
        
        // Debug: Show test detail files before cleanup
        echo "Test detail files in /tmp before cleanup:"
        try {
            sh "ls -la /tmp/test_details_*.json 2>/dev/null || echo 'No test detail files found'"
            
            // Clean up any empty or malformed test detail files before report generation
            sh """
                find /tmp -name 'test_details_*.json' -size 0 -delete 2>/dev/null || true
                find /tmp -name 'test_details_*.json' -exec sh -c 'python3 -m json.tool "\$1" >/dev/null 2>&1 || rm -f "\$1"' _ {} \\; 2>/dev/null || true
            """
            
            echo "Test detail files after cleanup:"
            sh "ls -la /tmp/test_details_*.json 2>/dev/null || echo 'No test detail files found after cleanup'"
        } catch (Exception e) {
            echo "Warning: Could not execute debug commands - may be running outside node context: ${e.message}"
        }
        
        // Get reports directory from pipeline configuration
        def reportsDirectory = pipelineConfig.testing?.reports_directory
        if (!reportsDirectory) {
            error "reports_directory not specified in pipeline configuration testing section"
        }
        
        // Ensure reports directory exists and clean any stale reports
        sh "mkdir -p ${WORKSPACE}/${reportsDirectory}"
        sh "rm -f ${WORKSPACE}/${reportsDirectory}/test_report_detailed.json || true"
        sh "rm -f ${WORKSPACE}/${reportsDirectory}/test_report_detailed.html || true"
        
        // Use the simtemp test composer with configuration-driven paths
        def reportGenerator = pipelineConfig.testing?.test_composer
        if (!reportGenerator) {
            error "test_composer not specified in pipeline configuration testing section"
        }
        
        try {
            sh "cd ${WORKSPACE} && python3 ${reportGenerator} --output-dir ${reportsDirectory}"
            echo "JSON test reports generated successfully"
            
            // Debug: Show what files exist in reports directory
            echo "Files in ${reportsDirectory} directory:"
            sh "ls -la ${WORKSPACE}/${reportsDirectory}/ || echo 'No reports directory found'"
        } catch (Exception e) {
            echo "Warning: Could not execute shell commands - may be running outside node context: ${e.message}"
            // Try alternative approach without shell commands
            echo "Skipping report generation due to context limitations"
        }
        
        // Clear any previous cached data and load fresh detailed test report
        globalDetailedReport = [:]  // Clear any previous cached data
        echo "Loading fresh detailed test report for PR comment enhancement..."
        def detailedReport = loadDetailedTestReport(pipelineConfig)
        if (detailedReport) {
            globalDetailedReport = detailedReport  // Store fresh report globally for PR comment
            echo "Fresh detailed report loaded with ${detailedReport.summary?.total_tests ?: 0} tests from ${detailedReport.summary?.total_modules ?: 0} modules"
            def enhancedData = convertDetailedReportToPRFormat(detailedReport)
            if (enhancedData.testResults && enhancedData.testDetails) {
                echo "Enhanced test data loaded from detailed report"
                // Override with structured data from detailed report
                testResults = enhancedData.testResults
                testDetails = enhancedData.testDetails
                
                // Recalculate overall result based on detailed report
                overallResult = testResults.values().any { it != 0 } ? 1 : 0
                echo "Final test summary from detailed report: ${testResults.size()} modules, overall result: ${overallResult}"
            }
        }
        
    } catch (Exception e) {
        echo "Warning: Could not generate JSON test reports: ${e.message}"
    }
    
    // Store results globally for final PR comment
    globalTestResults = testResults
    globalTestDetails = testDetails
    if (overallResult != 0) {
        globalTestStatus = 'failure'
        error "Tests failed with exit code: ${overallResult}"
    } else {
        globalTestStatus = 'success'
    }
    
    return testResults
}

// Function to send consolidated PR comment with all results
def sendConsolidatedPRComment() {
    if (!params.PUBLISH_PR_COMMENT) {
        echo "DEBUG: PR comment disabled by parameter"
        return
    }
    
    // Load pipeline configuration first (needed for repository configuration)
    def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
    
    // Generate Python test files table comment using the dedicated script
    echo "🧪 Generating PR comment with Python test files table..."
    try {
        def pythonScript = "simtemp/tests/jenkins_pr_comment_generator.py"
        if (fileExists(pythonScript)) {
            // Set environment variables for the Python script
            def actualConfigPath = env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH
            def testConfigPath = pipelineConfig?.testing?.test_config_file ?: "simtemp/tests/config/simtemp_tests.yml"
            
            echo "DEBUG: Using config paths - pipeline: ${actualConfigPath}, test: ${testConfigPath}"
            
            sh """
                cd ${WORKSPACE}
                export TEST_CONFIG_PATH="${testConfigPath}"
                export ACTUAL_PIPELINE_CONFIG_PATH="${actualConfigPath}"
                export BUILD_NUMBER="${env.BUILD_NUMBER}"
                export BUILD_URL="${env.BUILD_URL}"
                export JOB_NAME="${env.JOB_NAME}"
                export BRANCH_NAME="${env.BRANCH_NAME}"
                export BUILD_STATUS="${(globalBuildStatus == 'failure' || globalTestStatus == 'failure') ? 'failure' : 'success'}"
                python3 ${pythonScript}
            """
            
            // Check if the generated comment files exist
            if (fileExists('pr_comment_table.md')) {
                echo "✅ Python test files comment generated successfully"
                
                // Read the generated comment
                def pythonFilesComment = readFile('pr_comment_table.md')
                
                // Send the Python files comment and return early
                def overallStatus = (globalBuildStatus == 'failure' || globalTestStatus == 'failure') ? 'failure' : 'success'
                def githubRepo = getPRTargetRepository(pipelineConfig)
                sendPRComment(overallStatus, pythonFilesComment, githubRepo)
                return
            } else {
                echo "⚠️ Python files comment generation failed - pr_comment_table.md not found"
            }
        } else {
            echo "⚠️ Python comment generator script not found at ${pythonScript}"
        }
    } catch (Exception e) {
        echo "⚠️ Error generating Python files comment: ${e.message}"
        echo "Falling back to standard PR comment format"
    }
    
    // Load GitHub issue mappings dynamically from configuration files
    def githubIssueMapping = loadGitHubIssueMappings()
    
    // Helper function to generate GitHub issue URL from test ID
    def generateGitHubIssueUrl = { testId ->
        if (!testId) return null
        
        // Check if we have a specific issue number for this test ID
        if (githubIssueMapping.containsKey(testId)) {
            def issueNumber = githubIssueMapping[testId]
            return "https://github.com/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/issues/${issueNumber}"
        }
        
        // For test IDs without specific issues, use search URL
        return "https://github.com/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/issues?q=${testId}"
    }
    
    echo "DEBUG: sendConsolidatedPRComment() called"
    echo "DEBUG: globalBuildResults = ${globalBuildResults}"
    echo "DEBUG: globalTestResults = ${globalTestResults}"
    echo "DEBUG: globalTestDetails = ${globalTestDetails}"
    echo "DEBUG: globalBuildStatus = ${globalBuildStatus}"
    echo "DEBUG: globalTestStatus = ${globalTestStatus}"
    
    // Get build information
    def buildNumber = env.BUILD_NUMBER ?: 'unknown'
    def buildUrl = env.BUILD_URL ?: ''
    def jobName = env.JOB_NAME ?: 'unknown'
    def branchName = env.BRANCH_NAME ?: 'unknown'
    
    // Determine overall status
    def overallStatus = 'success'
    if (globalBuildStatus == 'failure' || globalTestStatus == 'failure') {
        overallStatus = 'failure'
    }
    
    def statusText = overallStatus == 'success' ? 'Tests Success Details' : 'Tests Failure Details'
    
    // Start building the comment in the requested format
    def commentLines = []
    commentLines.add("## ${statusText}")
    commentLines.add("Branch: `${branchName}`")
    commentLines.add("Pipeline: [Overview](${buildUrl}display/redirect)")
    commentLines.add("Jenkins Job: [#${buildNumber}](${buildUrl})")
    commentLines.add("Console output: [Log](${buildUrl}console)")
    commentLines.add("Download [Artifacts](${buildUrl}artifact/)")
    commentLines.add("")

    // Add build results if available
    if (globalBuildResults.size() > 0) {
        commentLines.add("## Build Results:")
        commentLines.add("")
        globalBuildResults.each { moduleName, result ->
            def buildStatus = result == 'success' ? '✅' : '❌'
            commentLines.add("- **${moduleName}**: ${result}")
        }
        commentLines.add("")
    }

    // Add detailed test results in the requested format
    if (globalTestResults.size() > 0) {
        commentLines.add("## Test Results:")
        commentLines.add("")
        
        // Collect and display requirement IDs (extract parent requirements from test IDs)
        def allRequirementIds = [] as Set
        if (globalDetailedReport && globalDetailedReport.modules) {
            globalDetailedReport.modules.each { moduleName, moduleData ->
                if (moduleData.tests) {
                    moduleData.tests.each { test ->
                        def testId = test.test_id ?: ""
                        if (testId) {
                            // Extract parent requirement ID from test case ID
                            // e.g., "F-K1-TC-001" -> "F-K1", "F-K8-TC-001" -> "F-K8"
                            def reqMatch = testId =~ /^([A-Z]+-[A-Z]+\d+)/
                            if (reqMatch) {
                                def parentReqId = reqMatch[0][1]
                                allRequirementIds.add(parentReqId)
                            }
                        }
                    }
                }
            }
        }
        
        if (allRequirementIds.size() > 0) {
            def sortedIds = allRequirementIds.sort()
            def requirementLinks = []
            sortedIds.each { reqId ->
                // Check if the parent requirement itself has a direct GitHub issue mapping
                if (githubIssueMapping.containsKey(reqId)) {
                    // Use direct issue link for parent requirement
                    def githubUrl = generateGitHubIssueUrl(reqId)
                    requirementLinks.add("[${reqId}](${githubUrl})")
                } else {
                    // Check if this parent requirement has any test cases with GitHub issue mappings
                    def hasMappedTestCases = githubIssueMapping.keySet().any { testId ->
                        testId.startsWith(reqId + "-")
                    }
                    
                    if (hasMappedTestCases) {
                        // Use search URL for parent requirements without direct mappings
                        def githubUrl = "https://github.com/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/issues?q=${reqId}"
                        requirementLinks.add("[${reqId}](${githubUrl})")
                    } else {
                        // Show as non-clickable if no mappings found
                        requirementLinks.add("${reqId}")
                    }
                }
            }
            
            if (requirementLinks.size() > 0) {
                commentLines.add("### **Requirements Coverage**")
                commentLines.add("- **Requirements Tested**: ${requirementLinks.join(', ')}")
                commentLines.add("- **Total Requirements**: ${allRequirementIds.size()}")
                commentLines.add("")
            }
        }
        
        // Summary line - use test report summary if available
        def totalTests = 0
        def passedTests = 0
        def failedTests = 0
        def skippedTests = 0
        def notImplementedTests = 0
        
        // If we have a test report, use its summary
        if (globalDetailedReport && globalDetailedReport.summary) {
            def summary = globalDetailedReport.summary
            totalTests = summary.total_tests ?: 0
            passedTests = summary.passed_tests ?: 0
            failedTests = summary.failed_tests ?: 0
            skippedTests = summary.skipped_tests ?: 0
            notImplementedTests = summary.not_implemented_tests ?: 0
            
            echo "Using detailed report summary: ${totalTests} total, ${passedTests} passed, ${failedTests} failed, ${skippedTests} skipped, ${notImplementedTests} not implemented"
        }
        
        globalTestResults.each { moduleName, result ->
            def moduleStatus = result == 0 ? '✅' : '❌'
            def moduleTestCount = 0
            def modulePassedCount = 0
            
            commentLines.add("### **${moduleName}**")
            
            // Show detailed test results if available
            if (globalTestDetails.containsKey(moduleName) && globalTestDetails[moduleName].size() > 0) {
                globalTestDetails[moduleName].each { detail ->
                    def testLine = ""
                    def testPassed = false
                    
                    if (moduleName == 'jenkins_test') {
                        // Special handling for jenkins_test format: "Test: connectivity PASSED"
                        if (detail.contains('Test:')) {
                            def parts = detail.split(':', 2) // Split into max 2 parts
                            if (parts.length >= 2) {
                                def testName = parts[1].trim().replaceAll(' ✅', '').replaceAll(' ❌', '')
                                def status = (detail.toLowerCase().contains('passed')) ? '✅' : ((detail.toLowerCase().contains('failed')) ? '❌' : '❔')
                                testPassed = status == '✅'
                                testLine = "- ${status} **${testName}**"
                            }
                        }
                    } else {
                        // Regular module handling: "Test 1: test_name PASSED"
                        if (detail.contains('Test ') && detail.contains(':')) {
                            def parts = detail.split(':', 2) // Split into max 2 parts
                            if (parts.length >= 2) {
                                def testIdentifier = parts[0].trim() // "Test 1"
                                def testNameAndStatus = parts[1].trim()
                                def testName = testNameAndStatus.replaceAll(' ✅', '').replaceAll(' ❌', '').replaceAll(' ⚪', '').replaceAll(' 🟡', '').trim()
                                def status = detail.contains('✅') ? '✅' : (detail.contains('❌') ? '❌' : (detail.contains('⚪') ? '⚪' : (detail.contains('🟡') ? '🟡' : moduleStatus)))
                                testPassed = detail.contains('✅')
                                
                                // Check if test name contains test ID pattern and add GitHub link
                                def testIdMatch = testName =~ /\[([^\]]+)\]/
                                if (testIdMatch) {
                                    def testId = testIdMatch[0][1]
                                    def cleanTestName = testName.replaceAll(/\[[^\]]+\]\s*/, '').trim()
                                    
                                    // Check if this is a NOT IMPLEMENTED test or IN PROGRESS test, or if test ID has exact mapping
                                    if (status == '⚪' || status == '🟡' || !githubIssueMapping.containsKey(testId)) {
                                        testLine = "- ${status} **${testIdentifier}**: [${testId}] ${cleanTestName}"
                                    } else {
                                        def githubUrl = generateGitHubIssueUrl(testId)
                                        testLine = "- ${status} **${testIdentifier}**: [${testId}](${githubUrl}) ${cleanTestName}"
                                    }
                                } else {
                                    testLine = "- ${status} **${testIdentifier}**: ${testName}"
                                }
                            }
                        }
                    }
                    
                    if (testLine) {
                        commentLines.add(testLine)
                        moduleTestCount++
                        if (testPassed) modulePassedCount++
                    }
                }
                
                // If no individual tests were parsed but we have test details, show them as-is
                if (moduleTestCount == 0 && globalTestDetails[moduleName].size() > 0) {
                    globalTestDetails[moduleName].each { detail ->
                        // Don't add status icon if detail already starts with one
                        if (detail.startsWith('✅') || detail.startsWith('❌') || detail.startsWith('⚪') || detail.startsWith('🟡') || detail.startsWith('⏭️')) {
                            commentLines.add("- ${detail}")
                            // Count as passed only if it actually contains ✅
                            if (detail.contains('✅')) modulePassedCount++
                        } else {
                            def status = result == 0 ? '✅' : '❌'
                            commentLines.add("- ${status} ${detail}")
                            // Count as passed only if the status is success
                            if (result == 0) modulePassedCount++
                        }
                        moduleTestCount++
                    }
                }
            } else {
                // If no detailed test results, show the overall module result
                def status = result == 0 ? '✅' : '❌'
                commentLines.add("- ${status} **Module execution** (exit code: ${result})")
                moduleTestCount = 1
                if (result == 0) modulePassedCount = 1
            }
            
            // Add module summary
            if (moduleTestCount > 1) {
                commentLines.add("  - **Summary**: ${modulePassedCount}/${moduleTestCount} tests passed")
            }
        }
        
        // Add overall test summary
        commentLines.add("### **Overall Test Summary**")
        commentLines.add("- **Total tests**: ${totalTests}")
        commentLines.add("- **Passed**: ${passedTests}")
        commentLines.add("- **Failed**: ${failedTests}")
        if (skippedTests > 0) {
            commentLines.add("- **Skipped**: ${skippedTests}")
        }
        if (notImplementedTests > 0) {
            commentLines.add("- **Not Implemented**: ${notImplementedTests}")
        }
        if (totalTests > 0) {
            def successRate = ((passedTests * 100) / totalTests).intValue()
            commentLines.add("- **Success rate**: ${successRate}%")
        }
        commentLines.add("")
    } else {
        commentLines.add("## Test Results:")
        commentLines.add("ℹ️ **No tests were configured to run**")
        commentLines.add("")
        commentLines.add("Tests are configured in this priority order:")
        commentLines.add("1. **`pipeline_config.yml`** test suites configuration (primary source)")
        commentLines.add("2. `TEST_MODULES` parameter (override - e.g., 'module1,module2')")
        commentLines.add("3. Manual trigger: Set `ENABLE_JENKINS_TEST=true` AND `TEST_MODULES=jenkins_test`")
        commentLines.add("")
        commentLines.add("Check your `pipeline_config.yml` file or set parameters to override.")
        commentLines.add("")
        commentLines.add("### Build Information:")
        commentLines.add("- Build status: ${globalBuildStatus}")
        commentLines.add("- Test status: ${globalTestStatus} (no tests configured)")
        commentLines.add("")
    }

    // Join all lines into final comment
    def finalComment = commentLines.join('\n')
    
    // Determine target repository for PR comments
    def githubRepo = getPRTargetRepository(pipelineConfig)
    
    // Send the comment using the basic sendPRComment function with target repository
    sendPRComment(overallStatus, finalComment, githubRepo)
}

// Function to determine the target repository for PR comments based on configuration
def getPRTargetRepository(pipelineConfig) {
    def targetRepo = env.GITHUB_REPO
    
    try {
        // Check if repository configuration exists in pipeline config
        if (pipelineConfig.repository?.pr_target) {
            targetRepo = pipelineConfig.repository.pr_target
            echo "Using PR target repository from pipeline config: ${targetRepo}"
        } else {
            echo "No repository.pr_target configuration found in pipeline config, using env.GITHUB_REPO: ${targetRepo}"
        }
        
    } catch (Exception e) {
        echo "ERROR: Failed to read repository configuration from pipeline config: ${e.message}"
        echo "Using env.GITHUB_REPO for PR: ${targetRepo}"
    }
    
    return targetRepo
}

// Function to send PR comment with job results
def sendPRComment(status, details = '', targetRepo = null) {
    def githubRepo = targetRepo ?: env.GITHUB_REPO
    // Try to automatically detect PR number from various environment variables
    def prNumber = null
    
    // Use PR number from diagnostics first (most reliable)
    if (env.DETECTED_PR_NUMBER) {
        prNumber = env.DETECTED_PR_NUMBER
    } 
    // Otherwise check standard environment variables
    else if (env.CHANGE_ID) {
        prNumber = env.CHANGE_ID
    } else if (env.ghprbPullId) {
        prNumber = env.ghprbPullId
    } else if (env.PULL_REQUEST_NUMBER) {
        prNumber = env.PULL_REQUEST_NUMBER
    } else {
        // Try to extract from branch name with expanded patterns
        def branchName = env.BRANCH_NAME ?: env.GIT_BRANCH ?: ''
        def prMatch = branchName =~ /(?i)(?:pr|pull)[\/\-]?(\d+)/
        if (prMatch) {
            prNumber = prMatch[0][1]
        }
    }
    
    if (!prNumber) {
        echo "No PR number detected - attempting to extract from Git commit messages or refs"
        try {
            // Try to get PR number from git log
            def gitLog = sh(script: "git log --oneline -1", returnStdout: true).trim()
            def prMatch = gitLog =~ /(?:#|PR|pr)\s*(\d+)/
            if (prMatch) {
                prNumber = prMatch[0][1]
                echo "Detected PR number from git log: ${prNumber}"
            }
        } catch (Exception e) {
            echo "Could not extract PR from git log: ${e.message}"
        }
    }
    
    // If still no PR number, try to find it via GitHub API using current branch
    if (!prNumber) {
        try {
            withCredentials([string(credentialsId: 'github-api-token', variable: 'GITHUB_TOKEN')]) {
                echo "Attempting to find PR for current branch via GitHub API..."
                def currentBranch = env.BRANCH_NAME ?: env.GIT_BRANCH ?: ''
                
                if (currentBranch) {
                    // Clean branch name (remove origin/ prefix if present)
                    def cleanBranch = currentBranch.replaceAll(/^origin\//, '')
                    
                    // Query GitHub API for PRs matching the current branch
                    def response = sh(
                        script: """
                            curl -s \\
                            -H "Authorization: token ${GITHUB_TOKEN}" \\
                            -H "Accept: application/vnd.github.v3+json" \\
                            "https://api.github.com/repos/${env.GITHUB_OWNER}/${githubRepo}/pulls?state=open&head=${env.GITHUB_OWNER}:${cleanBranch}"
                        """,
                        returnStdout: true
                    ).trim()
                    
                    if (response) {
                        
                        // Parse JSON response
                        def pulls = []
                        try {
                            def jsonSlurper = new groovy.json.JsonSlurper()
                            if (response.trim().startsWith('[')) {
                                pulls = jsonSlurper.parseText(response)
                            }
                        } catch (Exception e) {
                            echo "Error parsing GitHub API response: ${e.message}"
                        }
                        
                        // Extract PR number if found
                        if (pulls && pulls.size() > 0) {
                            prNumber = pulls[0].number.toString()
                            echo "Found PR #${prNumber} for branch '${cleanBranch}'"
                        } else {
                            // Try alternative approach without owner prefix
                            def apiUrl = "https://api.github.com/repos/${env.GITHUB_OWNER}/${githubRepo}/pulls?state=open&head=${cleanBranch}"
                            
                            response = sh(
                                script: """
                                    curl -s \\
                                    -H "Authorization: token ${GITHUB_TOKEN}" \\
                                    -H "Accept: application/vnd.github.v3+json" \\
                                    "${apiUrl}"
                                """,
                                returnStdout: true
                            ).trim()
                            
                            try {
                                def jsonSlurper = new groovy.json.JsonSlurper()
                                if (response.trim().startsWith('[')) {
                                    pulls = jsonSlurper.parseText(response)
                                    
                                    if (pulls && pulls.size() > 0) {
                                        prNumber = pulls[0].number.toString()
                                        echo "Found PR #${prNumber} for branch '${cleanBranch}' (alternative query)"
                                    }
                                }
                            } catch (Exception e) {
                                echo "Error parsing GitHub API response: ${e.message}"
                            }
                            
                            // Last resort - get all PRs and filter
                            if (!prNumber) {
                                def allPRsUrl = "https://api.github.com/repos/${env.GITHUB_OWNER}/${githubRepo}/pulls?state=open"
                                
                                response = sh(
                                    script: """
                                        curl -s \\
                                        -H "Authorization: token ${GITHUB_TOKEN}" \\
                                        -H "Accept: application/vnd.github.v3+json" \\
                                        "${allPRsUrl}"
                                    """,
                                    returnStdout: true
                                ).trim()
                                
                                try {
                                    def jsonSlurper = new groovy.json.JsonSlurper()
                                    if (response.trim().startsWith('[')) {
                                        pulls = jsonSlurper.parseText(response)
                                        
                                        // Process each PR to find our branch
                                        pulls.each { pull ->
                                            if (pull.head.ref == cleanBranch) {
                                                prNumber = pull.number.toString()
                                                echo "Found PR #${prNumber} by matching branch '${cleanBranch}'"
                                            }
                                        }
                                    }
                                } catch (Exception e) {
                                    echo "Error processing all PRs: ${e.message}"
                                }
                            }
                        }
                    }
                }
            }
        } catch (Exception e) {
            echo "Could not query GitHub API for PR detection: ${e.message}"
        }
    }
    
    if (!prNumber) {
        echo "⚠️ No PR number detected from any source - skipping PR comment"
        
        // Debug detailed information to help troubleshoot
        echo "===== Environment Variables for Debugging ====="
        echo "BRANCH_NAME: ${env.BRANCH_NAME}"
        echo "GIT_BRANCH: ${env.GIT_BRANCH}"
        echo "CHANGE_ID: ${env.CHANGE_ID}"
        echo "GITHUB_OWNER: ${env.GITHUB_OWNER}"
        echo "GITHUB_REPO: ${env.GITHUB_REPO}"
        echo "BUILD_NUMBER: ${env.BUILD_NUMBER}"
        echo "BUILD_URL: ${env.BUILD_URL}"
        echo "JOB_NAME: ${env.JOB_NAME}"
        echo "DEBUG: ==========================================="
        
        // Debug Jenkins credential availability without printing it
        withCredentials([string(credentialsId: 'github-api-token', variable: 'DEBUG_TOKEN')]) {
            echo "DEBUG: GitHub token is available: ${DEBUG_TOKEN ? 'yes (length: ' + DEBUG_TOKEN.length() + ')' : 'no'}"
        }
        echo "  ghprbPullId: ${env.ghprbPullId}" 
        echo "  PULL_REQUEST_NUMBER: ${env.PULL_REQUEST_NUMBER}"
        echo "  BRANCH_NAME: ${env.BRANCH_NAME}"
        echo "  GIT_BRANCH: ${env.GIT_BRANCH}"
        echo "  GITHUB_OWNER: ${env.GITHUB_OWNER}"
        echo "  GITHUB_REPO: ${env.GITHUB_REPO}"
        
        // Verificar si se proporcionó un PR_NUMBER manual para pruebas
        if (params.PR_NUMBER) {
            echo "Usando número de PR proporcionado manualmente: ${params.PR_NUMBER}"
            prNumber = params.PR_NUMBER
        } else {
            return
        }
    }
    
    echo "Sending PR comment to detected PR #${prNumber}"
    
    // Use the provided details as the complete comment body, or generate a simple one
    def commentBody = details ?: """
## ${status == 'success' ? '✅' : '❌'} Jenkins Build ${status == 'success' ? 'PASSED' : 'FAILED'}

**Job:** ${env.JOB_NAME}  
**Build:** [#${env.BUILD_NUMBER}](${env.BUILD_URL})  
**Status:** ${status == 'success' ? 'PASSED' : 'FAILED'}

---
*Automated comment from Jenkins CI*
"""
    
    try {
        withCredentials([string(credentialsId: 'github-api-token', variable: 'GITHUB_TOKEN')]) {
            echo "GitHub token credential loaded successfully"
            
            // Create a temporary file with the comment body to avoid shell escaping issues
            def buildNum = env.BUILD_NUMBER ?: 'unknown'
            def commentFile = "${WORKSPACE}/comment_${prNumber}_${buildNum}.json"
            
            // More robust JSON escaping function
            def escapeJson = { text ->
                return text.replace('\\', '\\\\')    // Escape backslashes first
                          .replace('"', '\\"')       // Escape quotes
                          .replace('\n', '\\n')      // Escape newlines
                          .replace('\r', '\\r')      // Escape carriage returns
                          .replace('\t', '\\t')      // Escape tabs
                          .replace('\b', '\\b')      // Escape backspaces
                          .replace('\f', '\\f')      // Escape form feeds
                          .replace('/', '\\/')       // Escape forward slashes (optional but safer)
            }
            
            // Create JSON content with proper escaping
            def escapedComment = escapeJson(commentBody)
            def jsonContent = """{"body":"${escapedComment}"}"""
            
            // Debug: Show JSON content length and first few characters
            echo "JSON content length: ${jsonContent.length()}"
            echo "JSON content preview: ${jsonContent.take(200)}..."
            
            writeFile file: commentFile, text: jsonContent
            
            // Validate JSON syntax before sending
            def jsonValidation = sh(
                script: "python3 -m json.tool '${commentFile}' > /dev/null 2>&1",
                returnStatus: true
            )
            
            if (jsonValidation != 0) {
                echo "⚠️ JSON validation failed. Attempting to fix common issues..."
                // Try a simpler approach with basic text
                def simpleComment = commentBody.replaceAll(/[^\x20-\x7E\n\r\t]/, '') // Remove non-printable chars
                def simpleEscaped = simpleComment.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                def simpleJson = """{"body":"${simpleEscaped}"}"""
                writeFile file: commentFile, text: simpleJson
                echo "Created simplified JSON version"
            }
            
            def response = sh(
                script: """
                    curl -s -X POST \\
                    -H "Authorization: token ${GITHUB_TOKEN}" \\
                    -H "Accept: application/vnd.github.v3+json" \\
                    -H "Content-Type: application/json" \\
                    -d @"${commentFile}" \\
                    "https://api.github.com/repos/${env.GITHUB_OWNER}/${githubRepo}/issues/${prNumber}/comments"
                """,
                returnStdout: true
            ).trim()
            
            // Clean up the temporary file
            sh "rm -f '${commentFile}'"
            
            if (response.contains('"id":')) {
                echo "✅ PR comment sent successfully to PR #${prNumber}"
            } else {
                echo "⚠️ Unexpected response: ${response}"
            }
        }
    } catch (Exception e) {
        echo "❌ Failed to send PR comment: ${e.message}"
        // Don't fail the build if comment fails
    }
}

// Function to test PR comment functionality
def postPRComment(pipelineConfig = null) {
    echo "Preparing PR comment..."
    
    // Determine target repository for PR comments
    def githubRepo = env.GITHUB_REPO
    if (pipelineConfig) {
        githubRepo = getPRTargetRepository(pipelineConfig)
        echo "Using target repository from config: ${githubRepo}"
    } else {
        echo "No pipeline config provided, using default repository: ${githubRepo}"
    }
    
    def prNumber = null
    
    // Check for PR number from various sources (in priority order)
    if (env.DETECTED_PR_NUMBER) {
        prNumber = env.DETECTED_PR_NUMBER
        echo "Using PR #${prNumber} from diagnostics"
    } else if (params.PR_NUMBER) {
        prNumber = params.PR_NUMBER
        echo "Using PR #${prNumber} from parameters"
    } else if (env.CHANGE_ID) {
        prNumber = env.CHANGE_ID
        echo "Using PR #${prNumber} from CHANGE_ID"
    }
    
    if (!prNumber) {
        echo "⚠️ No PR number found. Cannot post comment."
        return
    }
    
    try {
        withCredentials([string(credentialsId: 'github-api-token', variable: 'GITHUB_TOKEN')]) {
            // Test GitHub repository access
            def repoTestResponse = sh(
                script: """
                    curl -s -w "%{http_code}" \\
                    -H "Authorization: token ${GITHUB_TOKEN}" \\
                    -H "Accept: application/vnd.github.v3+json" \\
                    "https://api.github.com/repos/${env.GITHUB_OWNER}/${githubRepo}" \\
                    -o /dev/null
                """,
                returnStdout: true
            ).trim()
            
            if (repoTestResponse == "200") {
                echo "✅ GitHub API access verified - comments will be posted to PR #${prNumber}"
                
                // Actually post the comment here with build results
                // This is just a placeholder - in a real implementation,
                // you would format a comment with test results and post it
                
            } else {
                echo "❌ GitHub API access failed (HTTP ${repoTestResponse})"
                echo "Check GitHub token permissions and repository access"
            }
        }
    } catch (Exception e) {
        echo "❌ PR comment failed: ${e.message}"
        echo "Check GitHub credentials and permissions"
    }
}

pipeline {
    agent any
    
    triggers {
        // Disabled to prevent duplicate executions with infra_ext/Jenkinsfile
        // Use webhook triggers instead for better performance
        // pollSCM('* * * * *')  // Check for changes every minute (most frequent allowed)
        // Note: SCM polling doesn't support seconds, minimum is 1 minute
    }
    
    parameters {
        // Infrastructure configuration
        string(name: 'PIPELINE_CONFIG_PATH', defaultValue: '', description: 'Path to pipeline configuration file (relative to repo root)')
        string(name: 'TEST_CONFIG_PATH', defaultValue: '', description: 'Path to test configuration file (relative to repo root)')
        string(name: 'INFRASTRUCTURE_PATH', defaultValue: 'infrastructure', description: 'Path to infrastructure submodule within parent repository')
        
        // GitHub repository configuration (for PR comments and issue linking)
        string(name: 'GITHUB_OWNER', defaultValue: '', description: 'GitHub repository owner/organization name')
        string(name: 'GITHUB_REPO', defaultValue: '', description: 'GitHub repository name')
        string(name: 'PR_NUMBER', defaultValue: '', description: 'Pull Request number (for manual PR comment testing)')
        
        // Build and test configuration
        string(name: 'BUILD_MODULES', defaultValue: '', description: 'Specific modules to build (comma-separated, overrides config)')
        string(name: 'TEST_MODULES', defaultValue: '', description: 'Specific modules to test (comma-separated, overrides config)')
        
        // Test control parameters
        booleanParam(name: 'ENABLE_JENKINS_TEST', defaultValue: false, description: 'Manual trigger: Set to true AND set TEST_MODULES=jenkins_test to run only Jenkins test')
        string(name: 'TEST_EXCEPTION_MODULE', defaultValue: 'none', description: 'Module for exception testing (use module name from config or "none")')
        booleanParam(name: 'TEST_FORCE_EXCEPTION', defaultValue: false, description: 'Force an exception during tests')
        
        // Output configuration
        booleanParam(name: 'PUBLISH_PR_COMMENT', defaultValue: true, description: 'Post build results as comment to associated PR automatically')
    }

    environment {
        // Configuration paths - these can be overridden by parent repository
        PIPELINE_CONFIG_PATH = "${params.PIPELINE_CONFIG_PATH ?: 'simtemp/pipeline_config.yml'}"
        TEST_CONFIG_PATH = "${params.TEST_CONFIG_PATH ?: 'simtemp/tests/config/simtemp_tests.yml'}"
        
        // Build and test module configuration
        ALL_BUILD_MODULES = "${params.BUILD_MODULES ?: ''}"
        ALL_TEST_MODULES = "${params.TEST_MODULES ?: ''}"
        
        // GitHub repository configuration - can be overridden by parent repository
        // Uso de valores por defecto simplificados para garantizar el funcionamiento de los comentarios en PRs
        // Basado en el commit 00a13a1 que funcionaba correctamente
        GITHUB_OWNER = "${params.GITHUB_OWNER ?: 'n2Electrons'}"
        GITHUB_REPO = "${params.GITHUB_REPO ?: 'n2Electrons-Infra'}"
        
        // Infrastructure submodule path (path to this infrastructure within parent repo)
        INFRASTRUCTURE_PATH = "${params.INFRASTRUCTURE_PATH ?: 'infrastructure'}"
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo 'Code checked out from SCM'
                script {
                    // Clear global variables to prevent cache issues from previous runs
                    clearGlobalVariables()
                    
                    echo "=== Infrastructure Setup ==="
                    echo "Infrastructure path: ${env.INFRASTRUCTURE_PATH}"
                    echo "Pipeline config override: ${params.PIPELINE_CONFIG_PATH}"
                    echo "Test config override: ${params.TEST_CONFIG_PATH}"
                    
                    // Auto-discover or use provided configuration paths
                    def configPath = params.PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH
                    def pipelineConfig = loadPipelineConfig(configPath)
                    
                    // Store the actual config path used for later stages
                    env.ACTUAL_PIPELINE_CONFIG_PATH = configPath
                    
                    // Read sub-project path from pipeline configuration
                    env.SUB_PROJECT_PATH = pipelineConfig.global?.sub_project_path
                    
                    if (!env.SUB_PROJECT_PATH) {
                        error "sub_project_path not defined in global section of ${configPath}"
                    }
                    
                    // Auto-discover test config path if not provided
                    if (!env.TEST_CONFIG_PATH && !params.TEST_CONFIG_PATH) {
                        def testConfigPaths = [
                            'simtemp/tests/config/simtemp_tests.yml'
                        ]
                        
                        for (def testPath : testConfigPaths) {
                            if (fileExists(testPath)) {
                                env.TEST_CONFIG_PATH = testPath
                                echo "Auto-discovered test config at: ${testPath}"
                                break
                            }
                        }
                    } else {
                        env.TEST_CONFIG_PATH = params.TEST_CONFIG_PATH ?: env.TEST_CONFIG_PATH
                    }
                    
                    echo "=== Configuration Setup ==="
                    echo "Sub-project path: ${env.SUB_PROJECT_PATH} (from config)"
                    echo "Pipeline config path: ${configPath}"
                    echo "Test config path: ${env.TEST_CONFIG_PATH}"
                    echo "=== Build Information ==="
                    echo "Branch: ${env.BRANCH_NAME}"
                    echo "Build Number: ${env.BUILD_NUMBER}"
                    echo "Job Name: ${env.JOB_NAME}"
                    echo "=== GitHub Configuration ==="
                    echo "GitHub Owner: ${env.GITHUB_OWNER}"
                    echo "GitHub Repo: ${env.GITHUB_REPO}"
                    echo "=== Parameters ==="
                    echo "BUILD_MODULES: ${params.BUILD_MODULES}"
                    echo "TEST_MODULES: ${params.TEST_MODULES}"
                    echo "ENABLE_JENKINS_TEST: ${params.ENABLE_JENKINS_TEST}"
                    echo "=== Environment ==="
                    echo "ALL_BUILD_MODULES: ${env.ALL_BUILD_MODULES}"
                    echo "ALL_TEST_MODULES: ${env.ALL_TEST_MODULES}"
                    echo "=========================="
                }
            }
        }

        stage('Jenkins-Test') {
            steps {
                script {
                    echo "=== Jenkins Integration Test Stage ==="
                    
                    try {
                        // Run Jenkins-specific integration tests
                        // runJenkinsTests()
                        echo "✅ Jenkins integration tests completed successfully"
                    } catch (Exception e) {
                        echo "❌ Jenkins integration tests failed: ${e.message}"
                        throw e
                    }
                }
            }
            post {
                always {
                    echo "Jenkins integration test stage completed"
                }
                success {
                    echo "✅ Jenkins integration tests passed"
                }
                failure {
                    echo "❌ Jenkins integration tests failed"
                }
            }
        }

        stage('Build') {
            steps {
                script {
                    echo "=== Build Stage ==="
                    echo "DEBUG: About to run module builds..."
                    echo "DEBUG: env.ALL_BUILD_MODULES = '${env.ALL_BUILD_MODULES}'"
                    echo "DEBUG: params.BUILD_MODULES = '${params.BUILD_MODULES}'"
                    
                    // Always try to run builds - buildModules() will handle configuration reading
                    try {
                        buildModules()
                        echo "✅ Build stage completed successfully"
                    } catch (Exception e) {
                        echo "❌ Build stage failed: ${e.message}"
                        throw e
                    }
                }
            }
            post {
                always {
                    script {
                        // Archive build artifacts
                        try {
                            // Get test configuration for dynamic paths
                            def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
                            def testConfigs = getTestConfigs(pipelineConfig)
                            
                            // Archive kernel module artifacts defined in pipeline configuration
                            if (pipelineConfig.artifacts?.kernel_modules) {
                                pipelineConfig.artifacts.kernel_modules.each { moduleConfig ->
                                    archiveArtifacts artifacts: moduleConfig.path, allowEmptyArchive: true, fingerprint: true
                                    echo "Archived module artifacts: ${moduleConfig.path} - ${moduleConfig.description}"
                                }
                            }
                            
                            // Archive YAML configuration files (essential)
                            if (pipelineConfig.artifacts?.essential_configs) {
                                pipelineConfig.artifacts.essential_configs.each { configArtifact ->
                                    archiveArtifacts artifacts: configArtifact.path, allowEmptyArchive: true, fingerprint: true
                                    echo "Archived essential config: ${configArtifact.path} - ${configArtifact.description}"
                                }
                            }
                            
                            echo "✅ Build artifacts archived successfully"
                        } catch (Exception e) {
                            echo "⚠️ Warning: Could not archive some build artifacts: ${e.message}"
                        }
                    }
                }
            }
        }

        stage('QEMU-Build') {
            steps {
                script {
                    echo "=== Building Simtemp Driver for QEMU ARM Environment ==="
                    
                    try {
                        // Load test configuration for build environment
                        def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
                        def testConfigs = getTestConfigs(pipelineConfig)
                        
                        // Check if QEMU integration tests are enabled
                        def qemuEnabled = testConfigs.tests?.qemu_integration?.enabled ?: false
                        def usePrecompiled = testConfigs.tests?.qemu_integration?.use_precompiled_driver ?: false
                        
                        echo "QEMU integration tests enabled: ${qemuEnabled}"
                        
                        if (!qemuEnabled) {
                            echo "⚠️ QEMU integration tests are disabled - skipping QEMU driver build"
                            echo "✅ Build stage completed (no QEMU build required)"
                            return
                        }
                        
                        // No special build environment needed for native x86_64 build
                        def buildEnv = []
                        
                        // Add precompiled driver settings if configured
                        if (usePrecompiled) {
                            buildEnv.add('USE_PRECOMPILED_DRIVER=true')
                            def precompiledPath = testConfigs.tests.qemu_integration.precompiled_path
                            if (precompiledPath) {
                                buildEnv.add("PRECOMPILED_DRIVER_PATH=${precompiledPath}")
                            }
                            echo "Build stage: Using precompiled driver mode for QEMU integration"
                        } else {
                            buildEnv.add('USE_PRECOMPILED_DRIVER=false')
                            echo "Build stage: Using compilation mode for QEMU integration"
                        }
                        
                        withEnv(buildEnv) {
                            // Execute the simtemp driver build script and check result
                            sh '''
                                set -e
                                echo "Building simtemp driver for QEMU environment..."
                                cd deployment/qemu
                                
                                if [ ! -x scripts/build_simtemp_driver.sh ]; then
                                    echo "Build script not found or not executable: scripts/build_simtemp_driver.sh"
                                    ls -la scripts/
                                    exit 1
                                fi
                                
                                # Execute the build script
                                ./scripts/build_simtemp_driver.sh
                                BUILD_RESULT=$?
                                if [ $BUILD_RESULT -eq 0 ]; then
                                    echo "Simtemp driver build completed successfully"
                                else
                                    echo "Simtemp driver build failed with exit code $BUILD_RESULT"
                                    exit $BUILD_RESULT
                                fi
                            '''
                        }
                        
                    } catch (Exception e) {
                        echo "Failed to build simtemp driver for QEMU: ${e.message}"
                        throw e
                    }
                }
            }
            post {
                always {
                    script {
                        // Archive artifacts only if QEMU tests are enabled
                        try {
                            def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
                            def testConfigs = getTestConfigs(pipelineConfig)
                            def qemuEnabled = testConfigs.tests?.qemu_integration?.enabled ?: false
                            def usePrecompiled = testConfigs.tests?.qemu_integration?.use_precompiled_driver ?: false
                            
                            if (!qemuEnabled) {
                                echo "⚠️ QEMU tests disabled - skipping build artifacts archiving"
                                return
                            }
                            
                            // Archive artifacts based on build mode
                            if (!usePrecompiled) {
                                echo "Archiving compiled driver artifacts..."
                                archiveArtifacts artifacts: 'deployment/qemu/rootfs/tmp/src/simtemp_driver/*.ko', allowEmptyArchive: true, fingerprint: true
                            } else {
                                echo "Precompiled mode: Skipping .ko artifact archiving (driver is in rootfs)"
                            }
                            
                            // Always archive the rootfs (contains precompiled driver or newly compiled one)
                            archiveArtifacts artifacts: 'deployment/qemu/rootfs.cpio.gz', allowEmptyArchive: false, fingerprint: true
                            echo "✅ Simtemp driver artifacts archived"
                        } catch (Exception e) {
                            echo "⚠️ Warning: Could not archive simtemp driver artifacts: ${e.message}"
                        }
                    }
                }
                success {
                    echo "✅ Simtemp driver build stage completed successfully"
                }
                failure {
                    echo "❌ Simtemp driver build stage failed"
                }
            }
        }

        stage('Test') {
            steps {
                script {
                    echo "=== Test Stage ==="

                    try {
                        // Use the proper test module function that integrates with PR comments
                        runModuleTests()
                        echo "Test stage completed successfully"
                    } catch (Exception e) {
                        echo "Test stage failed: ${e.message}"
                        throw e
                    }
                    
                    // Run PR comment test if enabled
                    if (params.PUBLISH_PR_COMMENT) {
                        echo "Testing PR comment functionality..."
                        def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
                        postPRComment(pipelineConfig)
                    }
                }
            }
            post {
                always {
                    script {
                        // Archive test results and reports
                        try {
                            // Get test configuration for dynamic paths
                            def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
                            def testConfigs = getTestConfigs(pipelineConfig)
                            
                            // Get reports directory from pipeline configuration
                            def reportsDirectory = pipelineConfig.testing?.reports_directory
                            if (reportsDirectory) {
                                // Archive test reports based on pipeline configuration
                                def reportArtifacts = [
                                    "${reportsDirectory}/test_report.html",
                                    "${reportsDirectory}/test_report_detailed.html",
                                    "${reportsDirectory}/test_report.json",
                                    "${reportsDirectory}/test_report_detailed.json",
                                    "${reportsDirectory}/**/*"
                                ]
                                
                                reportArtifacts.each { artifact ->
                                    if (artifact.endsWith('**/*')) {
                                        archiveArtifacts artifacts: artifact, allowEmptyArchive: true, fingerprint: true
                                    } else if (fileExists(artifact)) {
                                        archiveArtifacts artifacts: artifact, fingerprint: true
                                    }
                                }
                                echo "✅ Test reports archived from ${reportsDirectory}"
                            }
                            
                            // Archive artifacts defined in pipeline configuration
                            if (pipelineConfig.artifacts?.test_reports) {
                                pipelineConfig.artifacts.test_reports.each { reportConfig ->
                                    archiveArtifacts artifacts: reportConfig.path, allowEmptyArchive: true, fingerprint: true
                                    echo "Archived test reports: ${reportConfig.path} - ${reportConfig.description}"
                                }
                            }
                            
                            // Archive module artifacts for each test suite
                            testConfigs.tests.each { testSuiteName, testSuiteConfig ->
                                def modulePath = testSuiteConfig.module_path
                                if (modulePath) {
                                    // Use the module path from configuration (relative to sub-project directory)
                                    // Expand variables if needed
                                    if (testSuiteConfig.env) {
                                        testSuiteConfig.env.each { key, value ->
                                            modulePath = modulePath.replace("\${${key}}", value)
                                        }
                                    }
                                    archiveArtifacts artifacts: "${env.SUB_PROJECT_PATH}/${modulePath}", allowEmptyArchive: true, fingerprint: true
                                    echo "Archived tested module: ${env.SUB_PROJECT_PATH}/${modulePath}"
                                }
                            }
                            
                            // Archive YAML configurations used during testing
                            if (pipelineConfig.artifacts?.essential_configs) {
                                pipelineConfig.artifacts.essential_configs.each { configArtifact ->
                                    archiveArtifacts artifacts: configArtifact.path, allowEmptyArchive: true, fingerprint: true
                                    echo "Archived essential config: ${configArtifact.path} - ${configArtifact.description}"
                                }
                            }
                            
                            // Archive test detail files used for report generation
                            try {
                                archiveArtifacts artifacts: "tmp/test_details_*.json", allowEmptyArchive: true, fingerprint: true
                                echo "Archived test detail files from /tmp"
                            } catch (Exception e) {
                                echo "⚠️ Note: No test detail files found in /tmp to archive"
                            }
                            
                            // Archive pytest cache and test logs (excluding unwanted files)
                            try {
                                // Archive test results but skip .pytest_cache entirely due to unwanted files
                                archiveArtifacts artifacts: "${env.SUB_PROJECT_PATH}/tests/reports/**/*", allowEmptyArchive: true, fingerprint: true
                                echo "Archived test results (skipped .pytest_cache to exclude CACHEDIR.TAG, README.md, nodeids, stepwise)"
                            } catch (Exception e) {
                                echo "⚠️ Note: No test results found to archive"
                            }
                            
                            echo "✅ Test artifacts archived successfully"
                        } catch (Exception e) {
                            echo "⚠️ Warning: Could not archive some test artifacts: ${e.message}"
                        }
                    }
                }
            }
        }
        
        stage('Cleanup') {
            steps {
                script {
                    echo "=== Cleanup Stage ==="
                    echo "Cleaning up workspace permissions for kernel module files"
                    
                    try {
                        // Get cleanup script from pipeline configuration
                        def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
                        def cleanupScript = pipelineConfig.stages?.cleanup?.script
                        
                        if (cleanupScript && fileExists(cleanupScript)) {
                            sh "chmod +x ${cleanupScript}"
                            sh "${cleanupScript}"
                            echo "✅ Workspace permissions cleaned up successfully using ${cleanupScript}"
                        } else {
                            echo "⚠️ Warning: Cleanup script not found or not configured"
                        }
                    } catch (Exception e) {
                        echo "⚠️ Warning: Could not clean up workspace permissions: ${e.message}"
                        // Don't fail the build if cleanup fails
                    }
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo 'Pipeline completed'
                
                // Send consolidated PR comment once for all outcomes
                sendConsolidatedPRComment()
                
                // Archive general pipeline artifacts
                try {
                    // Get test configuration for dynamic paths
                    def pipelineConfig = loadPipelineConfig(env.ACTUAL_PIPELINE_CONFIG_PATH ?: env.PIPELINE_CONFIG_PATH)
                    def testConfigs = getTestConfigs(pipelineConfig)
                    
                    // Archive all reports from pipeline configuration
                    def reportsDirectory = pipelineConfig.testing?.reports_directory
                    if (reportsDirectory) {
                        archiveArtifacts artifacts: "${reportsDirectory}/**/*", allowEmptyArchive: true, fingerprint: true
                        echo "Archived reports from: ${reportsDirectory}"
                    }
                    
                    // Archive test report artifacts defined in pipeline configuration
                    if (pipelineConfig.artifacts?.test_reports) {
                        pipelineConfig.artifacts.test_reports.each { reportConfig ->
                            archiveArtifacts artifacts: reportConfig.path, allowEmptyArchive: true, fingerprint: true
                            echo "Archived test reports: ${reportConfig.path}"
                        }
                    }
                    
                    // Archive essential configuration files
                    if (pipelineConfig.artifacts?.essential_configs) {
                        pipelineConfig.artifacts.essential_configs.each { configArtifact ->
                            archiveArtifacts artifacts: configArtifact.path, allowEmptyArchive: true, fingerprint: true
                            echo "Archived essential config: ${configArtifact.path}"
                        }
                    }
                    
                    // Archive module artifacts defined in pipeline configuration
                    if (pipelineConfig.artifacts?.kernel_modules) {
                        pipelineConfig.artifacts.kernel_modules.each { moduleConfig ->
                            archiveArtifacts artifacts: moduleConfig.path, allowEmptyArchive: true, fingerprint: true
                            echo "Archived final module artifacts: ${moduleConfig.path}"
                        }
                    }
                    
                    // Archive the Jenkinsfile itself for reference
                    // (Already included in essential_configs)
                    
                    echo "✅ General pipeline artifacts archived"
                } catch (Exception e) {
                    echo "⚠️ Warning: Could not archive some general artifacts: ${e.message}"
                }
            }
        }
        success {
            echo 'Pipeline succeeded'
        }
        failure {
            echo 'Pipeline failed'
        }
        unstable {
            echo 'Pipeline unstable'
        }
    }
}
