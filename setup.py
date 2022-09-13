from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="blatt",
    version='0.1.6',
    author="Renat Shigapov",
    license="MIT",
    description="NLP-helper for OCR-ed pages in PAGE XML format.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/UB-Mannheim/blatt",
    install_requires=['lxml', 'tqdm', 'click', 'segtok'],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'blatt = blatt.cli:cli',
        ],
    },
)
