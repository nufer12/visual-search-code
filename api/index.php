<?php

// allow CORS requests
header('Access-Control-Allow-Origin: *');

// not used
define('_ROOT_API_', '[api_data_path]');
define('_ROOT_PYTHON_', '[python_data_path]');
define('_LIB_',"lib/");

// no script kiddies ;)
define('ABSPATH', True);

// index, search data, and full resolution images will be stored here
define('_DATA_', _ROOT_PYTHON_."dataNewInterface/");
// thumbnails of images will be stored here, not required by search and indexing stuff
define('_THUMBS_', _ROOT_API_."interfaceThumbs/");

// there is a caching system, but this is a bit messy :D
define('ENABLE_CACHE', FALSE);

umask(0);
// and go...
include('routing.php');
?>
