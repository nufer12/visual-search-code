# REST API

This directory contains the php code for the REST API

### Software
- based on PHP 7.2 and Ubuntu 18.04

### Instructions
- install php 
    - `sudo apt-get install php libapache2-mod-php`
- install required php apcu extension
    - `sudo apt install php-apcu`
- adapt `config.php`
    - provide your database password, i.e. replace `[database_password]`
    - set an api secret, i.e. replace `[api_scret]`
- adapt `index.php`
    - set api data path (thumbnails of images), i.e. replace `[api_data_path]`
    - set python data path (initialization, search data and full resolution images), i.e. replace `[python_data_path]`
    - if the python search backend should run on another machine, 
    then the python backend data path must be accessible from both machines, e.g. use `sshfs`
- copy the api directory into your *www-directory* (ours `/media/dataDrive/www/html/api`) 

The `www-directory/api` must include the php api code and `www-directory/v2` the compiled angular frontend code.
The directory must be specified in the Apache2 configuration files.


