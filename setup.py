from setuptools import setup, find_packages

setup(
    name="crs-bot",
    version="0.1.0",
    description="A bot that monitors GitHub releases and sends notifications to Discord",
    author="Lucas de los Santos",
    author_email="",  # Add if public
    url="https://github.com/lucasdelossantos/CRS-Bot",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "pyyaml>=6.0.1",
        "responses>=0.25.0",
        "setuptools>=69.0.3",
    ],
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.14.0",
            "black>=25.1.0",
            "flake8>=6.1.0",
            "isort>=5.12.0",
            "mypy>=1.7.0",
        ],
    },
) 