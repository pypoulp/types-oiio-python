"""Utility script to generate and fix type stubs for the OpenImageIO and PyOpenColorIO packages."""

import re
import subprocess
from pathlib import Path
from typing import List

here = Path(__file__).parent

OIIO_PKG_DIR = here / "types_oiio_python" / "OpenImageIO"
OCIO_PKG_DIR = here / "types_oiio_python" / "PyOpenColorIO"


def generate_stubs(package_name: str) -> None:
    """Run `stubgen` to generate type stubs."""
    subprocess.run(
        ["stubgen", "-p", package_name, "-o", "types_oiio_python", "--inspect-mode"],
        check=True,
    )


def fix_stubs_args(lines: List[str]) -> List[str]:
    """Fix the stubs where keyword args are followed by positional args."""

    def_pattern = re.compile(r"^(\s*)def\s+(\w+)\((.*?)\)\s*->\s*([^:]+):(\s*\.\.\.)?$")

    def parse_arguments(arg_string: str) -> List[str]:
        """Parse the arguments string and return a list of arguments."""
        args = []
        current_arg: List[str] = []
        bracket_level = 0

        for char in arg_string:
            if char == "," and bracket_level == 0:
                if current_arg:
                    args.append("".join(current_arg).strip())
                current_arg = []
            else:
                current_arg.append(char)
                if char in "([{<":
                    bracket_level += 1
                elif char in ")]}>":
                    bracket_level -= 1

        if current_arg:
            args.append("".join(current_arg).strip())

        return [arg for arg in args if arg]

    def fix_arguments(def_line: str) -> str:
        """Fix the arguments in the given def line."""
        match = def_pattern.match(def_line)
        if not match:
            return def_line

        indent, func_name, args_str, return_type = match.groups()[:4]
        parsed_args = parse_arguments(args_str)
        fixed_args = []
        has_positional_after = False

        # First pass: check if there are positional args after keyword args
        for i, arg in enumerate(reversed(parsed_args)):
            if "=" not in arg and i != 0:
                has_positional_after = True
                break

        # Second pass: fix arguments
        for arg in parsed_args:
            if "=" in arg and has_positional_after and "= ..." in arg:
                fixed_args.append(arg.split("=")[0].strip())
            else:
                fixed_args.append(arg)

        new_args = ", ".join(fixed_args)
        if def_line.strip().endswith("..."):
            return f"{indent}def {func_name}({new_args}) -> {return_type}: ...\n"
        return f"{indent}def {func_name}({new_args}) -> {return_type}:\n"

    return [
        fix_arguments(line) if line.strip().startswith("def ") else line
        for line in lines
    ]


def fix_oiio_stubs() -> None:
    """Apply custom fixes to the generated OpenImageIO stubs."""
    to_remove = [OIIO_PKG_DIR / "_tool_wrapper.pyi"]
    for path in to_remove:
        if path.exists():
            path.unlink()
    main_stubs = OIIO_PKG_DIR / "OpenImageIO.pyi"

    with open(main_stubs, "r", encoding="utf-8") as file:
        lines = file.readlines()

    # Fix the stubs
    cleaned_lines = fix_stubs_args(lines)

    #  Add 'import typing_extensions' at the top if not present
    if not any(
        "from typing_extensions import Buffer" in line for line in cleaned_lines
    ):
        cleaned_lines.insert(0, "from typing_extensions import Buffer\n\n")

    # Write the cleaned content back to the file
    with open(main_stubs, "w", encoding="utf-8") as file:
        file.writelines(cleaned_lines)


if __name__ == "__main__":
    # Clean the directory
    # Generate stubs
    print("Generating stubs...")
    generate_stubs("OpenImageIO")
    generate_stubs("PyOpenColorIO")

    # Fix stubs
    print("Fixing stubs...")
    fix_oiio_stubs()
