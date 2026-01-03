# Contributing to vinput

Thank you for contributing to vinput! This project is protected by GPL-3.0-or-later with distributed copyright to ensure it remains free forever.

## How Contributions Work

### Your Rights as a Contributor

When you contribute to vinput:
- ✅ You **retain copyright** to your code
- ✅ You **retain all rights** to use your code elsewhere
- ✅ You license it under GPL-3.0-or-later (no exclusivity required)
- ✅ Your contribution is protected from proprietary relicensing

### Contributor License Statement

By submitting a contribution (code, documentation, etc.), you agree to:

```
I certify that:

1. I authored 100% of the content I'm contributing, or I have legal
   permission to contribute all content I'm submitting.

2. I understand that my contribution will be licensed under the same
   GPL-3.0-or-later license as the rest of the project.

3. I retain copyright to my contribution and grant the project the right
   to distribute it under GPL-3.0-or-later.

4. I understand that the GPL-3.0-or-later license is irrevocable and
   cannot be changed to a more permissive or proprietary license by any
   future copyright holder.

5. I agree that my contribution helps protect vinput from proprietary
   takeover and ensures it remains free software forever.
```

**You do NOT need to sign anything.** By submitting a pull request or patch,
you implicitly agree to these terms.

## Distributed Copyright Model

This project uses **distributed copyright** (like Linux):

- Each contributor owns their code
- No copyright assignment to maintainers
- No CLA requiring you to give up rights
- Unanimous consent needed to change license (prevents relicensing)
- Future buyers cannot close-source the project

This is the strongest protection against "capitalist snakes" trying to
steal and commercialize our work.

## Code Style Guidelines

- Python: PEP 8 compliant
- Type hints where possible
- Async/await for I/O-bound operations
- Comments for complex logic
- License header in new files (see examples)

## License Header for New Files

Add this to the top of new Python files:

```python
# vinput - Voice Automation for AMD Strix Halo
# Copyright (C) 2026 [Your Name]
# SPDX-License-Identifier: GPL-3.0-or-later

"""
[Brief description of module]
"""
```

Replace `[Your Name]` with your name. This establishes your copyright.

## Testing

Before submitting:

```bash
# Run test suite
python test_installation.py

# Check for version mismatches
./verify_isolation.sh

# Test in container
podman-compose up
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes with license headers
4. Commit with descriptive messages
5. Push to your fork
6. Open a Pull Request with description

## Commit Message Format

```
Brief description (50 chars max)

Longer explanation if needed (72 chars per line).
Reference issues: Fixes #123

Why this change:
- Point 1
- Point 2
```

## What We're Looking For

### High Priority
- NPU inference optimizations
- Audio engine improvements
- Virtual controller enhancements
- Hardware compatibility fixes

### Medium Priority
- Documentation improvements
- Test coverage expansion
- Performance profiling
- CI/CD setup

### Low Priority (but welcome)
- GUI tools
- Additional command types
- Mouse automation (new feature)
- Language support

## Questions?

- Ask in a GitHub issue
- Discussion: GitHub Discussions
- Email: jason@minisforum-ms-m1.local

## Code of Conduct

Be respectful. That's it. No CoC committees, just be decent to each other.

## License Reminder

By contributing, you're helping protect vinput from proprietary takeover.
Your code will remain free, forever, for everyone. Thank you for that.

---

**Remember:** GPL means freedom. We're not trying to exclude commercial users,
we're trying to ensure that improvements benefit everyone, not just one
corporation's bottom line.
