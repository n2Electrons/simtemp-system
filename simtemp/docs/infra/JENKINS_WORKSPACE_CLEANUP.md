# Jenkins Workspace Cleanup - Root Permissions

This document explains the issue with Jenkins workspace cleanup when kernel modules are built and tested with root privileges.

## Problem

When the `require_root: true` flag is set in the pipeline configuration, kernel module tests run with root privileges (using sudo). This creates files owned by the root user in the following directories:

- `simtemp/kernel/obj/` - Contains compiled kernel modules and build artifacts
- `simtemp/tests/` - May contain temporary files created during testing

Since these files are owned by root and not the Jenkins user, Jenkins cannot delete them during workspace cleanup, resulting in the error:

```
ERROR: Failed to clean the workspace
```

## Solution

We've implemented a two-part solution:

1. A cleanup script (`simtemp/scripts/cleanup_permissions.sh`) that runs after tests and resets ownership of files to the Jenkins user.
2. A new `cleanup` stage in the pipeline configuration that runs this script even if tests fail.

### Cleanup Script

The cleanup script performs the following actions:

- Changes ownership of all files in the `simtemp/kernel/obj/` directory to the Jenkins user
- Makes all files readable and writable by the Jenkins user
- Handles potential root-owned files in the test directory
- Falls back to more permissive permissions if sudo is not available

### Pipeline Configuration

The pipeline configuration includes:

```yaml
stages:
  # Other stages...
  
  cleanup:
    enabled: true
    timeout_minutes: 2
    description: "Cleanup workspace permissions to allow Jenkins to clean"
    always_run: true
    script: "simtemp/scripts/cleanup_permissions.sh"
```

The `always_run: true` setting ensures this stage executes even if previous stages fail, ensuring workspace cleanup is always possible.

## Best Practices

1. Be aware that setting `require_root: true` will create root-owned files that require special handling for cleanup.
2. Always include a cleanup stage in pipelines that build kernel modules or other components requiring elevated privileges.
3. Consider using containerized builds where permission issues can be more easily managed.
4. Document the implications of root permissions in your pipeline configuration files.

## Related Configuration

The `require_root` flag in `pipeline_config.yml` indicates that tests will run with root privileges:

```yaml
kernel:
  testing:
    require_root: true   # Tests need root to load/unload kernel modules; NOTE: This creates root-owned files that need cleanup
    test_load: true      # Tests do load the kernel module
    test_unload: true    # Tests do unload the kernel module
```

This flag is used as documentation of the test requirements but should be accompanied by appropriate cleanup steps.