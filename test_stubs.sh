echo "OpenImageIO:"
stubtest OpenImageIO --allowlist oiio-mypy-baseline.txt
echo "PyOpenColorIO:"
stubtest PyOpenColorIO --allowlist ocio-mypy-baseline.txt