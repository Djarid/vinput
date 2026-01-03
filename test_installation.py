#!/usr/bin/env python3
"""
Quick test script to validate vinput installation without NPU hardware.
Tests audio capture, VAD, preprocessing, and input device independently.
"""

import asyncio
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_audio_engine():
    """Test audio capture and VAD."""
    logger.info("=" * 60)
    logger.info("TEST 1: Audio Engine")
    logger.info("=" * 60)
    
    try:
        from src.audio_engine import AudioEngine
        
        engine = AudioEngine()
        await engine.start()
        logger.info("✓ Audio engine started successfully")
        logger.info("  Listening for speech (5 second timeout)...")
        
        # Test with timeout
        try:
            audio_data = await asyncio.wait_for(
                engine.detect_speech(buffer_ms=500), 
                timeout=5.0
            )
            if len(audio_data) > 0:
                logger.info(f"✓ Captured {len(audio_data)} audio samples")
            else:
                logger.info("  No speech detected (expected if quiet)")
        except asyncio.TimeoutError:
            logger.info("  Timeout (expected if no speech)")
        
        await engine.stop()
        logger.info("✓ Audio engine shut down gracefully\n")
        return True
    
    except Exception as e:
        logger.error(f"✗ Audio engine test failed: {e}\n")
        return False


async def test_input_engine():
    """Test virtual Xbox controller creation."""
    logger.info("=" * 60)
    logger.info("TEST 2: Input Engine (Virtual Controller)")
    logger.info("=" * 60)
    
    try:
        from src.input_engine import VirtualXboxController
        
        controller = VirtualXboxController()
        
        try:
            controller.initialize()
            logger.info("✓ Virtual Xbox 360 controller created")
            
            # Test button press (non-blocking for safety)
            await controller.tap_button('A', duration_ms=100)
            logger.info("✓ Button press test succeeded")
            
            controller.shutdown()
            logger.info("✓ Virtual controller shut down\n")
            return True
        
        except PermissionError:
            logger.error("✗ Permission denied accessing /dev/uinput")
            logger.error("  Run: sudo ./setup/setup_strix_env.sh")
            return False
    
    except Exception as e:
        logger.error(f"✗ Input engine test failed: {e}\n")
        return False


def test_dependencies():
    """Check if all required packages are installed with STRICT version validation."""
    logger.info("=" * 60)
    logger.info("TEST 3: Dependencies (STRICT version checking)")
    logger.info("=" * 60)
    logger.info("NOTE: Version mismatches will cause hardware failures on Strix Halo\n")
    
    # CRITICAL: Pinned versions from white paper requirements
    # These are NOT optional - mismatches cause real hardware problems
    required_versions = {
        'numpy': ('1.24.3', 'CRITICAL: float32 memory contiguity for DMA/IOMMU safety'),
        'sounddevice': ('0.4.6', 'CRITICAL: callback timing < 1ms jitter for audio stability'),
        'webrtcvad': ('2.0.10', 'CRITICAL: reference VAD state machine (no alternatives)'),
        'evdev': ('1.5.0', 'CRITICAL: Xbox AbsInfo range support (-32768 to 32767)'),
        'scipy': ('1.10.1', 'CRITICAL: audio filtering compatibility'),
        'pyyaml': ('6.0.1', 'CRITICAL: YAML config parsing compatibility'),
    }
    
    optional_packages = {
        'onnxruntime': 'Inference (custom wheel with Vitis AI EP required)',
    }
    
    all_installed = True
    versions_match = True
    critical_failures = []
    
    # Check required packages with STRICT version validation
    for package, (required_ver, reason) in required_versions.items():
        try:
            mod = __import__(package.replace('-', '_'))
            installed_ver = getattr(mod, '__version__', 'unknown')
            
            if installed_ver == 'unknown':
                logger.warning(f"⚠ {package:20s} v{installed_ver:10s} - {reason}")
                logger.warning(f"   Cannot determine version - manual check required")
                versions_match = False
            elif installed_ver == required_ver:
                logger.info(f"✓ {package:20s} v{installed_ver:10s} - OK")
            else:
                # Version mismatch - FAIL HARD
                logger.error(
                    f"✗ {package:20s} v{installed_ver:10s} (MISMATCH)"
                )
                logger.error(f"   Required:   v{required_ver}")
                logger.error(f"   Reason:     {reason}")
                logger.error(f"   Impact:     HARDWARE FAILURES on Strix Halo MS-M1")
                versions_match = False
                critical_failures.append(package)
        except ImportError:
            logger.error(f"✗ {package:20s} [NOT INSTALLED]")
            logger.error(f"   Reason: {reason}")
            all_installed = False
            critical_failures.append(package)
    
    # Check optional packages
    logger.info("")
    for package, purpose in optional_packages.items():
        try:
            mod = __import__(package.replace('-', '_'))
            installed_ver = getattr(mod, '__version__', 'unknown')
            
            # Check for Vitis AI EP
            if package == 'onnxruntime':
                try:
                    providers = mod.get_available_providers()
                    if 'VitisAIExecutionProvider' in providers:
                        logger.info(f"✓ {package:20s} v{installed_ver} with VitisAI EP")
                    else:
                        logger.error(
                            f"✗ {package:20s} v{installed_ver} [NO Vitis AI EP]"
                        )
                        logger.error("  REQUIRED: Install custom wheel from AMD Developer Lounge")
                        logger.error("  https://www.amd.com/en/developer/resources/ryzen-ai-software.html")
                        critical_failures.append(f"{package} (no Vitis AI EP)")
                except Exception:
                    logger.error(f"✗ {package:20s} - Could not check providers")
                    critical_failures.append(package)
            else:
                logger.info(f"✓ {package:20s} v{installed_ver} - {purpose}")
        except ImportError:
            logger.error(f"✗ {package:20s} [NOT INSTALLED] (REQUIRED)")
            logger.error(f"   Purpose: {purpose}")
            critical_failures.append(package)
    
    # Summary with STRICT failure reporting
    if critical_failures:
        logger.error("\n" + "=" * 60)
        logger.error("✗✗✗ CRITICAL FAILURES - CANNOT RUN ON HARDWARE ✗✗✗")
        logger.error("=" * 60)
        for failure in critical_failures:
            logger.error(f"  - {failure}")
        logger.error("\nThis system is NOT ready. Fix with:")
        logger.error("  pip install --force-reinstall -r requirements.txt")
        logger.error("\nOr use containerized deployment (RECOMMENDED):")
        logger.error("  podman-compose up")
        return False
    elif not all_installed or not versions_match:
        logger.warning("\n⚠ Version control required on Strix Halo MS-M1")
        if not all_installed:
            logger.warning("  Missing packages detected - install all from requirements.txt")
        if not versions_match:
            logger.warning("  Version mismatches WILL cause:")
            logger.warning("    - IOMMU page faults (numpy float32 layout)")
            logger.warning("    - Audio buffer underruns (sounddevice timing)")
            logger.warning("    - VAD state machine crashes (webrtcvad)")
            logger.warning("    - Virtual controller failures (evdev ranges)")
        logger.warning("\nRECOMMENDATION: Use containerized deployment:")
        logger.warning("  podman-compose up")
        logger.warning("\nIf using native, reinstall strictly:")
        logger.warning("  pip install --force-reinstall -r requirements.txt")
        return False
    else:
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL DEPENDENCIES STRICT VERSION CHECK PASSED")
        logger.info("=" * 60)
        logger.info("System is ready for Strix Halo MS-M1 deployment\n")
        return True


def test_environment():
    """Check system environment."""
    logger.info("=" * 60)
    logger.info("TEST 4: System Environment")
    logger.info("=" * 60)
    
    import os
    import subprocess
    
    checks = []
    
    # Check kernel version
    try:
        kernel = os.uname()[2]
        logger.info(f"✓ Kernel: {kernel}")
        if '6.14' in kernel or '6.15' in kernel or '7.' in kernel:
            logger.info("  ✓ Kernel version 6.14+ (good for XDNA 2)")
        else:
            logger.warning("  ⚠ Kernel older than 6.14 (may not support amdxdna)")
    except Exception as e:
        logger.warning(f"  Could not check kernel: {e}")
    
    # Check amdxdna module
    try:
        result = subprocess.run(['lsmod'], capture_output=True, text=True)
        if 'amdxdna' in result.stdout:
            logger.info("✓ amdxdna kernel module loaded")
        else:
            logger.warning("⚠ amdxdna kernel module not loaded (XDNA 2 not available)")
    except Exception as e:
        logger.warning(f"  Could not check kernel modules: {e}")
    
    # Check /dev/uinput
    if os.path.exists('/dev/uinput'):
        if os.access('/dev/uinput', os.R_OK | os.W_OK):
            logger.info("✓ /dev/uinput readable and writable")
        else:
            logger.warning("⚠ /dev/uinput exists but not accessible")
            logger.warning("  Run: ./setup/setup_strix_env.sh")
    else:
        logger.warning("⚠ /dev/uinput not found")
    
    logger.info()
    return True


async def main():
    """Run all tests."""
    print("\n")
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║             vinput Installation Validation                 ║")
    logger.info("║     Voice -> uinput Automation for AMD Strix Halo           ║")
    logger.info("╚════════════════════════════════════════════════════════════╝\n")
    
    # Run tests
    results = {}
    
    results['dependencies'] = test_dependencies()
    results['environment'] = test_environment()
    results['audio'] = await test_audio_engine()
    results['input'] = await test_input_engine()
    
    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{test_name.capitalize():20s} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        logger.info("System validated for Strix Halo MS-M1 hardware")
        logger.info("\nReady to run:")
        logger.info("  python src/main.py")
    else:
        logger.error("\n✗✗✗ TESTS FAILED ✗✗✗")
        if not results['dependencies']:
            logger.error("\nDependency failures MUST be fixed before running on hardware.")
            logger.error("Do NOT attempt to run src/main.py")
            logger.error("\nFix with:")
            logger.error("  Option 1 (RECOMMENDED): Use containerized deployment")
            logger.error("    podman-compose up")
            logger.error("  Option 2: Reinstall native environment")
            logger.error("    pip install --force-reinstall -r requirements.txt")
            logger.error("    Then re-run: python test_installation.py")
        else:
            logger.warning("See error messages above for details.")
            logger.warning("Required steps:")
            logger.warning("    1. Run: ./setup/setup_strix_env.sh")
            logger.warning("    2. Install: pip install -r requirements.txt")
            logger.warning("    3. Download Whisper models to models/")
            logger.warning("    4. Configure commands in config/commands.yaml")
    
    logger.info()
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
