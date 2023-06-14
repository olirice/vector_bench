#!/usr/bin/env python
import setuptools

setuptools.setup(
    name="vector_bench",
    version="0.0.1",
    description="Method chaining built on generators",
    url="https://github.com/olirice/vector_bench",
    author="Oliver Rice",
    author_email="oliver@oliverrice.com",
    packages=setuptools.find_packages("src", exclude=("src/tests",)),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "vector_bench = vector_bench.cli:app",
        ]
    },
    tests_require=["pytest", "coverage"],
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    install_requires=["typer[all]", "sqlalchemy", "psycopg2-binary", "parse", "numpy"],
)
