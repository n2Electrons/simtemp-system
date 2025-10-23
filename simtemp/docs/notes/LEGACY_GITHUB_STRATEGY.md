# Legacy vs Current GitHub Links Management Strategy

## Context

The **simtemp** project development moved from `n2Electrons/n2Electrons-Infra` to `n2Electrons/simtemp-system`. This means we have:

- **Legacy Issues** (57-65): Created in `n2Electrons/n2Electrons-Infra` before migration
- **Current Issues** (66+): Created in `n2Electrons/simtemp-system` after migration

## Implemented Configuration

### 1. Pipeline Configuration (`pipeline_config.yml`)

```yaml
# Repository configuration for multi-repo support
repository:
  # Repository where the current PR is located (for PR comments)
  pr_target: "simtemp-system"
  # Current development repository
  current_repo: "https://github.com/n2Electrons/simtemp-system"
  # Legacy repository for historical issues/PRs (before migration)
  legacy_repo: "https://github.com/n2Electrons/n2Electrons-Infra"
  
  # Repository mapping for different issue ranges
  issue_mapping:
    # Legacy issues (created before migration to simtemp-system)
    legacy:
      repository: "https://github.com/n2Electrons/n2Electrons-Infra"
      issue_range: [57, 65]  # Issues 57-65 are in the legacy repo
    # Current issues (created after migration)
    current:
      repository: "https://github.com/n2Electrons/simtemp-system"
      issue_range: [66, 999]  # Future issues will be in simtemp-system
```

### 2. Issue Mapping by Range

| Issue Range | Repository | Usage |
|-------------|------------|-------|
| 57-65 | `n2Electrons/n2Electrons-Infra` | Legacy issues (pre-migration) |
| 66+ | `n2Electrons/simtemp-system` | Current issues (post-migration) |

### 3. Current Links in Traceability

The following issues correctly point to the **legacy** repository (`n2Electrons-Infra`):

- **F-K1**: https://github.com/n2Electrons/n2Electrons-Infra/issues/58
- **F-K1-TC-001**: https://github.com/n2Electrons/n2Electrons-Infra/issues/61 ✅
- **F-K1-TC-002**: https://github.com/n2Electrons/n2Electrons-Infra/issues/62
- **F-D2-TC-001**: https://github.com/n2Electrons/n2Electrons-Infra/issues/64
- **F-D2-TC-002**: https://github.com/n2Electrons/n2Electrons-Infra/issues/65
- **F-D4**: https://github.com/n2Electrons/n2Electrons-Infra/issues/57
- **F-D4-TC-001**: https://github.com/n2Electrons/n2Electrons-Infra/issues/59

## Management Tools

### Automated Script: `fix_github_links.py`

The script has been updated to automatically handle legacy vs current mapping:

```bash
# Basic usage (applies automatic mapping)
python simtemp/scripts/traceability/fix_github_links.py

# With custom repositories
python simtemp/scripts/traceability/fix_github_links.py \
  --current-repo n2Electrons/simtemp-system \
  --legacy-repo n2Electrons/n2Electrons-Infra

# Show changes only (dry-run)
python simtemp/scripts/traceability/fix_github_links.py --dry-run
```

### Script Features

1. **Automatic Mapping**: Automatically determines which repository to use based on issue number
2. **Configurable Ranges**: Ranges are defined as easily modifiable constants
3. **Validation**: Only fixes links pointing to incorrect repositories (like `challenge_2509`)
4. **Automatic Backup**: Creates backups before making changes

## Benefits of this Strategy

1. **Historical Accuracy**: Legacy links maintain their original context
2. **Continuous Access**: Legacy issues remain accessible at their original location
3. **Migration Clarity**: Clear separation between pre and post migration
4. **Automation**: Script handles mapping automatically
5. **Flexibility**: Easy to adjust ranges or repositories in the future

## Verification

The HTML report (`traceability_view_report.html`) now shows:

- **F-K1-TC-001** with link to: `https://github.com/n2Electrons/n2Electrons-Infra/issues/61` ✅
- 🔗 icon pointing to the correct repository according to issue range
- Consistency across all issues in the same range

## Next Steps

1. **New Issues**: Create in `simtemp-system` (number 66+)
2. **Legacy References**: Maintain access to `n2Electrons-Infra` for consultation
3. **Documentation**: Update README to explain dual structure
4. **Monitoring**: Periodically verify that links work correctly

This strategy ensures project continuity while respecting development history and facilitating the transition to the new main repository.