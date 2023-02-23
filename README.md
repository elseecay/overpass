![test-lint](https://github.com/elseecay/overpass/actions/workflows/test-lint.yml/badge.svg)

# **Overpass**

Overpass is pure python password manager

**Required python >= 3.10**


## *Installation*

- **Clone repo**

        git clone https://github.com/elseecay/overpass.git

- **Create venv and install dependencies**

        cd overpass
        python -m venv ./venv

        source ./venv/bin/activate  # linux
        .\venv\Scripts\Activate.ps1 # windows

        pip install -r requirements.txt

        # run tests (optional)
        python main.py -t all

- **Build executable**

        python mkexe.py

        # move it to your $PATH if you like
        sudo mv ./overpass /usr/local/bin/overpass # linux

- **Create config file**

        mkdir $HOME/.overpass
        cp ./cfgsample.json $HOME/.overpass/config.json


- *You can also try it inside docker*

        docker build . -t overpass
        docker run --rm -it overpass


## *Configuration*

    db_directory - absolute folder path where to search databases
    default_db - database for auto connect on execution

    cloud.enabled - enable/disable cloud
    cloud.service - cloud service used by default
    cloud.autoupload - upload database on disconnection (if changed)

    cloud.dropbox.refresh_token_path - absolute path to txt file with token (get it with --get-token-dropbox)
    cloud.dropbox.upload_directory - dropbox upload directory path, shoud start with '/'

    cloud.yandex_disk.access_token_path - absolute path to txt file with token (get it with --get-token-yandex)
    cloud.yandex_disk.upload_directory - dropbox upload directory path, shoud start with 'app:/'


## *How to use*

    # create database 'mydb' and connect to it
    newdb -c mydb

    # create table 'pass'
    newtable pass

    # insert key 'google.com' into table 'pass'
    ins pass google.com login:mylogin password:mypass

    # get key 'google.com' from table 'pass'
    get pass google.com

    # exit
    q

    # use 'help' for full command list
    help

    # use 'cmd -h' for specific command help 
    newtable -h


## *Plans*

- Client/Server
- GUI
- Android app
