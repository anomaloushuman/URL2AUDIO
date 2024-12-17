# setup.py
from setuptools import setup

setup(
    name='YT2MP3',
    version='0.1',
    install_requires=[
        'numpy==1.26.4',
        'shazamio==0.7.0',
        'yt-dlp==2024.12.13',
        'pydub==0.25.1',
        'librosa==0.10.2.post1',
        'mutagen==1.47.0',
    ],
)