# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-12-30

### Added
- Initial release of Simple Usage Monitor
- Real-time token and cost tracking for Claude Code CLI
- Support for Claude Sonnet 4.5, Opus 4.5, and Haiku 4.5
- Tiered pricing calculation for high-volume usage
- Cache token tracking (read and write tokens)
- 5-hour session window tracking matching Claude's limits
- Plan-based limits support (Pro, Max 5, Max 20)
- Terminal overlay showing live usage metrics
- Session reset countdown timer
- Command-line arguments: `--plan`, `--path`, `--version`
- Auto-detection of Claude Code installation
- Privacy-first local processing (no external API calls)
- Comprehensive test suite with 92% coverage (134 tests)
- PyPI package distribution

### Features
- **Session Management**
  - Automatic session boundary detection
  - Support for multiple concurrent sessions
  - Session expiry tracking
  - Deduplication of log entries

- **Cost Tracking**
  - Accurate cost calculation with current pricing
  - Tiered pricing for Sonnet 4.5
  - Flat pricing for Opus 4.5 and Haiku 4.5
  - Cache token cost calculation

- **Terminal UI**
  - Non-intrusive bottom overlay
  - Real-time updates
  - Clean, readable format
  - Responsive to terminal size changes

### Documentation
- Comprehensive README with usage examples
- Contributing guidelines
- Code of Conduct
- MIT License
- Issue templates for bugs and feature requests

### Technical Details
- Python 3.8+ support
- Dependencies: pexpect
- Built with setuptools
- Type hints throughout codebase
- Dataclass-based models

---

## Release Notes Template

For future releases, use this template:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed in future versions

### Removed
- Features that have been removed

### Fixed
- Bug fixes

### Security
- Security-related changes
```

---

[Unreleased]: https://github.com/SrivathsanSivakumar/simple-usage-monitor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SrivathsanSivakumar/simple-usage-monitor/releases/tag/v0.1.0
