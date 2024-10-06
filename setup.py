from setuptools import setup, find_packages

setup(
    name="InvestmentApp",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "yfinance",
        "numpy",
        "matplotlib",
        "pandas",
        "schedule",
        "Pillow",
        "qrcode",
        "requests",
        "pytz",
    ],
    entry_points={
        'console_scripts': [
            'investmentapp=main:main',
        ],
    },
)