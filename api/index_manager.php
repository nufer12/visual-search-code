<?php
defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


require_once 'response.php';
require_once 'dbservice.php';

require_once 'util.php';
require_once 'auth.php';
require_once 'image.php';
require_once 'job.php';

class Index extends DatabaseInterface implements JsonSerializable
{
    public $id;
    public $is_latest;
    public $collection_id;
    public $creator_id;
    public $creation_date;
    public $name;
    public $status;
    public $job;
    public $total_images;
    public $type;
    public $typename;
    public $typedescription;
    public $params;
    public $start_time;
    public $end_time;
    public $exitcode;
    public $worker_id;

    const updateable_values = ['name', 'is_latest', 'job', 'total_images', 'status', 'params', 'start_time', 'end_time', 'exitcode', 'worker_id'];
    const table_name = 'vis_indices';

    public static function getDBValuesForNew($params): array
    {
        return [
            'id' => null,
            'is_latest' => true,
            'collection_id' => $params[0],
            'creator_id' => AuthService::$id,
            'creation_date' => date('Y-m-d H:i:s'),
            'name' => $params[1],
            'status' => 0,
            'total_images' => $params[5],
            'type' => $params[2],
            'params' => $params[4],
            'start_time' => null,
            'end_time' => null,
            'exitcode' => null,
            'worker_id' => $params[3],
        ];
    }

    public function jsonSerialize()
    {
        return [
            'id' => $this->id,
            'is_latest' => $this->is_latest,
            'collection_id' => $this->collection_id,
            'creator_id' => $this->creator_id,
            'creator' => User::getUserName($this->creator_id),
            'creation_date' => $this->creation_date,
            'name' => $this->name,
            'status' => $this->status,
            'total_images' => $this->total_images,
            'type' => $this->type,
            'typename' => $this->typename,
            'typedescription' => $this->typedescription,
            'params' => $this->params,
            'start_time' => $this->start_time,
            'end_time' => $this->end_time,
            'exitcode' => $this->exitcode,
            'worker_id' => $this->worker_id,
        ];
    }

    /*

    from database

     */

    public static function ofCollection(int $collection_id, $limits = []): array
    { // array of index
        $bindings = [
            ":collectionid" => $collection_id,
        ];
        return DBService::getData(
            'Index-ofCollection:' . $collection_id,
            "SELECT `vis_indices`.`id`, `vis_indices`.`is_latest`, `vis_indices`.`collection_id`, `vis_indices`.`creator_id`, `vis_indices`.`creation_date`, `vis_indices`.`name`, `vis_indices`.`status`, `vis_indices`.`exitcode`, `vis_indices`.`total_images`, `vis_indices`.`type`, `vis_index_types`.`name` AS typename, `vis_index_types`.`description` AS typedescription FROM `vis_indices` INNER JOIN `vis_index_types` ON `vis_indices`.`type` = `vis_index_types`.`id` WHERE `vis_indices`.`collection_id` = :collectionid",
            $bindings,
            [PDO::FETCH_CLASS, __CLASS__],
            $limits
        );
        // CACHE: cleared in
        // - Collection::markIndicesAsModified
        // - Index::update
        // - Index::rerun
        // - Index::stop
        // - Index::new
    }

    /*

    Create New

     */

    public static function getSupportedIndexTypes($id = null, $full = false)
    {
        // TD: add caching --> requires possibility to add Index Types via PHP
        try {
            $select_stuff = ($full) ? '*' : '`id`, `name`, `description`';
            $where_stuff = ($id !== null) ? ' WHERE `id` = :typeid' : "";
            $statement = DBService::getPDO()->prepare("SELECT " . $select_stuff . " FROM `vis_index_types`" . $where_stuff);
            if ($id !== null) {
                $statement->bindValue(':typeid', $id);
            }
            $statement->execute();
            $data = $statement->fetchAll(PDO::FETCH_ASSOC);
            return ["data" => $data, "total" => count($data)];
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function new (...$parameters): int {
        $collection_id = $parameters[0];
        $settings = $parameters[1];
        $title = $settings['title'];
        // requires title
        if (trim($title) == "") {
            ResponseService::throw(APIError::E_INPUT_REQUIRED_FIELD_MISSING, ['id' => 'new', 'missing' => 'title', 'type' => 'index']);
        }
        // requires indextype
        $index_type = Index::getSupportedIndexTypes($settings['indextype'], true);
        if (count($index_type["data"]) < 1) {
            ResponseService::throw(APIError::E_INPUT_REQUIRED_FIELD_MISSING, ['id' => 'new', 'missing' => 'indextype', 'type' => 'index']);
        } else {
            $index_type = $index_type["data"][0];
        }
        // is a machine set?
        $machine_id = (isset($settings["machine"])) ? $settings["machine"] : -1;

        // get images
        $images = Image::ofCollection($collection_id);
        $index_id = parent::new ($collection_id, $title, $settings['indextype'], $machine_id, $index_type["params"], $images["total"]);

        $mainDirectory = _DATA_ . 'images_' . $collection_id . DIRECTORY_SEPARATOR . 'index_' . $index_id;
        $flag0 = mkdir($mainDirectory, 0777);
        if (!$flag0) {
            Index::update(array($index_id, 'status' => 9));
            ResponseService::throw(APIError::E_SERVER_CREATE_FOLDERS, ['type' => 'index', 'id' => 'new']);
        }
        // Save images
        $destination = $mainDirectory . DIRECTORY_SEPARATOR . 'image_list.json';
        $fp = fopen($destination, 'w');
        fwrite($fp, json_encode($images["data"], JSON_NUMERIC_CHECK));
        fclose($fp);
        
        DBService::clearCache('Index-ofCollection:' . $collection_id);
        // CACHE: set in Index::ofCollection
        DBService::clearCache('Job-get');
        // CACHE: set in Job::getPendingIndexJobs, Job::getRunningIndexJobs, Job::getFinishedIndexJobs

        return $index_id;

    }

    public static function rerun($index_id)
    {
        $index_data = Index::getByID($index_id);
        // if running or no update required: throw error
        if ($index_data->status == 2) {
            ResponseService::throw(APIError::E_INPUT_INDEX_RUNNING);
        }
        if ($index_data->is_latest) {
            ResponseService::throw(APIError::E_INPUT_INDEX_NO_UPDATE_REQUIRED);
        }
         // Save images
        $images = Image::ofCollection($index_data->collection_id);
        $mainDirectory = _DATA_ . 'images_' . $index_data->collection_id . DIRECTORY_SEPARATOR . 'index_' . $index_id;
        $destination = $mainDirectory . DIRECTORY_SEPARATOR . 'image_list.json';
        $fp = fopen($destination, 'w');
        fwrite($fp, json_encode($images["data"], JSON_NUMERIC_CHECK));
        fclose($fp);

        // update index
        Index::update($index_id, array('total_images' => $images["total"], "is_latest" => 1, "status" => 0));
        // DBService::clearCache('Index-ofCollection:' . $collection_id);
        // CACHE: set in Index::ofCollection
        // already cleared in Index::update

        return $index_data->id;
    }

    public static function stop($index_id)
    {
        $index_data = Index::getByID($index_id);
        if($index_data->status > 2) {
            ResponseService::throw(APIError::E_INPUT_NOTHING_TO_STOP);
        }
        // DBService::clearCache('Index-ofCollection:' . $collection_id);
        // CACHE: set in Index::ofCollection
        // already cleared in Index::update
        return Index::update($index_id, ['status' => -1]);
    }

    public static function update(int $id, array $values, $safe = false): int
    {
        // TD: only allow some of them to be updated
        $index_info = Index::getByID($id);
        DBService::clearCache('Index-ofCollection:' . $index_info->collection_id);
        // CACHE: set in Index::ofCollection
        DBService::clearCache('Job-get');
        // CACHE: set in Job::getPendingIndexJobs, Job::getRunningIndexJobs, Job::getFinishedIndexJobs
        return parent::update($id, $values, $safe);
    }

}
