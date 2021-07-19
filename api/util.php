<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );

require_once("dbservice.php");
require_once("response.php");


abstract class DatabaseInterface {

  
  const updateable_values = [];
  const table_name = '';

  abstract static function getDBValuesForNew(array $params);

  public static function getByID(int $id) : DatabaseInterface {

    $class_name = get_called_class();
    $cache_name = 'Obj-'.$class_name.'-'.$id;
    if(ENABLE_CACHE && apcu_exists($cache_name)) {
      return apcu_fetch($cache_name);
    }
    // CACHE: cleared in
    // - update
    // IMPORTANT: IF YOU MODIFY OBJECTS DIRECTLY YOU MUST UNSET THE CACHE MANUALLY!

    try {
      $statement = DBService::getPDO()->prepare("SELECT * FROM `".$class_name::table_name."` WHERE `id` = :id");
      $statement->bindValue(':id', $id);
      $statement->execute();
      $data = $statement->fetchObject($class_name);
      if($data == null) {
        ResponseService::throw(APIError::E_NOTFOUND_DB_ENTRY, ['id' => $id, 'type' => $class_name]);
        return null;
      }
      if(ENABLE_CACHE) {
        apcu_store($cache_name, $data);
      }
      return $data;
    }
    catch (PDOException $exception) {
      DBService::handlePDOError(__FUNCTION__, $exception);
    }
  }


  public static function new(... $params) : int {
    $class_name = get_called_class();
    $values = $class_name::getDBValuesForNew($params);
    $keys = array_keys($values);
    try {
      $statement = DBService::getPDO()->prepare("INSERT INTO `".$class_name::table_name."` (`".implode("`, `", $keys)."`) VALUES (:".implode(", :", $keys).")");
      foreach($values as $key => $value) {
        $statement->bindValue(':'.$key, $value);
      }
      $statement->execute();
      // TD: in parallel a mess --> switch to OUTPUT
      $id = DBService::getPDO()->lastInsertId();

      return $id;
    }
    catch (PDOException $exception) {
       DBService::handlePDOError(__FUNCTION__, $exception);
    }
  }


  #public static function update(int $id, array $values, $safe = false) : int {
  public static function update(int $id, array $values, bool $safe = false) : int {
    $class_name = get_called_class();
    $keys = array_keys($values);
    $used_keys = array();
    $update_statements = array_filter(array_map(function($key) use ($class_name, &$used_keys) {
	    if(!$safe || in_array($key, $class_name::updateable_values)) {
		    $used_keys[] = $key;
		    return "`".$key."` = :".$key;
      }
    }, $keys), function($e) {return $e != null;});
    try {
      $statement = DBService::getPDO()->prepare("UPDATE `".$class_name::table_name."` SET ".implode(', ', $update_statements)." WHERE `id` = :id");
      foreach($used_keys as $key) {
        $statement->bindValue(':'.$key, $values[$key]);
      }
      $statement->bindValue(':id', $id);
      $statement->execute();

      $cache_name = 'Obj-'.$class_name.'-'.$id;
      apcu_delete($cache_name);
      // CACHE: set in getByID

      return $statement->rowCount();
    }
    catch (PDOException $exception) {
       DBService::handlePDOError(__FUNCTION__, $exception);
    }
  }

}


 ?>
