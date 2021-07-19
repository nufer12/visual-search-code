<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


include_once 'config.php';
include_once 'response.php';

class DBService
{
    private static $pdo = null;

    public static function init()
    {
        global $db_config;
        $opt = array(
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, // throw errors
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC, // fetch always as assoc
        );
        self::$pdo = new PDO("mysql:host=" . $db_config["host"] . ";dbname=" . $db_config["db"] . ";charset=utf8", $db_config["user"], $db_config["password"], $opt);
    }

    public static function getPDO()
    {
        // init database on first call
        if (self::$pdo == null) {
            DBService::init();
        }
        return self::$pdo;
    }

    public static function handlePDOError($funcname, $exception)
    {
        // handle PDO errors as throwing same to the user :D
        ResponseService::throw(APIError::E_SERVER_PDO_ERROR, array("function" => $funcname, "message" => $exception->getMessage()));
    }

    public static function clearCache($cache_base)
    {
        // just a helper function...
        apcu_delete(new APCUIterator('/^' . $cache_base . '/'));
    }

    public static function getData($cache_base, $sql, $bindings, $fetch_type, $limits = [], $cache = true)
    {
        // only meaningful if cache is on
        //// IMPORTANT: YOU NEED TO KEEP TRACK OF UPDATES ON YOUR OWN BY RESETTING THESE CACHES!!!


        $cache_base = $cache_base . '-' . json_encode($bindings) . '-';
        // if limits provided define a LIMIT statement
        $limiting = (count($limits) < 2) ? '' : ' LIMIT :limoff, :limmax';
        try {
            $data = null;
            // build up cache name and get from cache if exists
            $cache_name_data = $cache_base . json_encode($limits);
            if (ENABLE_CACHE && $cache && apcu_exists($cache_name_data)) {
                $data = apcu_fetch($cache_name_data);
            } else {
                // create statements
                $statement = DBService::getPDO()->prepare($sql . $limiting);
                if (count($limits) == 2) {
                    // bind values
                    $statement->bindValue(':limoff', (int) $limits[0], PDO::PARAM_INT);
                    $statement->bindValue(':limmax', (int) $limits[1], PDO::PARAM_INT);
                }
                // well  :D
                foreach ($bindings as $key => $value) {
                    $statement->bindValue($key, $value);
                }
                $statement->execute();
                $data = $statement->fetchAll(...$fetch_type);
                // if cache anabled save for 1h
                if (ENABLE_CACHE && $cache) {
                    apcu_store($cache_name_data, $data, 3600);
                }
            }

            // get total number of elements

            $total_count = 0;
            // build cache name and get if exists
            $cache_name_count = $cache_base . 'Total';
            if (ENABLE_CACHE && $cache && apcu_exists($cache_name_count)) {
                $total_count = apcu_fetch($cache_name_count);
            } else {
                // modifying select statement as counter
                // neglect limits now
                $sql2 = preg_replace('/^SELECT( DISTINCT)? [^(FROM)]+ FROM/', 'SELECT$1 COUNT(*) FROM', $sql, 1);
                $statement = DBService::getPDO()->prepare($sql2);
                foreach ($bindings as $key => $value) {
                    $statement->bindValue($key, $value);
                }
                $statement->execute();
                $total_count = $statement->fetchColumn();
                // save to cache
                if (ENABLE_CACHE && $cache) {
                    apcu_store($cache_name_count, $data);
                }
            }
            return ["data" => $data, "total" => $total_count];
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

}
