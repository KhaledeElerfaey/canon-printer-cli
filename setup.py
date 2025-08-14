#!/usr/bin/env python3

from setuptools import setup, find_packages
import sys
import os

# Read README for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

# Platform-specific dependencies
install_requires = [
    'requests>=2.28.0',
    'PyYAML>=6.0',
    'Pillow>=9.0.0',
    'zeroconf>=0.39.0',
]

# Add platform-specific dependencies
if sys.platform.startswith('win'):
    install_requires.extend([
        'pywin32>=227',
        'wmi>=1.5.1'
    ])
else:
    install_requires.append('python-cups>=1.9.73')

setup(
    name='canon-printer-cli',
    version='1.0.0',
    author='Canon Printer CLI',
    author_email='',
    description='A cross-platform command-line tool for printing documents to Canon printers via IPP',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    url='https://github.com/your-username/canon-printer-cli',
    packages=find_packages(exclude=['tests*']),
    py_modules=[
        'main',
        'printer_discovery',
        'document_handler', 
        'config_manager',
        'platform_utils'
    ],
    entry_points={
        'console_scripts': [
            'canon-print=main:main',
            'canon-printer-cli=main:main',
        ],
    },
    install_requires=install_requires,
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=3.0.0',
            'black>=22.0.0',
            'flake8>=4.0.0',
            'mypy>=0.950',
        ],
        'gui': [
            'tkinter',  # Usually included with Python
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Office/Business',
        'Topic :: Printing',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Topic :: Utilities',
    ],
    python_requires='>=3.7',
    keywords='canon printer ipp printing cli cross-platform windows macos linux',
    project_urls={
        'Bug Reports': 'https://github.com/your-username/canon-printer-cli/issues',
        'Source': 'https://github.com/your-username/canon-printer-cli',
        'Documentation': 'https://github.com/your-username/canon-printer-cli/blob/main/README.md',
    },
    include_package_data=True,
    zip_safe=False,
)
