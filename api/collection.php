<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


require_once 'response.php';
require_once 'dbservice.php';
require_once 'user.php';
require_once 'util.php';
require_once 'auth.php';
require_once 'routing.php';

class Collection extends DatabaseInterface implements JsonSerializable
{

    public $id;
    public $creator_id;
    public $created;
    public $name;
    public $comment;
    public $status;
    public $total_images;

    const updateable_values = ['name', 'comment'];
    const table_name = 'vis_collections';

    public static function getDBValuesForNew($params): array
    {
        return [
            'id' => null,
            'creator_id' => AuthService::$id,
            'created' => date('Y-m-d H:i:s'),
            'name' => $params[0],
            'comment' => $params[1],
            'status' => 0,
            'total_images' => 0,
        ];
    }

    public function jsonSerialize(): array
    {
        return [
            'id' => $this->id,
            'creator_id' => $this->creator_id,
            'creator' => User::getUserName($this->creator_id),
            'created' => $this->created,
            'name' => $this->name,
            'comment' => $this->comment,
            'status' => $this->status,
            'total_images' => $this->total_images,
            'preview' => $this->previewSource(),
            'editable' => Collection::userCan($this->id, AuthService::get(), Scope::EDIT),
        ];

    }

    public static function userCan($collection_id, User $user, int $action): bool
    {

        /*
        r = read access
        w = write access
        c = can create

        GLOBAL RIGHTS: defined by user->coll_priv
          r w c
        0 x x x
        1 x x y
        2 y x x
        3 y x y
        4 y y y

        LOCAL RIGHTS: defined by vis_collection_access
          r w
        0 x x
        1 y x
        2 y y
        
        */

        // everyone can view its collections
        if ($collection_id == 'all' && $action == Scope::VIEW) {
            return true;
        }

        switch ($action) {
            case Scope::VIEW:
                return $user->coll_priv >= 2 || (isset($user->collection_details[$collection_id]) && $user->collection_details[$collection_id][0] >= 1);
                break;
            case Scope::EDIT:
                return $user->coll_priv == 4 || (isset($user->collection_details[$collection_id]) && $user->collection_details[$collection_id][0] >= 2);
                break;
            case Scope::CREATE:
                return $user->coll_priv == 1 || $user->coll_priv >= 3;
                break;
            default:
                ResponseService::throw(APIError::E_SERVER_UNKNOWN_PERMISSION_REQUEST);
                return false;
                break;
        }
    }

    public static function getCollectionAccessCodes($user_id): array
    {
        $cache_name = 'Collection-getCollectionAccessCodes-' . $user_id;
        // CACHE: cleared in 
        // - Collection::setCollectionAccessCode
        // - User::update

        if (ENABLE_CACHE && apcu_exists($cache_name)) {
            return apcu_fetch($cache_name);
        }

        try {
            $statement = DBService::getPDO()->prepare("SELECT `collection_id`, `priv` FROM `vis_collection_access` WHERE `user_id` = :userid");
            $statement->bindValue(':userid', $user_id);
            $statement->execute();
            $data = $statement->fetchAll(PDO::FETCH_COLUMN | PDO::FETCH_GROUP);
            if (ENABLE_CACHE) {
                apcu_store($cache_name, $data);
            }
            return $data;
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function setCollectionAccessCode(int $user_id, int $collection_id, int $value): void
    {
        DBServie::clearCache('Collection-getCollectionAccessCodes-' . $user_id);
        // CACHE: set in Collection::getCollectionAccessCodes
        try {
            // first delete all if any...
            $statement = DBService::getPDO()->prepare("DELETE FROM `vis_collection_access` WHERE `user_id` = :userid AND `collection_id` = :collid");
            $statement->bindValue(':userid', $user_id);
            $statement->bindValue(':collid', $collection_id);
            $statement->execute();
            // then create new 
            $statement = DBService::getPDO()->prepare("INSERT INTO `vis_collection_access` (`user_id`, `collection_id`, `priv`)  VALUES (:userid, :collid, :priv)");
            $statement->bindValue(':userid', $user_id);
            $statement->bindValue(':collid', $collection_id);
            $statement->bindValue(':priv', $value);
            $statement->execute();
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function new (...$params): int {
      $title = $params[0];
      $comment = $params[1];
      // check if there is a title
      if ($params[0] == null || trim($title) == "") {
          ResponseService::throw(APIError::E_INPUT_REQUIRED_FIELD_MISSING, ['id' => 'new', 'missing' => 'title', 'type' => 'collection']);
          return null;
      }
      // create DB entry
      $collection_id = parent::new ($title, $comment);

      DBService::clearCache('Collection-ofUser');
      // CACHE: set in Collection::ofUser

      // if user has not global permissions, give local permissions for this collection
      try {
          if (!Collection::userCan($collection_id, AuthService::get(), Scope::EDIT)) {
              $statement = DBService::getPDO()->prepare("INSERT INTO `vis_collection_access` VALUES (NULL, :userID, :collectionID, 2)");
              $statement->bindValue(':userID', AuthService::$id);
              $statement->bindValue(':collectionID', $collection_id);
              $statement->execute();
              // update session to update rights
              AuthService::update();
          }
      } catch (PDOException $exception) {
          DBService::handlePDOError(__FUNCTION__, $exception);
      }

      // create folders
      $folderName = 'images_' . $collection_id;
      $mainDirectory = _DATA_ . $folderName;
      $flag0 = mkdir($mainDirectory, 0777);
      $flag1 = mkdir($mainDirectory . DIRECTORY_SEPARATOR . "images", 0777);
      $flag2 = mkdir(_THUMBS_ . "images_" . $collection_id, 0777);
      $flag3 = mkdir($mainDirectory . DIRECTORY_SEPARATOR . "uploads", 0777);
      // An error occured
      if (!$flag0 || !$flag1 || !$flag2 || !$flag3) {
          Collection::update($collection_id, array('status' => 9));
          ResponseService::throw(APIError::E_SERVER_CREATE_FOLDERS, ['type' => 'collection', 'id' => 'new']);
          return null;
      }
      return $collection_id;
  }

    public static function ofUser($user_id, $limits = []): array
    {
        // get collections the user can access
        $bindings = [
            ":userid" => $user_id,
        ];
        return DBService::getData(
            'Collection-ofUser:' . $user_id,
            "SELECT DISTINCT `vis_collections`.* FROM `vis_collections` LEFT JOIN `vis_collection_access` ON `vis_collection_access`.`collection_id`= `vis_collections`.`id` WHERE ((SELECT `vis_users`.`coll_priv` FROM `vis_users` WHERE `vis_users`.`id` = :userid) >= 2 OR (`vis_collection_access`.`user_id` = :userid AND `vis_collection_access`.`priv` >= 1)) AND `vis_collections`.`status` != 9",
            $bindings,
            [PDO::FETCH_CLASS, __CLASS__],
            $limits
        );
        // CACHE: cleared in 
        // - Collection::new
        // - Collection::addToImageCounter
        // - Collection::update
        // - User::update
    }

    private function previewSource(): string
    {
        // get the filename of the most recent image in collection
        // TD:: add this to database?

        $cache_name = 'Collection-preview:' . $this->id;
        if (ENABLE_CACHE && apcu_exists($cache_name)) {
            return apcu_fetch($cache_name);
        }
        // CACHE:: cleared in 
        // - Collection::addToImageCounter
        try {
            $statement = DBService::getPDO()->prepare("SELECT `filename` FROM `vis_images` WHERE `collection_id` = :collid AND `status` != 9 ORDER BY `upload_date` DESC LIMIT 1");
            $statement->bindValue(':collid', $this->id);
            $statement->execute();
            $data = $statement->fetchAll();
            $filename = (count($data) == 0) ? '' : $data[0]['filename'];
            if (ENABLE_CACHE) {
                apcu_store($cache_name, $filename);
            }
            return $filename;
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function addToImageCounter(int $collection_id, int $number)
    {
        try {
            $statement = DBService::getPDO()->prepare("UPDATE `vis_collections` SET `total_images` = `total_images` + :toadd WHERE `id` = :collid");
            $statement->bindParam(':toadd', $number);
            $statement->bindValue(':collid', $collection_id);
            $statement->execute();
            DBService::clearCache('Collection-preview:' . $collection_id);
            // CACHE:: set in $collection->previewSource();
            DBService::clearCache("Collection-ofUser");
            // CACHE:: set in Collection::ofUser
            DBService::clearCache("Obj-Collection-".$collection_id);
            // CACHE: set in Collection::getByID
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function markIndicesAsModified(int $collection_id)
    {
        // set all indices to modified
        try {
            $statement = DBService::getPDO()->prepare("UPDATE `vis_indices` SET `is_latest` = 0 WHERE `collection_id` = :collid");
            $statement->bindValue(':collid', $collection_id);
            $statement->execute();

            DBService::clearCache("Index-ofCollection:" . $collection_id);
            // CACHE: was set in Index::ofCollection
            DBService::clearCache("Obj-Index");
            // CACHE: was set in Index::getByID
            DBService::clearCache('Job-get');
            // CACHE: set in Job::getPendingIndexJobs, Job::getRunningIndexJobs, Job::getFinishedIndexJobs
        } catch (PDOException $exception) {
            DBManager::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function update(int $id, array $values, $safe = false): int
    {
        return parent::update($id, $values, $safe);
        DBService::clearCache('Collection-ofUser');
        // CACHE: set in Collection::ofUser
    }

}
