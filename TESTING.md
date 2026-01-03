# Testing Guide for vinput

## Overview

vinput has comprehensive unit tests that validate all components without requiring actual hardware (audio devices, uinput, NPU).

## ⚠️ Important: Isolated Test Environment

**DO NOT run tests directly in your native Python environment!**

The test dependencies in `requirements-dev.txt` may conflict with the strictly pinned runtime versions in `requirements.txt`. Version mismatches can cause:
- IOMMU faults on Strix Halo hardware
- Audio buffer underruns
- Virtual controller failures

## Safe Testing Methods

### Method 1: Container-Based Testing (Recommended)

Run tests in an isolated container environment:

```bash
# Run all tests
podman-compose run --rm vinput-test

# Run specific test file
podman-compose run --rm vinput-test pytest tests/test_audio_engine.py

# Run with coverage
podman-compose run --rm vinput-test pytest --cov=src --cov-report=html

# Run verbose
podman-compose run --rm vinput-test pytest -vv
```

### Method 2: Isolated Virtual Environment

If you must test natively, create a separate test virtualenv:

```bash
# Create test-specific virtualenv
python -m venv .venv-test
source .venv-test/bin/activate

# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Deactivate when done
deactivate
```

**Never activate `.venv-test` in the same session as your production `.venv`!**

## Test Structure

```
tests/
├── __init__.py              # Test package
├── conftest.py              # Shared fixtures and mocks
├── test_audio_engine.py     # Audio capture & VAD tests (13 tests)
├── test_input_engine.py     # Virtual controller tests (20 tests)
├── test_inference_engine.py # NPU inference tests (13 tests)
└── test_main.py             # Orchestrator tests (16 tests)
```

## Running Specific Tests

```bash
# Run tests for specific module
podman-compose run --rm vinput-test pytest tests/test_audio_engine.py

# Run specific test class
podman-compose run --rm vinput-test pytest tests/test_audio_engine.py::TestAudioEngine

# Run specific test method
podman-compose run --rm vinput-test pytest tests/test_audio_engine.py::TestAudioEngine::test_initialization

# Run tests matching pattern
podman-compose run --rm vinput-test pytest -k "button"
```

## Test Markers

```bash
# Run only fast tests (exclude slow integration tests)
podman-compose run --rm vinput-test pytest -m "not slow"

# Run only integration tests
podman-compose run --rm vinput-test pytest -m integration

# Skip hardware-dependent tests
podman-compose run --rm vinput-test pytest -m "not hardware"
```

## Coverage Reports

```bash
# Generate HTML coverage report
podman-compose run --rm vinput-test pytest --cov=src --cov-report=html

# View coverage (open htmlcov/index.html in browser)
firefox htmlcov/index.html
```

## Continuous Integration

For CI/CD pipelines, use container-based testing:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    podman-compose run --rm vinput-test pytest --cov=src --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Troubleshooting

### Import Errors

If you see import errors, ensure you're running tests from the project root:

```bash
cd /path/to/vinput
podman-compose run --rm vinput-test
```

### Mock Failures

If tests fail due to missing mocks, check [tests/conftest.py](tests/conftest.py) has proper fixtures.

### Version Conflicts

If you accidentally installed test dependencies in your production environment:

```bash
# Recreate clean production environment
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Test Development

When adding new tests:

1. Add fixtures to `tests/conftest.py` if reusable
2. Mock all hardware dependencies (sounddevice, evdev, onnxruntime)
3. Use `@pytest.mark.asyncio` for async tests
4. Add appropriate markers (`@pytest.mark.slow`, `@pytest.mark.integration`)

Example:

```python
import pytest
from unittest.mock import patch

class TestNewFeature:
    @pytest.mark.asyncio
    async def test_new_function(self, mock_uinput):
        """Test description."""
        # Your test code here
        assert True
```

## Why Container Testing?

1. **Version Isolation**: Test dependencies don't pollute production environment
2. **Reproducibility**: Same test environment on all machines
3. **Hardware Independence**: Tests run without audio devices, NPU, or uinput
4. **Safety**: Prevents accidental hardware failures from version mismatches

Remember: The pinned versions in `requirements.txt` are **critical** for Strix Halo hardware. Don't compromise version control for testing convenience.
