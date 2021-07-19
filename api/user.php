<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


require_once 'dbservice.php';
require_once 'response.php';
require_once 'util.php';

/*

User

 */

class User extends DatabaseInterface implements JsonSerializable
{

    public $id;
    public $name;
    public $password;
    public $time_limit;

    public $coll_priv;
    public $user_priv;
    public $resource_priv;

    public $status;

    public $collection_details = array();

    const updateable_values = [];
    const table_name = 'vis_users';
    public static function getDBValuesForNew($params): array
    {
        return [
            'id' => null,
            'name' => $params[0],
            'password' => $params[2],
            'time_limit' => $params[1],
            'coll_priv' => $params[3],
            'user_priv' => $params[4],
            'resource_priv' => $params[5],
            'status' => 0,
            'session_id' => '',    // NON
        ];
    }

    public function jsonSerialize()
    {
        $sess_id = (AuthService::$id == $this->id) ? session_id() : '';
        return [
            'id' => $this->id,
            'name' => $this->name,
            'time_limit' => $this->time_limit,

            'coll_priv' => $this->coll_priv,
            'user_priv' => $this->user_priv,
            'resource_priv' => $this->resource_priv,

            'collection_details' => $this->collection_details,

            'status' => $this->status,
            'session-id' => $sess_id,

        ];
    }

    public static function jsonDeserialize(array $data): User
    {
        // for session storage
        $user = new User();
        $user->id = $data['id'];
        $user->name = $data['name'];
        $user->time_limit = $data['time_limit'];
        $user->coll_priv = $data['coll_priv'];
        $user->user_priv = $data['user_priv'];
        $user->resource_priv = $data['resource_priv'];
        $user->collection_details = $data['collection_details'];
        if (AuthService::$id == $user->id) {
            $user->session_id = session_id();
        }

        return $user;
    }
    

    public static function getByUserName(string $username): User
    {
        try {
            $statement = DBService::getPDO()->prepare("SELECT * FROM `vis_users` WHERE `name` = :name");
            $statement->bindValue(':name', $username);
            $statement->execute();
            $user = $statement->fetchObject(__CLASS__);
            if ($user == null) {
                ResponseService::throw(APIError::E_NOTFOUND_USER, ['username' => $username, 'type' => 'User']);
                return null;
            }
            if ($user->coll_priv != 4) {
                $user->collection_details = Collection::getCollectionAccessCodes($user->id);
            }
            return $user;
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function getByID(int $id): DatabaseInterface
    {
        $user = parent::getByID($id);
        if ($user->coll_priv != 4) {
            $user->collection_details = Collection::getCollectionAccessCodes($user->id);
        }
        return $user;
    }

    /*

    Get usernames

     */

    public static function getUserName($user_id)
    {
        // caching is done in Obj-User-$user_id
        return User::getByID($user_id)->name;
    }

    /*

    New

     */

    public static function usernameExists($username): bool
    {
        try {
            $statement = DBService::getPDO()->prepare("SELECT `id` FROM `vis_users` WHERE `name` = :name");
            $statement->bindValue(':name', $username);
            $statement->execute();
            $user = $statement->fetchObject(__CLASS__);
            if ($user == null) {
                return false;
            } else {
                return true;
            }
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function new (...$parameters): int {
        $username = trim($parameters[0]);

        if ($parameters[0] == null || $username == "") {
            ResponseService::throw(APIError::E_INPUT_REQUIRED_FIELD_MISSING, ['id' => 'new', 'missing' => 'username', 'type' => 'User']);
            return null;
        }
        if (User::usernameExists($username)) {
            ResponseService::throw(APIError::E_INPUT_REQUIRED_FIELD_WRONG, ['type' => 'User', 'id' => 'new', 'data' => 'username exists']);
        }

        // set time limit
        $time_limit = $parameters[1];
        $today = date('Y-m-d H:i:s');
        
        // validate passwords
        $password = trim($parameters[2]);
        if ($parameters[2] == null || $password == "") {
            ResponseService::throw(APIError::E_INPUT_REQUIRED_FIELD_MISSING, ['id' => 'new', 'missing' => 'password', 'type' => 'User']);
            return null;
        }

        // TD: validate
        $coll_priv = intval($parameters[3]);
        $user_priv = intval($parameters[4]);
        $resource_priv = intval($parameters[5]);

        $user_id = parent::new ($username, $time_limit, $password, $coll_priv, $user_priv, $resource_priv);

        DBService::clearCache('User-listAll');
        // CACHE: set in User::listAll
        return $user_id;

    }

    public static function listAll($limits = []): array
    {

        $bindings = [];
        return DBService::getData(
            'User-listAll',
            "SELECT `id`, `name`, `time_limit`, `coll_priv`, `user_priv`, `resource_priv`, `status` FROM `vis_users`",
            $bindings,
            [PDO::FETCH_CLASS, __CLASS__],
            $limits
        );
        // CACHE: cleared in
        // - User::new
        // - User::update
    }

    public static function editInfo(int $user_id)
    {

        $user = User::getByID($user_id);
        // unset passwords for security reason
        $user->password = '';
        $user->session_id = '';
        // get own collections...
        $editable_collections = Collection::ofUser(AuthService::$id)["data"];
        $new_details = array();
        // match them with collections of user
        foreach ($editable_collections as $collection) {
            $new_details[$collection->id] = 0;
            // set own access level
            if (isset($user->collection_details[$collection->id])) {
                $new_details[$collection->id] = $user->collection_details[$collection->id][0];
            }
        }
        $user->collection_details = $new_details;
        return $user;
    }

    public static function setSessionID(int $user_id, string $session_id)
    {
      parent::update($user_id, ["session_id" => $session_id]);
    }

    public static function update(int $user_id, array $params, $safe = false): int
    {
        $update_params = [];
        $self_with_details = User::editInfo(AuthService::$id);

        // name must not be empty and should not exists already
        if (isset($params['name']) && trim($params['name']) != "") {
            if (User::usernameExists(trim($params['name']))) {
                ResponseService::throw(APIError::E_INPUT_REQUIRED_FIELD_WRONG, ['type' => 'User', 'id' => $user_id, 'data' => 'username exists']);
            } else {
                $update_params['name'] = trim($params['name']);
            }
        }

        // passwords must match and can not be empty, only a user itself can update the password
        if (isset($params['password']) && trim($params['password']) != "") {
            if ($self_with_details->id == $user_id) {
                $update_params['password'] = trim($params['password']);
            } else {
                ResponseService::throw(APIError::E_INPUT_UPDATE_ONLY_SELF, ['type' => 'User', 'id' => $user_id, 'data' => 'password']);
            }
        }

        // check if tries to grant more privileges than self has
        if (isset($params['coll_priv'])) {
            if ($params['coll_priv'] > $self_with_details->coll_priv || ($self_with_details->coll_priv == 2 && $params['coll_priv'] == 1)) {
                ResponseService::throw(APIError::E_INPUT_MORE_RIGHTS_THAN_SELF, ['type' => 'User', 'id' => $user_id, 'data' => 'coll_priv', 'have' => $self_with_details->coll_priv, 'requested' => $params['coll_priv']]);
            } else {
                $update_params['coll_priv'] = $params['coll_priv'];
            }
        }
        if (isset($params['user_priv'])) {
            if ($params['user_priv'] > $self_with_details->user_priv) {
                ResponseService::throw(APIError::E_INPUT_MORE_RIGHTS_THAN_SELF, ['type' => 'User', 'id' => $user_id, 'data' => 'user_priv', 'have' => $self_with_details->user_priv, 'requested' => $params['user_priv']]);
            } else {
                $update_params['user_priv'] = $params['user_priv'];
            }
        }
        if (isset($params['resource_priv'])) {
            if ($params['resource_priv'] > $self_with_details->resource_priv) {
                ResponseService::throw(APIError::E_INPUT_MORE_RIGHTS_THAN_SELF, ['type' => 'User', 'id' => $user_id, 'data' => 'resource_priv', 'have' => $self_with_details->resource_priv, 'requested' => $params['resource_priv']]);
            } else {
                $update_params['resource_priv'] = $params['resource_priv'];
            }
        }

        // validate ttime limit
        if (isset($params['time_limit'])) {
            $update_params['time_limit'] = trim($params['time_limit']);
        }
        // validate status
        if (isset($params['status'])) {
            $update_params['status'] = trim($params['status']);
        }

        DBService::clearCache('Collection-getCollectionAccessCodes-' . $user_id);
        DBService::clearCache('Collection-ofUser:' . $user_id);
        DBService::clearCache('User-listAll:' . $user_id);

        if (count($update_params) > 0) {
            parent::update($user_id, $update_params);
            
        }

        if (isset($params['collection_details'])) {
            foreach ($params['collection_details'] as $collection_id => $priv) {
                switch ($priv) {
                    case 0: // always possible
                        Collection::setCollectionAccessCode($user_id, $collection_id, 0);
                        break;
                    case 1:
                        if (Collection::userCan($collection_id, AuthService::get(), Scope::VIEW)) {
                            Collection::setCollectionAccessCode($user_id, $collection_id, 1);
                        } else {
                            ResponseService::throw(APIError::E_INPUT_MORE_RIGHTS_THAN_SELF, ['type' => 'User', 'id' => $user_id, 'collection' => $collection_id, 'requested' => $priv]);
                        }
                        break;
                    case 2:
                        if (Collection::userCan($collection_id, AuthService::get(), Scope::EDIT)) {
                            Collection::setCollectionAccessCode($user_id, $collection_id, 2);
                        } else {
                            ResponseService::throw(APIError::E_INPUT_MORE_RIGHTS_THAN_SELF, ['type' => 'User', 'id' => $user_id, 'collection' => $collection_id, 'requested' => $priv]);
                        }
                        break;
                    default:
                        # silently fail
                        break;
                }
            }
        }

        if ($user_id == AuthService::$id) {
            AuthService::update();
        } else {
            AuthService::logoutUser($user_id);
        }

        return 0;

    }

    /*

    Calculating permissions according to access level

     */

    public static function userCan($user_id, User $user, int $action): bool
    {

        /*
        r = read access
        w = write access
        c = can create

        GLOBAL RIGHTS: defined by user->user_priv
          r w c
        0 x x x
        1 y x x
        2 y y y
        
        */

        if ($user_id == 'all' && $action == Scope::VIEW) {
            return true;
        }

        switch ($action) {
            case Scope::VIEW:
                return $user->user_priv >= 1 || $user->id == $user_id;
                break;
            case Scope::EDIT:
                return $user->user_priv == 2 || $user->id == $user_id;
                break;
            case Scope::CREATE:
                return $user->user_priv == 2;
            default:
                ResponseService::throw(APIError::E_SERVER_UNKNOWN_PERMISSION_REQUEST);
                return false;
                break;
        }
    }

}
