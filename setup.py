from setuptools import setup, find_packages

# Read dependencies
with open("requirements.txt") as f:
    requirements = [
        line.strip() for line in f.readlines()
        if line.strip() and not line.startswith("#")
    ]

# Read README
with open("README.md") as f:
    long_description = f.read()

setup(
    name="quantum-hybrid-portfolio",
    version="0.1.0",
    author="Quantum Portfolio Team",
    description="Pragmatic quantum-inspired portfolio optimization using QSW",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/quantum-hybrid-portfolio",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
)