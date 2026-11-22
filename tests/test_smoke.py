"""Smoke tests to verify the package is importable and minimally functional."""


def test_package_imports():
    import openscience

    assert openscience is not None


def test_package_has_version_or_attribute():
    import openscience

    # The package should at least be a proper module; assert something stable.
    assert hasattr(openscience, "__name__")
