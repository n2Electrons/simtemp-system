# TESTPLAN.md

## 1. Objective
This document defines the **test plan** for the *NXP Systems Software Engineer Challenge* implementation.  
It covers the **verification and validation** of all **functional** and **non-functional** requirements defined in the *Requirements Analysis Document (RAD)* using a **Test-Driven Development (TDD)** methodology.

---

## 2. Methodology

### 2.1 Test-Driven Development (TDD)
Development follows an incremental **TDD cycle**:
1. **Write a test** based on a defined requirement and expected behavior.  
2. **Run the test** (it fails initially).  
3. **Implement the code** to make the test pass.  
4. **Refactor** for clarity and maintainability.  

Kernel and user-space tests are automated whenever possible:
- **Kernel space:** KUnit, kselftest, pytest harness for integration.  
- **User space:** pytest or gtest for CLI logic; shell tests for integration.  
- **Continuous Integration (CI):** Jenkins or GitHub Actions execute test suites automatically.

Each test case in this document is directly linked to a **requirement ID**, ensuring measurable verification of every design goal.

---

### 2.2 Strategy for Traceability
Traceability ensures that **every requirement** is covered by **at least one test case** and **every test case** corresponds to an implementation artifact.

| Level | Linkage |
|-------|----------|
| Requirement → Test Case | Unique Requirement ID (`F-K#`, `N-F#`, etc.) mapped to one or more test cases. |
| Test Case → Code | Each test refers to a specific function, module, or command validated. |
| Code → Commit | Each feature commit references the Requirement ID and Test Case ID in its message. |

A **traceability matrix** (below) is automatically validated during CI builds to confirm full coverage.

---

### 2.3 Test Case Definition
Each test case follows a consistent structure:

| Field | Description |
|--------|-------------|
| **Requirement ID** | Link to the originating requirement. |
| **Module / Sub-module** | Area of the code affected. |
| **Description** | Purpose and scope of the test. |
| **Test Case ID** | Unique identifier (e.g., `F-K4-TC-002`). |
| **Expected Result** | Pass criteria: measurable success condition. |

**Prefixes:**
- **F-K#** → Functional / Kernel  
- **F-U#** → Functional / User Space  
- **F-S#** → Functional / Scripts  
- **F-D#** → Functional / Documentation  
- **N-F#** → Non-Functional requirements

---

## 3. Test Plan Summary
All tests are executed after each milestone (M0–M10) in the development roadmap.  
- Kernel tests: via KUnit and pytest integration.  
- User tests: via pytest or run_demo.sh.  
- Documentation and script checks: via lint and CI validation.  
## 4. Test Cases and Traceability Table

| **#** | **Requirement ID** | **Module / Sub-module** | **Description** | **Test Cases (ID → Expected Result)** |
|:--:|:--:|:--|:--|:--|
| **1–2** | F-K1 | Kernel / Driver core | Register as platform driver via DT or local device. | • **F-K1-TC-001** → `insmod` registers driver; sysfs entries created.<br>• **F-K1-TC-002** → DT overlay binds driver; properties parsed with no errors. |
| **3–4** | F-K2 | Kernel / Sampler | Generate periodic samples every N ms. | • **F-K2-TC-001** → Sampling jitter ≤ ±10 %.<br>• **F-K2-TC-002** → Updating `sampling_ms` changes rate ≤ 2 periods. |
| **5–7** | F-K3 | Kernel / Char device | Expose `/dev/simtemp` binary records. | • **F-K3-TC-001** → Node exists with correct permissions.<br>• **F-K3-TC-002** → `read()` returns full struct.<br>• **F-K3-TC-003** → Non-blocking read returns `-EAGAIN`. |
| **8–10** | F-K4 | Kernel / I/O | Support blocking read and poll/epoll. | • **F-K4-TC-001** → `read()` blocks until next sample.<br>• **F-K4-TC-002** → `poll()` signals `POLLIN`.<br>• **F-K4-TC-003** → `poll()` wakes on threshold event. |
| **11–12** | F-K5 | Kernel / Alert logic | Raise alert flag when threshold exceeded. | • **F-K5-TC-001** → Alert within ≤ 2 periods; `stats.alerts++`.<br>• **F-K5-TC-002** → No alert when threshold > value. |
| **13–16** | F-K6 | Kernel / Sysfs interface | Provide attributes for config and stats. | • **F-K6-TC-001** → `sampling_ms` validates range.<br>• **F-K6-TC-002** → `threshold_mC` affects alerts.<br>• **F-K6-TC-003** → `mode` accepts valid enums.<br>• **F-K6-TC-004** → `stats` read-only and consistent. |
| **17–18** | F-K7 | Kernel / Config handler | Apply configuration atomically via sysfs/ioctl. | • **F-K7-TC-001** → Readers never see partial values.<br>• **F-K7-TC-002** → Ioctl applies all-or-nothing update. |
| **19–20** | F-K8 | Kernel / Lifecycle mgmt | Clean load/unload sequence. | • **F-K8-TC-001** → Load/unload no WARN/OOPS.<br>• **F-K8-TC-002** → Readers exit gracefully on unload. |
| **21–22** | F-K9 | Kernel / DT parser | Parse DT properties and apply defaults. | • **F-K9-TC-001** → DT props appear in sysfs.<br>• **F-K9-TC-002** → Defaults used when DT missing. |
| **23–25** | F-U1 | User space / CLI config | CLI configures sampling, threshold, and mode. | • **F-U1-TC-001** → `--set sampling_ms=50` updates sysfs.<br>• **F-U1-TC-002** → Invalid input rejected.<br>• **F-U1-TC-003** → Mode persists. |
| **26–28** | F-U2 | User space / CLI read loop | Read and display temperature samples. | • **F-U2-TC-001** → Record parsed correctly.<br>• **F-U2-TC-002** → 100 Hz 5 s → no errors.<br>• **F-U2-TC-003** → Alert printed on threshold cross. |
| **29–31** | F-U3 | User space / Event monitor | Poll/epoll for events. | • **F-U3-TC-001** → Poll triggers per sample.<br>• **F-U3-TC-002** → Poll wakes on alert ≤ 2 periods.<br>• **F-U3-TC-003** → Non-blocking returns immediately. |
| **32–33** | F-U4 | User space / Self-test mode | CLI validates alert detection. | • **F-U4-TC-001** → Self-test PASS (≤ 2 periods).<br>• **F-U4-TC-002** → High threshold → FAIL (exit ≠ 0). |
| **34–35** | F-U5 | User space / GUI | Visualize readings and live control. | • **F-U5-TC-001** → GUI updates ≥ 5 Hz.<br>• **F-U5-TC-002** → Parameter edits reflected in sysfs. |
| **36–38** | F-S1 | Scripts / build.sh | Automate kernel + CLI build. | • **F-S1-TC-001** → Build succeeds; artifacts present.<br>• **F-S1-TC-002** → Missing headers → clear error.<br>• **F-S1-TC-003** → Re-run idempotent. |
| **39–41** | F-S2 | Scripts / run_demo.sh | Automate demo pipeline. | • **F-S2-TC-001** → Demo runs OK; exit 0.<br>• **F-S2-TC-002** → Error → exit ≠ 0.<br>• **F-S2-TC-003** → Cleanup on failure. |
| **42–43** | F-S3 | Scripts / lint.sh | Lint and style verification. | • **F-S3-TC-001** → Clean run → return 0.<br>• **F-S3-TC-002** → Missing tools → graceful skip. |
| **44–45** | F-D1 | Docs / README.md | Build/run/demo guide. | • **F-D1-TC-001** → Fresh VM → success.<br>• **F-D1-TC-002** → Links valid. |
| **46–47** | F-D2 | Docs / DESIGN.md | Architecture & API. | • **F-D2-TC-001** → Struct/API match code.<br>• **F-D2-TC-002** → Locking rationale consistent. |
| **48–49** | F-D3 | Docs / TESTPLAN.md | Test coverage matrix. | • **F-D3-TC-001** → All reqs mapped.<br>• **F-D3-TC-002** → Commands + criteria documented. |
| **50–51** | F-D4 | Docs / AI_NOTES.md | Prompts and validation notes. | • **F-D4-TC-001** → Prompts recorded.<br>• **F-D4-TC-002** → Mitigations listed. |
| **52–53** | F-D5 | Docs / Git history | Repository structure. | • **F-D5-TC-001** → Tag v1.0 exists; Signed-off-by used.<br>• **F-D5-TC-002** → No binaries tracked. |
| **54–56** | N-F1 | Non-Functional / Performance | Operate ≤ 100 Hz with low latency. | • **N-F1-TC-001** → Sampling stable ±10 %.<br>• **N-F1-TC-002** → p95 latency < 10 ms.<br>• **N-F1-TC-003** → CPU usage < 5 %. |
| **57–58** | N-F2 | Non-Functional / Reliability | No kernel warnings/leaks. | • **N-F2-TC-001** → 200 load/unload → 0 WARN/OOPS.<br>• **N-F2-TC-002** → 6 h run → no leaks/crash. |
| **59–60** | N-F3 | Non-Functional / Concurrency | Thread-safe multi-access. | • **N-F3-TC-001** → 8 threads → no deadlock.<br>• **N-F3-TC-002** → Concurrent sysfs writes stable. |
| **61–62** | N-F4 | Non-Functional / Portability | Build/run on Ubuntu + ARM. | • **N-F4-TC-001** → Host build passes.<br>• **N-F4-TC-002** → ARM run in QEMU. |
| **63–64** | N-F5 | Non-Functional / Security | Input validation and permissions. | • **N-F5-TC-001** → Invalid sysfs → `-EINVAL`.<br>• **N-F5-TC-002** → Root-only RW verified. |
| **65–66** | N-F6 | Non-Functional / Maintainability | Code style & modularity. | • **N-F6-TC-001** → `checkpatch` 0 errors.<br>• **N-F6-TC-002** → Modules isolated; no symbol leak. |
| **67–68** | N-F7 | Non-Functional / Usability | CLI clarity & error handling. | • **N-F7-TC-001** → `--help` complete.<br>• **N-F7-TC-002** → Device removal error handled. |
| **69–70** | N-F8 | Non-Functional / Traceability | Req ↔ Test ↔ Code mapping. | • **N-F8-TC-001** → 1:1 mapping verified.<br>• **N-F8-TC-002** → Auto coverage 100 %. |
| **71–72** | N-F9 | Non-Functional / Compliance | Kernel coding style adherence. | • **N-F9-TC-001** → `checkpatch --strict` 0 errors, ≤ 3 warnings.<br>• **N-F9-TC-002** → `clang-format --dry-run` no diff. |
| **73–74** | N-F10 | Non-Functional / Documentation Quality | Consistency and reproducibility. | • **N-F10-TC-001** → Fresh VM → README success.<br>• **N-F10-TC-002** → Versions match environment. |

---

**Total test cases:** 74

All functional and non-functional requirements are uniquely identified and fully covered.

---

## 5. Execution Plan

| **Phase** | **Scope** | **Tools** | **Responsibility** |
|------------|------------|------------|---------------------|
| **Unit Testing** | KUnit, Python unittest for CLI | KUnit / pytest | Developer |
| **Integration Testing** | Kernel ↔ User-space interface | pytest + shell scripts | Developer |
| **System Testing** | Full run via `run_demo.sh` | Jenkins CI | CI pipeline |
| **Regression Testing** | Weekly automated run | GitHub Actions | CI pipeline |
| **Documentation Validation** | Lint, spelling, reproducibility | markdownlint, shell script | Reviewer |

---

## 6. Exit Criteria
- 100 % of requirements mapped to ≥ 1 test.  
- 100 % of tests pass on reference platform (Ubuntu LTS).  
- Kernel module unloads cleanly without leaks or warnings.  
- CI pipeline passes with zero errors or style violations.  

---

## 7. References
- [Linux Kernel Documentation: KUnit](https://www.kernel.org/doc/html/latest/dev-tools/kunit/index.html)  
- [pytest Documentation](https://docs.pytest.org/)  
- [Linux Kernel Coding Style Guide](https://www.kernel.org/doc/html/latest/process/coding-style.html)
