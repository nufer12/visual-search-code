# Apache2 configs

### Software
- based on Apache 2.4 and Ubuntu 18.04

### Instructions
- install Apache2
    - `sudo apt-get install apache2`
- configure `/etc/apache2/sites-available/000-default.conf` (adapt the provided example)
    - to run as local host replace **:80* with *localhost:80*
    - set ServerName by replacing `[server_name]`
    - set *www-directory* by replacing ours, i.e. replace `/media/dataDrive/www/html`
- configure `/etc/apache2/apache2.conf` (adapt the provided example)
    - set *www-directory* by replacing ours, i.e. replace `/media/dataDrive/www/html`
- increase file upload size limit (default 2MB) in PHP-Apache
    - see for example: https://www.cyberciti.biz/faq/increase-file-upload-size-limit-in-php-apache-app/ 
- enable specified modules and restart Apache2
    - `sudo a2enmod rewrite && sudo /etc/init.d/apache2 restart`
    
The `www-directory/api` must include the php api code and `www-directory/v2` the compiled angular frontend code.

    
 
