# MySQL database

This directory contains information for the mysql database configuration

### Software
- based on MySQL 5.7, phpMyAdmin 4.9 and Ubuntu 18.04

### Instructions
- install MySQL
    - `sudo apt-get install mysql-server`
- install phpMyAdmin for convenient database access 
    - `sudo apt-get install phpmyadmin php-mbstring php-gettext`
    - for phpMyAdmin configuration, see for example
    https://www.liquidweb.com/kb/install-phpmyadmin-ubuntu-18-04/
- load database structure from the provided `vis_cv_user.sql`
    - `mysql -u root -h localhost -p` (connect to mysql)
    - `CREATE DATABASE vis_cv_user;` (create database)
    - `USE vis_cv_user` (switch database)
    - `exit` (exit MySQL terminal)
    - `mysql -u root -h localhost -p vis_cv_user < vis_cv_user.sql`
    (load database structure from terminal after logout)
    
In the database `vis_cv_user.sql` a user (name: *test*, password: *test*) is included. 
Therefore, after installation you can login with this user.

