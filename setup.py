"""Setup script for the types_oiio_python package."""

from setuptools import setup  # type: ignore

if __name__ == "__main__":

    setup(
        package_dir={"": "types_oiio_python"},
        packages=["OpenImageIO", "PyOpenColorIO"],
        package_data={
            "OpenImageIO": ["*.*"],
            "PyOpenColorIO": ["*.*"],
        },
        include_package_data=True,
    )
