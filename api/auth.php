<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


require_once 'user.php';
require_once 'response.php';

/*

Authentication service

 */

// for non cookie support
if (isset($_GET["token"]) && $_GET["token"] != "") {
    session_id($_GET["token"]);
}
session_start();

abstract class AuthService
{

    private static $user = null; // user object
    public static $id = null; // id of authenticated user

    public static function get(): User
    {
        if (self::$user == null) {
            // check if stored in session
            if (isset($_SESSION['ise_user_data'])) {
                $user = User::jsonDeserialize($_SESSION['ise_user_data']);
                // check if sessions user object is valid
                if ($user !== null && $user->id > 0) {
                    self::$user = $user;
                    self::$id = $user->id;
                } else { // else throw authentication error
                    ResponseService::throw(APIError::E_AUTH);
                    return null;
                }
            } else { // else throw authentication error
                ResponseService::throw(APIError::E_AUTH);
                return null;
            }
        }
        return self::$user;
    }

    public static function set(User $user)
    {
        // store user in session data and service
        self::$id = $user->id;
        $_SESSION['ise_user_data'] = $user->jsonSerialize();
        self::$user = $user;
    }

    public static function update()
    {
        // reload data from database
        // important if permissions changed
        $user = User::getByID(self::$user->id);
        AuthService::set($user);
    }

    public static function login(string $username, string $password, string $timestamp): User
    {
        // load user from database
        $user = User::getByUserName($username);
        // avoid timeouts and replay attacks
        if (time() > intval($timestamp) + 300) {
            ResponseService::throw(APIError::E_AUTH_REPLAY);
            return null;
        }
        // is user allowed to login?
        if ($user->status == 9) {
            ResponseService::throw(APIError::E_AUTH_BLOCKED);
            return null;
        }
        // time limit over?
        $today = date("Y-m-d");
        if ($today > $user->time_limit) {
            ResponseService::throw(APIError::E_AUTH_LOGIN_TIME_LIMIT);
            return null;
        }

        // get hashes of passwords and compare
        $password_hash = trim($password);
        $password_db = md5($user->password . $timestamp);
        if ($password_hash == $password_db) {
            // generate new session id === token
            // and save for user
            session_regenerate_id(true);
            AuthService::set($user);
            User::setSessionID($user->id, session_id());
            return $user;
        } else {
            // handle as logout
            AuthService::logout();
            ResponseService::throw(APIError::E_AUTH_LOGIN_NAME_OR_PASSWORD);
            return null;
        }
    }

    public static function logout(): void
    {
        // destroy session and info in service
        self::$user = null;
        session_destroy();
    }

    public static function logoutUser($user_id): void
    {
        // logout another user by destroying his session
        $user = User::getByID($user_id);
        session_id($user->session_id);
        session_start();
        session_regenerate_id(true);
        User::setSessionID($user_id, '');
    }

}
