# Getting started

## Installing on the System Python

1) Download the source (or clone the repository) to your computer
2) Open a terminal in the directory of the source 
2) Install with setup.py

    On Mac or Linux:
    
    ``` python3 setup.py install```

    On Windows:
    ```py setup.py install```



## Setting up a Development Environment
1) Create a new Python 3 virtual environment

    On Mac or Linux:
    
    ``` python3 -m venv venv ```

    On Windows:
    ```py -m venv venv```

2) Activate Python virtual environment

    On Mac or Linux:
    
    ```source venv/bin/activate ```

    On Windows:
    ```venv/Scripts/activate```

3) Install the grabbags in development mode

    ```python -m pip install -e .```

4) Start hacking
