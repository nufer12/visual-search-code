<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


require_once 'auth.php';
class Scope
{

    // possible capabilities
    const VIEW = 0;
    const EDIT = 1;
    const CREATE = 2;
    const ISWORKER = 4;

    public $name;
    public $expression;
    public $routes = array();
    public $can = array();

    public static $basepath = '/';
    public static $path = '';
    public static $method = '';

    public static $routeNotFound = null;
    public static $methodNotAllowed = null;
    public static $scopeNotFound = null;

    public static $scopeWasFound = false;

    public static function init($base = '/')
    {
        // Parse current url
        $parsed_url = parse_url($_SERVER['REQUEST_URI']); //Parse Uri
        if (isset($parsed_url['path'])) {
            // do not make a difference between example.de/url and example.de/url/
            if (substr($parsed_url['path'], -1) == '/') {
                self::$path = substr($parsed_url['path'], 0, -1);
            } else {
                self::$path = $parsed_url['path'];
            }
        } else {
            self::$path = '/';
        }
        // remove double slashes
        self::$path = str_replace('//', '/', self::$path);
        self::$method = $_SERVER['REQUEST_METHOD'];
        self::$basepath = $base;
    }

    public function __construct($name, $num_params)
    {
        $this->name = $name;
        // create expression
        $this->expression = '/' . $name . str_repeat('/([^/]+)', $num_params);
        if (self::$basepath != '/') {
            $this->expression = Scope::$basepath . $this->expression;
        }
        $this->expression = '^' . $this->expression;
    }

    public function addRoute(string $expression, callable $function, string $method, array $needed_perm)
    {
        array_push($this->routes, array(
            'expression' => $this->expression . $expression . '$', // route specific expression
            'function' => $function, // the callback
            'method' => $method, // GET or POST
            'needed_perm' => $needed_perm, // the capabilities it requires
        ));
    }

    public function run()
    {
        // early return if base expression not matches
        if (!preg_match('#' . $this->expression . '#', self::$path, $matches)) {
            return false;
        }
        self::$scopeWasFound = true;

        $routeWasFound = false;
        $methodIsAllowed = false;
        foreach ($this->routes as $route) {
            // Check path match
            if (preg_match('#' . $route['expression'] . '#', self::$path, $matches)) { // route was found
                $routeWasFound = true;
                // Check method match
                if (strtolower(self::$method) == strtolower($route['method'])) {
                    $methodIsAllowed = true;
                    self::$scopeWasFound = true;
                    array_shift($matches); // Always remove first element. This contains the whole string

                    // everything matches. now check permissions
                    foreach ($route['needed_perm'] as $perm) {
                        if (!isset($this->can[$perm])) {
                            ResponseService::throw(APIError::E_SERVER_UNKNOWN_PERMISSION_REQUEST, ['requested' => $perm]);
                        } else {
                            $granted = call_user_func_array($this->can[$perm], [$matches]);
                            if (!$granted) {
                                ResponseService::throw(APIError::E_AUTH_NOT_GRANTED, ['requested' => $perm]);
                            }
                        }
                    }

                    // now call the callback
                    call_user_func_array($route['function'], $matches);
                    break;
                }
            }
        }

        // if method was not allowed...
        if (!$methodIsAllowed) {
            // ...but a matching path exists
            if ($routeWasFound) {
                ResponseService::throw(APIError::E_METHOD_NOTALLOWED);
            } else {
                ResponseService::throw(APIError::E_NOTFOUND_PATH);
            }
        }
    }

    public static function finish()
    {
        // check if a scope was found
        if (!self::$scopeWasFound) {
            ResponseService::throw(APIError::E_NOTFOUND_SCOPE);
        }
    }

}
