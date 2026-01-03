#!/bin/bash
# Verify container isolation for version management
# Run this to ensure container isn't using host Python packages

set -e

echo "==================================================================="
echo "           CONTAINER ISOLATION VERIFICATION"
echo "==================================================================="
echo ""

echo "1. Checking if container is running..."
if ! podman ps | grep -q vinput-dev; then
    echo "   ⚠ Container not running. Starting..."
    podman-compose up -d
    sleep 3
fi
echo "   ✓ Container is running"
echo ""

echo "2. Verifying Python executable path..."
PYTHON_PATH=$(podman-compose exec vinput which python)
echo "   Path: $PYTHON_PATH"
if [[ "$PYTHON_PATH" == *".venv"* ]]; then
    echo "   ✓ Using container virtualenv"
else
    echo "   ✗ WARNING: Not using container virtualenv!"
    exit 1
fi
echo ""

echo "3. Checking pinned versions in container..."
echo ""
podman-compose exec vinput python -c "
import sys
print('Python version:', sys.version)
print('')

packages = {
    'numpy': '1.24.3',
    'sounddevice': '0.4.6',
    'webrtcvad': '2.0.10',
    'evdev': '1.5.0',
    'scipy': '1.10.1',
    'pyyaml': '6.0.1',
}

all_match = True
for pkg, expected in packages.items():
    try:
        mod = __import__(pkg.replace('-', '_'))
        actual = getattr(mod, '__version__', 'unknown')
        status = '✓' if actual == expected else '✗'
        print(f'{status} {pkg:15s} Expected: {expected:8s} Actual: {actual:8s}')
        if actual != expected:
            all_match = False
    except ImportError:
        print(f'✗ {pkg:15s} NOT INSTALLED')
        all_match = False

print('')
if all_match:
    print('✓ All versions match requirements.txt')
    sys.exit(0)
else:
    print('✗ Version mismatches detected!')
    print('Rebuild container: podman-compose build --no-cache')
    sys.exit(1)
"

RESULT=$?
echo ""

if [ $RESULT -eq 0 ]; then
    echo "4. Running full test suite in container..."
    echo ""
    podman-compose exec vinput python test_installation.py
    TEST_RESULT=$?
    
    echo ""
    echo "==================================================================="
    if [ $TEST_RESULT -eq 0 ]; then
        echo "✓✓✓ CONTAINER ISOLATION VERIFIED ✓✓✓"
        echo ""
        echo "Container is using correct pinned versions."
        echo "Tests passed in isolated environment."
        echo "Safe to run: podman-compose exec vinput python src/main.py"
    else
        echo "✗ Tests failed in container"
        echo "Check test output above for details"
    fi
    echo "==================================================================="
    exit $TEST_RESULT
else
    echo "==================================================================="
    echo "✗ Container version isolation FAILED"
    echo ""
    echo "Rebuild with: podman-compose build --no-cache"
    echo "==================================================================="
    exit 1
fi
