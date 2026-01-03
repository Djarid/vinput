# Design Decision: Containerization-First Approach

## Change Made

**Removed virtualenv creation from setup_strix_env.sh**

The setup script was incorrectly conflating two distinct approaches:
1. **Containerized Deployment** (recommended, isolated versions)
2. **Native Development** (advanced, requires manual virtualenv)

### Why This Was Wrong

Creating a virtualenv automatically in the setup script implied that native setup was the default/recommended approach. This contradicts the core decision to use containerization for:
- ✅ Exact version pinning (no conflicts)
- ✅ Complete isolation (no system Python pollution)
- ✅ Reproducibility (same versions always)

## Corrected Architecture

### Primary Path: Containerized (Podman)
```bash
podman-compose build
podman-compose up
```
- Handles all version management internally
- No local Python virtualenv needed
- No setup complexity
- Zero version conflicts

### Secondary Path: Native Development (Advanced)
Only for developers working directly on Strix Halo hardware who need:
- Real-time debugging
- Direct hardware access
- Custom modifications

Requires manual setup:
```bash
python3 -m venv .venv              # User creates virtualenv
source .venv/bin/activate          # User activates
pip install -r requirements.txt    # User manages versions
```

## Updated Files

### `setup/setup_strix_env.sh`
**Before**: Validated environment AND created virtualenv
**After**: Validates environment ONLY
- ✅ Checks kernel version (6.14+)
- ✅ Validates amdxdna module
- ✅ Checks uinput permissions
- ✅ Verifies Podman/Docker installed
- ✅ Points users to containerized deployment
- ℹ️ Notes virtualenv creation for native setup (manual)

### `README.md`
**Before**: "Option A (Container)" and "Option B (Native)"
**After**: Clear hierarchy
- ✅ **Recommended**: Containerized approach
- ⚠️ **Advanced**: Native development (requires manual setup)

### `QUICKSTART.md`
**Before**: Container and native approaches equally weighted
**After**: Clear prioritization
- ✅ **3 min**: Containerized (primary)
- ⚠️ **5 min**: Manual validation + native setup (secondary)

## Design Principles Restored

1. **Containerization First**
   - Primary deployment vehicle
   - Handles version isolation completely
   - No virtualenv complexity needed

2. **Clear Separation of Concerns**
   - `setup_strix_env.sh` = Host validation only
   - `compose.yaml` = Version management + deployment
   - `.venv` (optional) = Native development only

3. **User Intent Clarity**
   - Most users (99%): Run `podman-compose up`
   - Advanced users (1%): Create `.venv` manually for development

## Key Points

**The containerized approach is self-contained:**
- No need for local Python virtual environment
- No need to manually manage dependencies
- No version conflicts possible
- Exact same versions every time

**Native development (if needed) requires explicit manual setup:**
- User must create virtualenv: `python3 -m venv .venv`
- User must activate it: `source .venv/bin/activate`
- User must install dependencies: `pip install -r requirements.txt`
- User must install custom wheel: AMD's onnxruntime_vitisai

This explicit approach makes it clear that native development is the exception, not the rule.

## Impact Summary

✅ **Removes confusion** about "which method should I use?"
✅ **Aligns with stated goal** of containerization for isolation
✅ **Simplifies default path** (podman-compose up)
✅ **Maintains advanced path** (native development still possible)
✅ **Documents trade-offs** (container = easy, native = control)

---

**Result**: Containerization-first architecture with optional native development fallback.
