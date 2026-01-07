"""Setup script for lib_zerodha."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text() if (this_directory / "README.md").exists() else ""

setup(
    name="lib_zerodha",
    version="1.0.0",
    description="A focused Kite Connect integration library for Zerodha API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Anil Kumar S N",
    author_email="anilkumarsn@example.com",
    url="https://github.com/anilkumarsn/lib_zerodha",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "websocket-client>=1.4.0",
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "urllib3>=1.26.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "analysis": [
            "matplotlib>=3.5.0",
            "seaborn>=0.11.0",
            "plotly>=5.10.0",
            "scipy>=1.9.0",
            "scikit-learn>=1.1.0",
        ],
    },
    keywords=[
        "zerodha", "kite", "trading", "api", "stocks", "finance", 
        "market-data", "websocket", "real-time", "nse", "bse"
    ],
)
