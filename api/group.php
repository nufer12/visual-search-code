<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


require_once 'response.php';
require_once 'dbservice.php';

require_once 'util.php';
require_once 'auth.php';

class Group extends DatabaseInterface
{

    public $id;
    public $name;
    public $members;
    public $collection_id;

    // const updateable_values = ['name', 'members'];
    const updateable_values = [];
    const table_name = 'vis_search_groups';

    public static function getDBValuesForNew($params): array
    {
        return [
            'id' => null,
            'name' => $params[1],
            'collection_id' => $params[0],
            'members' => $params[2],
        ];
    }

    public static function addToCounter($group_id)
    {
        DBServie::clearCache('Obj-Group-' . $group_id);
        // CACHE: set in Group::getByID
        try {
            $statement = DBService::getPDO()->prepare("UPDATE " . Group::table_name . " SET `members` = `members` + 1 WHERE `id` = :groupid");
            $statement->bindValue(':groupid', $group_id);
            $statement->execute();
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

}
