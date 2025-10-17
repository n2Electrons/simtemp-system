#!/usr/bin/env groovy

/**
 * Jenkins Pipeline Diagnostic Utilities
 * 
 * This file contains utility functions for diagnosing issues in Jenkins pipelines,
 * particularly focused on GitHub API interactions and PR detection.
 * 
 * Copyright (c) Jorge Rodriguez Moreno
 */

/**
 * Print detailed diagnostic information about the current environment
 * Includes environment variables, build info, and Git details
 */
def printEnvironmentDiagnostics() {
    echo "===== ENVIRONMENT DIAGNOSTICS ====="
    echo "Date/Time: ${new Date().toString()}"
    echo "Jenkins Version: ${env.JENKINS_VERSION ?: 'Version not available'}"
    
    // Build Information
    echo "----- Build Information -----"
    echo "BUILD_NUMBER: ${env.BUILD_NUMBER}"
    echo "BUILD_URL: ${env.BUILD_URL}"
    echo "JOB_NAME: ${env.JOB_NAME}"
    echo "NODE_NAME: ${env.NODE_NAME}"
    
    // Git Information
    echo "----- Git Information -----"
    echo "BRANCH_NAME: ${env.BRANCH_NAME}"
    echo "GIT_BRANCH: ${env.GIT_BRANCH}"
    echo "GIT_COMMIT: ${env.GIT_COMMIT}"
    echo "GIT_URL: ${env.GIT_URL}"
    echo "CHANGE_ID: ${env.CHANGE_ID}"
    
    // GitHub Information
    echo "----- GitHub Information -----"
    echo "GITHUB_OWNER: ${env.GITHUB_OWNER}"
    echo "GITHUB_REPO: ${env.GITHUB_REPO}"
    
    echo "=================================="
}

/**
 * Test GitHub API connectivity and token validity
 * @param token The GitHub API token to test
 * @param owner The GitHub repository owner
 * @param repo The GitHub repository name
 * @return Boolean indicating if the connection is successful
 */
def testGitHubAPIConnectivity(String token, String owner, String repo) {
    echo "Testing GitHub API connectivity..."
    
    if (!token) {
        echo "ERROR: No GitHub token provided"
        return false
    }
    
    if (!owner || !repo) {
        echo "ERROR: Repository owner or name not provided"
        return false
    }
    
    try {
        def response = sh(
            script: """
                curl -s -o /dev/null -w "%{http_code}" \\
                -H "Authorization: token ${token}" \\
                -H "Accept: application/vnd.github.v3+json" \\
                "https://api.github.com/repos/${owner}/${repo}"
            """,
            returnStdout: true
        ).trim()
        
        echo "GitHub API Response Code: ${response}"
        
        if (response == "200") {
            echo "✅ GitHub API connectivity test passed"
            return true
        } else {
            echo "❌ GitHub API connectivity test failed with status code: ${response}"
            return false
        }
    } catch (Exception e) {
        echo "❌ GitHub API connectivity test failed with exception: ${e.message}"
        return false
    }
}

/**
 * Run comprehensive PR detection diagnostics
 * This function attempts all known methods of detecting a PR in Jenkins
 * and provides a detailed report of what was found or not found
 * @return Map with diagnostic results
 */
def runPRDetectionDiagnostics() {
    echo "========== RUNNING PR DETECTION DIAGNOSTICS =========="
    def results = [
        success: false,
        prNumber: null,
        methods: [:],
        detectionTime: new Date().toString()
    ]
    
    echo "Testing all available PR detection methods..."
    
    // Method 1: Check GitHub issue mappings file first
    results.methods.github_mappings = [success: false, value: null]
    try {
        def branch = env.BRANCH_NAME ?: (env.GIT_BRANCH ?: null)
        if (branch) {
            def mappingFile = 'simtemp/tests/config/github_issue_mappings.json'
            if (fileExists(mappingFile)) {
                def mappings = readJSON file: mappingFile
                if (mappings && mappings[branch]) {
                    def prNumber = mappings[branch].toString()
                    results.methods.github_mappings.success = true
                    results.methods.github_mappings.value = prNumber
                    echo "✅ Found PR via GitHub mappings: ${prNumber}"
                    results.prNumber = prNumber
                    results.success = true
                }
            } else {
                echo "ℹ️ GitHub mappings file not found: ${mappingFile}"
            }
        } else {
            echo "ℹ️ No branch name available for mapping lookup"
        }
    } catch (Exception e) {
        echo "ERROR checking GitHub mappings: ${e.message}"
        results.methods.github_mappings.error = e.message
    }
    
    // Method 2: Using CHANGE_ID environment variable (Jenkins pipeline standard)
    results.methods.change_id = [success: false, value: null]
    try {
        if (env.CHANGE_ID) {
            results.methods.change_id.success = true
            results.methods.change_id.value = env.CHANGE_ID
            echo "✅ Found PR via CHANGE_ID: ${env.CHANGE_ID}"
            if (!results.prNumber) {
                results.prNumber = env.CHANGE_ID
                results.success = true
            }
        } else {
            echo "ℹ️ CHANGE_ID not available (requires Jenkins GitHub Branch Source Plugin)"
        }
    } catch (Exception e) {
        echo "ERROR checking CHANGE_ID: ${e.message}"
        results.methods.change_id.error = e.message
    }
    
    // Method 3: Parse from git branch name (if it follows naming convention like PR-123)
    results.methods.branch_parse = [success: false, value: null]
    try {
        def branch = env.BRANCH_NAME ?: (env.GIT_BRANCH ?: null)
        if (branch) {
            def matcher = branch =~ /PR-(\d+)|pull\/(\d+)|pr\/(\d+)/
            if (matcher.find()) {
                def prNumber = matcher.group(1) ?: (matcher.group(2) ?: matcher.group(3))
                results.methods.branch_parse.success = true
                results.methods.branch_parse.value = prNumber
                echo "✅ Found PR via branch name parsing: ${prNumber}"
                if (!results.prNumber) {
                    results.prNumber = prNumber
                    results.success = true
                }
            }
        } else {
            echo "ℹ️ No branch name available for parsing"
        }
    } catch (Exception e) {
        echo "ERROR parsing branch name: ${e.message}"
        results.methods.branch_parse.error = e.message
    }
    
    // Method 4: Check JOB_NAME for PR indicators
    results.methods.job_name_parse = [success: false, value: null]
    try {
        if (env.JOB_NAME) {
            def matcher = env.JOB_NAME =~ /PR-(\d+)|pull\/(\d+)|pr\/(\d+)/
            if (matcher.find()) {
                def prNumber = matcher.group(1) ?: (matcher.group(2) ?: matcher.group(3))
                results.methods.job_name_parse.success = true
                results.methods.job_name_parse.value = prNumber
                echo "✅ Found PR via job name parsing: ${prNumber}"
                if (!results.prNumber) {
                    results.prNumber = prNumber
                    results.success = true
                }
            }
        } else {
            echo "ℹ️ No JOB_NAME available for parsing"
        }
    } catch (Exception e) {
        echo "ERROR parsing job name: ${e.message}"
        results.methods.job_name_parse.error = e.message
    }
    
    // Summary of PR detection
    if (results.success) {
        echo "✅✅✅ PR DETECTION SUCCESSFUL: PR #${results.prNumber} ✅✅✅"
    } else {
        echo "❌❌❌ PR DETECTION FAILED: No PR could be detected ❌❌❌"
    }
    
    // Print detailed results
    echo "======= PR DETECTION DIAGNOSTICS RESULTS ======="
    echo "Success: ${results.success}"
    echo "PR Number: ${results.prNumber ?: 'NOT FOUND'}"
    echo "Detection Methods:"
    results.methods.each { method, result ->
        echo "  ${method}: ${result.success ? '✅' : '❌'} ${result.value ?: ''}"
    }
    echo "=============================================="
    
    return results
}

// Return this file as a module
return this