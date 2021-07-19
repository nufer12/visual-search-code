<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


abstract class APIError
{
    const E_SERVER_GENERAL_ERROR = [50000, 'Unknown Server error'];
    const E_SERVER_PDO_ERROR = [50001, 'Database Error'];
    const E_SERVER_UNKNOWN_PERMISSION_REQUEST = [50002, 'Unknown Permission Request'];
    const E_SERVER_CREATE_FOLDERS = [50003, 'Could not create folder structure'];
    const E_SERVER_UPLOAD_OPEN_ZIP = [50004, 'Could not open ZIP folder'];

    const E_AUTH = [40101, 'Authentication Error'];
    const E_AUTH_REPLAY = [40102, 'Timeout Error'];
    const E_AUTH_BLOCKED =  [40103, 'User blocked'];
    const E_AUTH_LOGIN_TIME_LIMIT = [40104, 'Time limit reached'];
    const E_AUTH_LOGIN_NAME_OR_PASSWORD = [40105, 'Username or Password incorrect'];
    const E_AUTH_NOT_GRANTED = [40106, 'Missing permissions for route'];

    const E_INPUT_REQUIRED_FIELD_MISSING = [40601, 'Required Field missing'];
    const E_INPUT_REQUIRED_FIELD_WRONG = [40601, 'Required Field not acceptable'];
    const E_INPUT_INDEX_RUNNING = [40602, 'Calculation is running.'];
    const E_INPUT_INDEX_NO_UPDATE_REQUIRED = [40603, 'Filter does not require an update'];
    const E_INPUT_NOTHING_TO_STOP = [40604, 'No job to stop'];
    const E_INPUT_UPLOAD_EMPTY = [40605, 'Input is empty'];
    const E_INPUT_UPLOAD_TOO_LARGE = [40606, 'Upload too large'];
    const E_INPUT_UPLOAD_UNKNOWN = [40607, 'Unknown upload type'];
    const E_INPUT_UPDATE_ONLY_SELF = [40608, 'This can only be updated by the user'];
    const E_INPUT_MORE_RIGHTS_THAN_SELF = [40609, 'Can not grant more rights than self'];


    const E_METHOD_NOTALLOWED = [40501, 'Method not allowed'];
    
    const E_NOTFOUND_PATH = [40401, 'Route not found in scope'];
    const E_NOTFOUND_SCOPE = [40402, 'Scope not found'];

}

class ResponseService
{
    function throw (array $code, $data = null) {
        ResponseService::send(array(
            "message" => $code[1],
            "error_code" => $code[0],
            "data" => $data,
        ), intval($code[0] / 100));
    }

    public static function send($data, int $status_code)
    {
        header('Content-Type: application/json;charset=utf-8');
        http_response_code($status_code);
        echo json_encode($data, JSON_NUMERIC_CHECK);
        exit();
    }

    public static function handleFatalPhpError()
    {
        $last_error = error_get_last();
        if ($last_error['type'] === E_ERROR) {
            ResponseService::throw(APIError::E_SERVER_GENERAL_ERROR, $last_error);
        }
    }

    public static function serveImage(string $filename)
    {
        $ntct = array("1" => "image/gif", "2" => "image/jpeg", "3" => "image/png", "6" => "image/bmp", "17" => "image/ico");
        header('Content-type: ' . $ntct[exif_imagetype($filename)]);
        readfile($filename);
        exit();
    }

    public static function serveJson(string $filename)
    {
        header('Content-type: application/json;charset=utf-8');
        readfile($filename);
        exit();
    }

    public static function serveJsonString(string $string)
    {
        header('Content-type: application/json;charset=utf-8');
        echo $string;
        exit();
    }
}
