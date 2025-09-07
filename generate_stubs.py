"""
Script to generate pyi stubs for OpenImageIO and PyOpenColorIO using an improved approach.

This script combines the advanced stub generation from OpenImageIO's new.py with
support for PyOpenColorIO and the existing cleanup functionality.
"""

from __future__ import absolute_import, annotations, division, print_function

import argparse
import os
import pathlib
import sys
from pathlib import Path
from typing import Optional

import mypy.stubgen
import mypy.stubgenc
from mypy.stubgenc import DocstringSignatureGenerator, SignatureGenerator
from stubgenlib.siggen import AdvancedSigMatcher, AdvancedSignatureGenerator
from stubgenlib.utils import add_positional_only_args

PY_TO_STDVECTOR_ARG = "float | typing.Iterable[float]"


class OIIOSignatureGenerator(AdvancedSignatureGenerator):
    """Signature generator specifically for OpenImageIO."""

    sig_matcher = AdvancedSigMatcher(
        signature_overrides={
            # signatures for these special methods include many inaccurate overloads
            "*.__ne__": "(self, other: object) -> bool",
            "*.__eq__": "(self, other: object) -> bool",
        },
        arg_type_overrides={
            # FIXME: Buffer may in fact be more accurate here
            ("*", "*", "Buffer"): "numpy.ndarray",
            # these use py_to_stdvector util
            ("*.ImageBufAlgo.*", "min", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "max", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "black", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "white", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "sthresh", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "scontrast", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "white_balance", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "values", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "top", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "bottom", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "topleft", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "topright", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "bottomleft", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "bottomright", "object"): PY_TO_STDVECTOR_ARG,
            ("*.ImageBufAlgo.*", "color", "object"): PY_TO_STDVECTOR_ARG,
            # BASETYPE & str are implicitly converible to TypeDesc
            ("*", "*", "*.TypeDesc"): "Union[TypeDesc, BASETYPE, str]",
            # list is not strictly required
            (
                "*.ImageOutput.open",
                "specs",
                "list[ImageSpec]",
            ): "typing.Iterable[ImageSpec]",
        },
        result_type_overrides={
            # FIXME: is there a way to use std::optional for these?
            ("*.ImageOutput.create", "object"): "ImageOutput | None",
            ("*.ImageOutput.open", "object"): "ImageOutput | None",
            ("*.ImageInput.create", "object"): "ImageInput | None",
            ("*.ImageInput.open", "object"): "ImageInput | None",
            # if you return an uninitialized unique_ptr to pybind11 it will convert to `None`
            ("*.ImageInput.read_native_deep_*", "DeepData"): "DeepData | None",
            # pybind11 has numpy support
            ("*.ImageInput.read_*", "object"): "numpy.ndarray | None",
            ("*", "Buffer"): "numpy.ndarray",
            ("*.get_pixels", "object"): "numpy.ndarray | None",
            # For results, `object` is too restrictive
            ("*.getattribute", "object"): "typing.Any",
            ("*.ImageSpec.get", "object"): "typing.Any",
            ("*.ImageBufAlgo.histogram", "*"): "tuple[int, ...]",
            ("*.ImageBufAlgo.isConstantColor", "*"): "tuple[float, ...] | None",
            ("*.ImageBufAlgo.color_range_check", "*"): "tuple[int, ...] | None",
            ("*.TextureSystem.imagespec", "object"): "ImageSpec | None",
            ("*.TextureSystem.texture", "tuple"): "tuple[float, ...]",
            ("*.TextureSystem.texture3d", "tuple"): "tuple[float, ...]",
            ("*.TextureSystem.environment", "tuple"): "tuple[float, ...]",
            ("*.ImageBuf.getpixel", "tuple"): "tuple[float, ...]",
            ("*.ImageBuf.interppixel*", "tuple"): "tuple[float, ...]",
            ("*.ImageSpec.get_channelformats", "tuple"): "tuple[TypeDesc, ...]",
        },
        property_type_overrides={
            ("*.ParamValue.value", "object"): "typing.Any",
        },
    )

    def process_sig(
        self, ctx: mypy.stubgen.FunctionContext, sig: mypy.stubgen.FunctionSig
    ) -> mypy.stubgen.FunctionSig:
        """Process signature with OIIO-specific handling."""
        return add_positional_only_args(ctx, super().process_sig(ctx, sig))


class OCIOSignatureGenerator(AdvancedSignatureGenerator):
    """Signature generator specifically for PyOpenColorIO."""

    sig_matcher = AdvancedSigMatcher(
        signature_overrides={
            # Special methods
            "*.__ne__": "(self, other: object) -> bool",
            "*.__eq__": "(self, other: object) -> bool",
        },
        arg_type_overrides={
            # Add PyOpenColorIO-specific type overrides here as needed
        },
        result_type_overrides={
            # Add PyOpenColorIO-specific result type overrides here as needed
        },
    )

    def process_sig(
        self, ctx: mypy.stubgen.FunctionContext, sig: mypy.stubgen.FunctionSig
    ) -> mypy.stubgen.FunctionSig:
        """Process signature with OCIO-specific handling."""
        return add_positional_only_args(ctx, super().process_sig(ctx, sig))


class CustomInspectionStubGenerator(mypy.stubgenc.InspectionStubGenerator):
    """Custom stub generator that uses our signature generators."""

    module_name: str = ""

    def get_sig_generators(self) -> list[SignatureGenerator]:
        if "OpenImageIO" in self.module_name:
            return [
                OIIOSignatureGenerator(
                    fallback_sig_gen=DocstringSignatureGenerator(),
                )
            ]
        elif "PyOpenColorIO" in self.module_name:
            return [
                OCIOSignatureGenerator(
                    fallback_sig_gen=DocstringSignatureGenerator(),
                )
            ]
        else:
            return [DocstringSignatureGenerator()]


def fix_pyopencolorio_exceptions(content: str) -> str:
    """
    Fix the cyclic Exception definition in PyOpenColorIO stubs.

    PyOpenColorIO defines its own Exception class that inherits from Exception,
    creating a cyclic definition. We need to alias the built-in Exception.
    """
    lines = content.split("\n")
    fixed_lines = []

    # Add import for built-in exceptions at the top (after other imports)
    import_added = False

    for i, line in enumerate(lines):
        # Add the import after the first import/from statement
        if not import_added and (
            line.startswith("import ") or line.startswith("from ")
        ):
            fixed_lines.append(line)
            # Check if we haven't already added this import
            if i + 1 < len(lines) and "builtins" not in lines[i + 1]:
                fixed_lines.append(
                    "from builtins import Exception as _BuiltinException"
                )
                import_added = True
            continue

        # Replace Exception inheritance with _BuiltinException
        if "class Exception(Exception):" in line:
            fixed_lines.append("class Exception(_BuiltinException): ...")
        elif (
            line.startswith("class ")
            and "(Exception)" in line
            and "class Exception" not in line
        ):
            # Other exception classes inheriting from the custom Exception are fine
            fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    return "\n".join(fixed_lines)


def fix_overload_conflicts(content: str) -> str:
    """
    Fix overlapping overload issues in generated stubs.

    Common issues:
    1. int is a subtype of float, so separate overloads conflict
    2. Union types that already include subtypes make separate overloads redundant

    Solution: Remove redundant overloads.
    """
    lines = content.split("\n")
    fixed_lines = []
    skip_next = False

    for i in range(len(lines)):
        if skip_next:
            skip_next = False
            continue

        line = lines[i]

        # Check for problematic overload patterns
        if i + 1 < len(lines) and "@overload" in line:
            next_line = lines[i + 1]

            # Pattern 1: int overload when float exists
            if "arg1: int" in next_line and any(
                [
                    "def attribute(" in next_line,
                    "def __init__(" in next_line and "arg1: int" in next_line,
                ]
            ):
                # Look ahead to see if there's a float version
                has_float_version = False
                for j in range(max(0, i - 4), min(len(lines), i + 6)):
                    if j != i + 1 and "arg1: float" in lines[j]:
                        has_float_version = True
                        break

                if has_float_version:
                    skip_next = True
                    continue

            # Pattern 2: TypeDesc class __init__ with redundant overloads
            # Skip standalone BASETYPE and str overloads when Union exists
            if (
                "def __init__(self, arg0: BASETYPE, /)" in next_line
                or "def __init__(self, arg0: str, /)" in next_line
            ):
                # Check if there's a union type that includes this nearby
                for j in range(max(0, i - 10), min(len(lines), i + 10)):
                    if j != i + 1 and "arg0: TypeDesc | BASETYPE | str" in lines[j]:
                        skip_next = True
                        break

                if skip_next:
                    continue

        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def generate_stubs_for_module(
    module_name: str,
    out_path: Path,
    rename_to_init: bool = True,
    cleanup_files: Optional[list[str]] = None,
) -> Path:
    """
    Generate stubs for a specific module.

    Args:
        module_name: Name of the module to generate stubs for
        out_path: Output directory for stubs
        rename_to_init: Whether to rename the main stub file to __init__.pyi
        cleanup_files: List of files to remove after generation

    Returns:
        Path to the generated stub file
    """
    print(f"\nGenerating stubs for {module_name}...")

    # Clean up existing stub directory if it exists
    module_dir = out_path / module_name
    if module_dir.exists():
        import shutil

        print(f"Cleaning existing stubs in {module_dir}")
        shutil.rmtree(module_dir)

    # Patch mypy's stub generator for this module
    old_generator = mypy.stubgenc.InspectionStubGenerator

    # Set the module name on the class itself
    CustomInspectionStubGenerator.module_name = module_name

    mypy.stubgen.InspectionStubGenerator = CustomInspectionStubGenerator  # type: ignore
    mypy.stubgenc.InspectionStubGenerator = CustomInspectionStubGenerator  # type: ignore

    try:
        # Import the module to ensure it's available
        __import__(module_name)

        # Run stubgen
        sys.argv[1:] = ["-p", module_name, "-o", str(out_path), "--inspect-mode"]
        mypy.stubgen.main()

        # Find the generated stub file
        module_dir = out_path / module_name
        source_path = module_dir / f"{module_name}.pyi"

        if not source_path.exists():
            # Sometimes the file might be named differently
            pyi_files = list(module_dir.glob("*.pyi"))
            if pyi_files and pyi_files[0].name != "__init__.pyi":
                source_path = pyi_files[0]

        if not source_path.exists():
            raise FileNotFoundError(f"Stub generation failed for {module_name}")

        # Rename to __init__.pyi if requested
        if rename_to_init and source_path.name != "__init__.pyi":
            dest_path = module_dir / "__init__.pyi"
            print(f"Renaming {source_path} to {dest_path}")
            # On Windows, remove destination if it exists
            if dest_path.exists():
                dest_path.unlink()
            source_path.rename(dest_path)
        else:
            dest_path = source_path

        # Add header comment
        content = dest_path.read_text()
        content = (
            f"# Auto-generated stubs for {module_name}\n"
            f"# Generated with generate_stubs.py\n\n"
        ) + content

        # Add typing_extensions import if needed and not present
        if (
            "Buffer" in content
            and "from typing_extensions import Buffer" not in content
        ):
            lines = content.split("\n")
            # Find where to insert the import (after other imports)
            import_index = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    import_index = i + 1
                elif import_index > 0 and line and not line.startswith(" "):
                    break
            lines.insert(import_index, "from typing_extensions import Buffer")
            content = "\n".join(lines)

        # Fix overload conflicts for OpenImageIO
        if module_name == "OpenImageIO":
            content = fix_overload_conflicts(content)

        # Fix Exception cyclic definition for PyOpenColorIO
        if module_name == "PyOpenColorIO":
            content = fix_pyopencolorio_exceptions(content)

        dest_path.write_text(content)

        # Clean up unwanted files
        if cleanup_files:
            for filename in cleanup_files:
                file_path = module_dir / filename
                if file_path.exists():
                    print(f"Removing {file_path}")
                    file_path.unlink()

        # Create py.typed marker file
        py_typed_path = module_dir / "py.typed"
        py_typed_path.touch()
        print(f"Created {py_typed_path}")

        return dest_path

    finally:
        # Restore original generator
        mypy.stubgen.InspectionStubGenerator = old_generator  # type: ignore
        mypy.stubgenc.InspectionStubGenerator = old_generator  # type: ignore


def main() -> None:
    """Main entry point for stub generation."""
    parser = argparse.ArgumentParser(
        description="Generate type stubs for OpenImageIO and PyOpenColorIO"
    )
    parser.add_argument(
        "--out-path",
        default="types_oiio_python",
        help="Directory to write the stubs (default: types_oiio_python)",
    )
    parser.add_argument(
        "--oiio-only", action="store_true", help="Only generate stubs for OpenImageIO"
    )
    parser.add_argument(
        "--ocio-only", action="store_true", help="Only generate stubs for PyOpenColorIO"
    )

    args = parser.parse_args()
    out_path = Path(args.out_path)

    print(f"Stub output directory: {out_path}")
    out_path.mkdir(parents=True, exist_ok=True)

    success = True

    # Generate OpenImageIO stubs
    if not args.ocio_only:
        try:
            oiio_stub = generate_stubs_for_module(
                "OpenImageIO",
                out_path,
                rename_to_init=True,
                cleanup_files=["_tool_wrapper.pyi"],
            )
            print(f"✓ Generated OpenImageIO stubs: {oiio_stub}")
        except Exception as e:
            print(f"✗ Failed to generate OpenImageIO stubs: {e}")
            success = False

    # Generate PyOpenColorIO stubs
    if not args.oiio_only:
        try:
            ocio_stub = generate_stubs_for_module(
                "PyOpenColorIO",
                out_path,
                rename_to_init=True,
                cleanup_files=["_tool_wrapper.pyi"],
            )
            print(f"✓ Generated PyOpenColorIO stubs: {ocio_stub}")
        except Exception as e:
            print(f"✗ Failed to generate PyOpenColorIO stubs: {e}")
            success = False

    if success:
        print("\n✓ Stub generation completed successfully!")
    else:
        print("\n✗ Some stub generation tasks failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
