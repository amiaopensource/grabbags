===============
Getting started
===============

Installing on the System Python
===============================

1. Download the source (or clone the repository) to your computer
2. Open a terminal in the directory of the source
3. Install with setup.py

    On Mac or Linux:

    .. code-block::

        python3 setup.py install

    On Windows:

    .. code-block::

        py setup.py install



Setting up a Development Environment
====================================
1. Create a new Python 3 virtual environment

    On Mac or Linux:

    .. code-block::

        python3 -m venv venv

    On Windows:

    .. code-block::

       py -m venv venv


2. Activate Python virtual environment

    On Mac or Linux:

    .. code-block::

       source venv/bin/activate

    On Windows:

    .. code-block::

       venv/Scripts/activate

3. Install the grabbags in development mode

    .. code-block::

       python -m pip install -e .

4. Start hacking

Building the documentation
==========================

1. Follow the instructions above and install and activate the development
virtual environment

2. Install sphinx

    .. code-block::

        python -m pip install sphinx


3. Run sphinx build target from setup.py

    .. code-block::

        python setup.py build_sphinx

By default, the documentation is generated into build/sphinx/html
