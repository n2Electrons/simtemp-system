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
 * Perform a detailed GitHub API request and save response for analysis
 * @param token The GitHub API token
 * @param url The complete GitHub API URL
 * @param outputFile File to save the response
 * @return The response as a string
 */
def performDetailedGitHubAPIRequest(String token, String url, String outputFile) {
    echo "Performing detailed GitHub API request to: ${url}"
    
    def response = ""
    
    try {
        response = sh(
            script: """
                curl -v -s \\
                -H "Authorization: token ${token}" \\
                -H "Accept: application/vnd.github.v3+json" \\
                "${url}"
            """,
            returnStdout: true
        ).trim()
        
        // Save response to file for analysis
        if (outputFile) {
            writeFile file: outputFile, text: response
            echo "API response saved to: ${outputFile}"
        }
        
        // Log response details
        echo "Response length: ${response.length()} characters"
        if (response.length() > 0) {
            echo "Response starts with: ${response.take(100)}..."
            echo "Response content type check: starts with '[' = ${response.trim().startsWith('[')}"
        } else {
            echo "WARNING: Empty response received"
        }
        
        return response
    } catch (Exception e) {
        echo "ERROR: API request failed: ${e.message}"
        return ""
    }
}

/**
 * Diagnose JsonSlurper availability and functionality
 * @return Boolean indicating if JsonSlurper is working
 */
def diagnoseJsonSlurper() {
    echo "Diagnosing JsonSlurper functionality..."
    
    try {
        // Test if JsonSlurper class is available
        echo "Checking if groovy.json.JsonSlurper is available"
        def slurperClass = this.class.classLoader.loadClass('groovy.json.JsonSlurper')
        echo "JsonSlurper class loaded successfully: ${slurperClass}"
        
        // Try to instantiate JsonSlurper
        def jsonSlurper = new groovy.json.JsonSlurper()
        echo "Successfully created JsonSlurper instance"
        
        // Test parsing a simple JSON string
        def testJson = '{"test": true, "value": 123}'
        def parsed = jsonSlurper.parseText(testJson)
        echo "Test parsing successful: ${parsed.test} / ${parsed.value}"
        
        return true
    } catch (Exception e) {
        echo "ERROR: JsonSlurper diagnosis failed: ${e.message}"
        echo "ERROR: Exception type: ${e.getClass().getName()}"
        echo "ERROR: Stack trace: ${e.getStackTrace().join('\n')}"
        return false
    }
}

/**
 * Find PR number for the current branch using GitHub API
 * @param token The GitHub API token
 * @param owner The GitHub repository owner
 * @param repo The GitHub repository name
 * @param branch The branch name to find PRs for
 * @return The PR number if found, null otherwise
 */
def findPRNumberForBranch(String token, String owner, String repo, String branch) {
    echo "Finding PR number for branch: ${branch}"
    
    if (!branch) {
        echo "ERROR: No branch name provided"
        return null
    }
    
    // Clean branch name (remove origin/ prefix if present)
    def cleanBranch = branch.replaceAll(/^origin\//, '')
    echo "Searching for PR with head branch: ${cleanBranch}"
    
    // First attempt: with owner prefix
    def url1 = "https://api.github.com/repos/${owner}/${repo}/pulls?state=open&head=${owner}:${cleanBranch}"
    def response1 = performDetailedGitHubAPIRequest(token, url1, "github_api_pr_response1.json")
    
    try {
        if (response1 && response1.trim().startsWith('[')) {
            def jsonSlurper = new groovy.json.JsonSlurper()
            def pulls = jsonSlurper.parseText(response1)
            
            if (pulls && pulls.size() > 0) {
                def prNumber = pulls[0].number.toString()
                echo "✅ Found PR #${prNumber} for branch '${cleanBranch}' via GitHub API (attempt 1)"
                return prNumber
            } else {
                echo "No open PRs found for branch with owner prefix"
            }
        }
    } catch (Exception e) {
        echo "ERROR: Failed to parse PR response 1: ${e.message}"
    }
    
    // Second attempt: without owner prefix
    def url2 = "https://api.github.com/repos/${owner}/${repo}/pulls?state=open&head=${cleanBranch}"
    def response2 = performDetailedGitHubAPIRequest(token, url2, "github_api_pr_response2.json")
    
    try {
        if (response2 && response2.trim().startsWith('[')) {
            def jsonSlurper = new groovy.json.JsonSlurper()
            def pulls = jsonSlurper.parseText(response2)
            
            if (pulls && pulls.size() > 0) {
                def prNumber = pulls[0].number.toString()
                echo "✅ Found PR #${prNumber} for branch '${cleanBranch}' via GitHub API (attempt 2)"
                return prNumber
            } else {
                echo "No open PRs found for branch without owner prefix"
            }
        }
    } catch (Exception e) {
        echo "ERROR: Failed to parse PR response 2: ${e.message}"
    }
    
    // Third attempt: get all PRs and filter
    def url3 = "https://api.github.com/repos/${owner}/${repo}/pulls?state=open"
    def response3 = performDetailedGitHubAPIRequest(token, url3, "github_api_all_prs_response.json")
    
    try {
        if (response3 && response3.trim().startsWith('[')) {
            def jsonSlurper = new groovy.json.JsonSlurper()
            def pulls = jsonSlurper.parseText(response3)
            echo "Found ${pulls.size()} open PRs in total"
            
            // Process each PR to find our branch
            for (def pull in pulls) {
                echo "PR #${pull.number}: branch '${pull.head.ref}'"
                if (pull.head.ref == cleanBranch) {
                    def prNumber = pull.number.toString()
                    echo "✅ Matched PR #${prNumber} with branch '${cleanBranch}'"
                    return prNumber
                }
            }
        }
    } catch (Exception e) {
        echo "ERROR: Failed to parse all PRs response: ${e.message}"
    }
    
    return null
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
                echo "❌ GitHub mappings file not found: ${mappingFile}"
            }
        } else {
            echo "❌ No branch name available for mapping lookup"
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
            results.prNumber = env.CHANGE_ID
            results.success = true
        } else {
            echo "ℹ️ CHANGE_ID not available (requires Jenkins GitHub Branch Source Plugin)"
        }
    } catch (Exception e) {
        echo "ERROR checking CHANGE_ID: ${e.message}"
        results.methods.change_id.error = e.message
    }
    
    // Method 3: Using GITHUB_PR_NUMBER environment variable (commonly set by GitHub plugins)
    results.methods.github_pr_number = [success: false, value: null]
    try {
        if (env.GITHUB_PR_NUMBER) {
            results.methods.github_pr_number.success = true
            results.methods.github_pr_number.value = env.GITHUB_PR_NUMBER
            echo "✅ Found PR via GITHUB_PR_NUMBER: ${env.GITHUB_PR_NUMBER}"
            if (!results.prNumber) {
                results.prNumber = env.GITHUB_PR_NUMBER
                results.success = true
            }
        } else {
            echo "ℹ️ GITHUB_PR_NUMBER not available (requires GitHub Actions or specific plugins)"
        }
    } catch (Exception e) {
        echo "ERROR checking GITHUB_PR_NUMBER: ${e.message}"
        results.methods.github_pr_number.error = e.message
    }
    
    // Method 4: Using GitHub API to find PR for branch
    results.methods.github_api = [success: false, value: null]
    try {
        def owner = env.GITHUB_OWNER ?: (env.REPO_OWNER ?: null)
        def repo = env.GITHUB_REPO ?: (env.REPO_NAME ?: null)
        def token = env.GITHUB_TOKEN ?: (env.GIT_TOKEN ?: null)
        def branch = env.BRANCH_NAME ?: (env.GIT_BRANCH ?: null)
        
        if (owner && repo && token && branch) {
            def prNumber = findPRNumberForBranch(token, owner, repo, branch)
            if (prNumber) {
                results.methods.github_api.success = true
                results.methods.github_api.value = prNumber
                echo "✅ Found PR via GitHub API: ${prNumber}"
                if (!results.prNumber) {
                    results.prNumber = prNumber
                    results.success = true
                }
            } else {
                echo "❌ Failed to find PR via GitHub API"
            }
        } else {
            echo "❌ Missing required parameters for GitHub API PR detection"
            def missingParams = []
            if (!owner) missingParams.add("GITHUB_OWNER")
            if (!repo) missingParams.add("GITHUB_REPO") 
            if (!token) missingParams.add("GITHUB_TOKEN")
            if (!branch) missingParams.add("BRANCH_NAME/GIT_BRANCH")
            
            echo "Missing parameters: ${missingParams.join(', ')}"
            echo "Available values:"
            echo "  GITHUB_OWNER: ${owner ?: 'NOT SET'}"
            echo "  GITHUB_REPO: ${repo ?: 'NOT SET'}"
            echo "  GITHUB_TOKEN: ${token ? 'SET (length: ' + token.length() + ')' : 'NOT SET'}"
            echo "  BRANCH_NAME: ${branch ?: 'NOT SET'}"
            
            results.methods.github_api.missing_params = [
                owner: !owner,
                repo: !repo,
                token: !token,
                branch: !branch
            ]
        }
    } catch (Exception e) {
        echo "ERROR checking via GitHub API: ${e.message}"
        results.methods.github_api.error = e.message
    }
    
    // Method 5: Parse from git branch name (if it follows naming convention like PR-123)
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
            echo "❌ No branch name available for parsing"
        }
    } catch (Exception e) {
        echo "ERROR parsing branch name: ${e.message}"
        results.methods.branch_parse.error = e.message
    }
    
    // Method 6: Check JOB_NAME for PR indicators
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
            echo "❌ No JOB_NAME available for parsing"
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