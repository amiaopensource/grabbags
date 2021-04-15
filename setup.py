from setuptools import setup

setup(
    name='grabbags',
    version='0.0.2',
    packages=['grabbags'],
    url='https://github.com/amiaopensource/grabbags',
    license='GPLv3',
    author='AMIA',
    author_email='',
    description='',
    test_suite='tests',
    entry_points={
      'console_scripts': [
          'grabbags = grabbags.grabbags:main'
      ]
    },
    install_requires=[
        "bagit"
    ],
    tests_require=[
        'pytest',
    ],
    setup_requires=[
        'pytest'
    ],


)
