from setuptools import setup

setup(
    name='grabbags',
    version='0.0.1',
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
    package_data={
        "grabbags": ["*.ui"],
    },
    install_requires=[
        "bagit",

    ],
    extras_require={
        'GUI': [
            "pyside2",
            "importlib_resources;python_version<'3.9'"
        ]
    },
    tests_require=[
        'pytest',
    ],
    setup_requires=[
        'pytest'
    ],


)
