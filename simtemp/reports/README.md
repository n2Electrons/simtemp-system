# Traceability Reports Directory

This directory contains comprehensive traceability reports generated from the TESTPLAN.md and GitHub integration.

## Report Files

### Core Traceability Data
- **`traceability.yml`** - Main traceability YAML file with requirements, test cases, and GitHub links
- **`traceability.yml.backup`** - Backup of previous traceability YAML file

### Visual Reports
- **`traceability_view_report.html`** - Interactive HTML tree view with expandable requirements and test cases
- **`traceability_report.mmd`** - Mermaid diagram source for flowchart visualization
- **`traceability_report.json`** - JSON export suitable for Grafana dashboards
- **`traceability_report.yml`** - Normalized YAML export of processed data

### Progress Tracking
- **`progress_report.txt`** - Current progress status of requirements and test cases

## Generation Commands

To regenerate these reports:

```bash
# Generate visual traceability reports
python3 examples/kernel_module/scripts/generate_traceability_view.py --out-dir examples/kernel_module/reports

# Update traceability YAML with GitHub links
python3 examples/kernel_module/scripts/generate_traceability_yaml.py --github-repo n2Electrons/n2Electrons-Infra

# Generate progress report
python3 examples/kernel_module/scripts/show_progress.py > examples/kernel_module/reports/progress_report.txt
```

## Report Statistics

Based on current traceability data (accurate as of the last report generation date; see "Generated on" below):
- **Total Requirements**: 34 (24 Functional + 10 Non-Functional)
- **Total Test Cases**: 74
- **GitHub Issues Linked**: 7 (requirements and test cases)
- **Automation Coverage**: High (most test cases automated except documentation and GUI)

## Report Usage

- **HTML Report**: Open `traceability_view_report.html` in a browser for interactive exploration
- **Mermaid Diagram**: Use `traceability_report.mmd` with Mermaid tools or GitHub markdown
- **JSON Data**: Import `traceability_report.json` into Grafana or other dashboarding tools
- **YAML Data**: Use normalized YAML for automation scripts and CI/CD pipelines

## GitHub Integration

The reports include GitHub issue links for:
- F-K1 → [Issue #58](https://github.com/n2Electrons/n2Electrons-Infra/issues/58)
- F-K1-TC-001 → [Issue #61](https://github.com/n2Electrons/n2Electrons-Infra/issues/61)
- F-K1-TC-002 → [Issue #62](https://github.com/n2Electrons/n2Electrons-Infra/issues/62)
- F-D2 → [Issue #63](https://github.com/n2Electrons/n2Electrons-Infra/issues/63)
- F-D2-TC-001 → [Issue #64](https://github.com/n2Electrons/n2Electrons-Infra/issues/64)
- F-D2-TC-002 → [Issue #65](https://github.com/n2Electrons/n2Electrons-Infra/issues/65)
- F-D4 → [Issue #59](https://github.com/n2Electrons/n2Electrons-Infra/issues/59)

---
*Generated on: October 8, 2025*
*Branch: f-d4-tc-prompts-recorded*