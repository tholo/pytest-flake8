# -*- coding: utf-8 -*-

"""Install package."""

import setuptools

setuptools.setup(
    name="pytest-flake8-v2",
    version="1.2.0",
    description="pytest plugin to check FLAKE8 requirements",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Operating System :: OS Independent",
    ],
    license="BSD License",
    author="Thorsten Lockert",
    author_email="tholo@sigmasoft.com",
    maintainer="Ilja Orlovs",
    maintainer_email="vrghost@gmail.com",
    url="https://github.com/VRGhost/pytest-flake8",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    py_modules=[
        "pytest_flake8",
    ],
    entry_points={
        "pytest11": ["flake8 = pytest_flake8"],
    },
    install_requires=[
        "flake8>=4.0",
        "pytest>=7.0",
    ],
    python_requires=">=3.6",
)
