<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );

require_once 'response.php';

// handle fatal server errors by sending message to user
register_shutdown_function(array('ResponseService', 'handleFatalPhpError'));

// Angular sends OPTION prefly for CORS requests
if (strtolower($_SERVER['REQUEST_METHOD']) == 'options') {
    ResponseService::send('', 200);
}

// JSON data accessible via POST
$json_str = file_get_contents('php://input');
$_POST = json_decode($json_str, true);

// include files
require_once 'dbservice.php';
require_once 'auth.php';
require_once 'route.php';
require_once 'user.php';
require_once 'collection.php';
require_once 'image.php';
require_once 'index_manager.php';
require_once 'upload.php';
require_once 'search.php';
require_once 'job.php';
require_once 'config.php';

// helping function for paginating requests
function get_limits()
{
    $limits = [];
    if (isset($_GET['from']) && isset($_GET['to'])) {
        $limits = [intval($_GET['from']), intval($_GET['to'])];
    }
    return $limits;
}

// Init the routing algorithm
Scope::init('/api');

/*

Authentication Scope

 */

$auth_scope = new Scope('auth', 0);

// define capability functions

// require authenticated user
$auth_scope->can[Scope::VIEW] = function () {
    AuthService::get();
    return true;
};

// get data of authenticated user
$auth_scope->addRoute('/check', function () {
    ResponseService::send([
        "data" => AuthService::get(),
        "total" => 1,
    ], 200);
}, 'get', [Scope::VIEW]);

// reload user data from database and update session variable
// useful for permission updates
$auth_scope->addRoute('/refresh', function () {
    AuthService::update();
}, 'get', [Scope::VIEW]);

// login
$auth_scope->addRoute('/login', function () {
    $username = $_POST["username"];
    $password = $_POST["password"];
    $time = $_POST["time"];
    ResponseService::send(AuthService::login($username, $password, $time), 200);
}, 'post', []);

// logout
$auth_scope->addRoute('/logout', function () {
    AuthService::logout();
    ResponseService::send('', 200);
}, 'get', [Scope::VIEW]);

// clear current cache & workers!
$auth_scope->addRoute('/clearcache', function () {
    apcu_clear_cache();
    ResponseService::send('Cache cleared', 200);
}, 'post', [Scope::VIEW]);

// run scope
$auth_scope->run();

/*

Job Scope

 */

$job_scope = new Scope('job', 1);

// define capability functions

$job_scope->can[Scope::ISWORKER] = function ($params) {
    global $api_secret;
    if ($_POST["token"] != $api_secret) {
        ResponseService::throw(APIError::E_WRONG_API_KEY);
    }
    // store worker in cache if not exists
    $id = $params[0];
    if (!apcu_exists('ISE_WORKER:' . $id)) {
        apcu_store('ISE_WORKER:' . $id, array(
            "id" => $id,
            "current_job" => null,
            "status" => 0,
            "last_update" => time(),
            "type" => $_POST["type"],
            "description" => $_POST["description"],
        ), 3 * 3600);
    }
    return true;
};
// authenticated user
$job_scope->can[Scope::VIEW] = function ($params) {
    return Job::userCan(AuthService::get(), Scope::VIEW);
};
$job_scope->can[Scope::EDIT] = function ($params) {
    return Job::userCan(AuthService::get(), Scope::EDIT);
};

// receive updates from worker
$job_scope->addRoute('/update', function ($id) {
    ResponseService::send(Job::updateWorkerStatus($id, $_POST), 200);
}, 'post', [Scope::ISWORKER]);
// get info on workers
$job_scope->addRoute('/info', function ($id) {
    ResponseService::send(Job::getWorkers(), 200);
}, 'get', [Scope::VIEW]);
// get running jobs
$job_scope->addRoute('/running', function ($id) {
    ResponseService::send(Job::getRunningJobs(), 200);
}, 'get', [Scope::VIEW]);
// get pending jobs
$job_scope->addRoute('/pending', function ($id) {
    ResponseService::send(Job::getPendingJobs(), 200);
}, 'get', [Scope::VIEW]);
// get finished jobs
$job_scope->addRoute('/finished', function ($id) {
    ResponseService::send(Job::getFinishedJobs(), 200);
}, 'get', [Scope::VIEW]);
// cancel a job
$job_scope->addRoute('/cancel/([0-9]+)', function ($id, $type) {
    ResponseService::send(Job::updateJobItem($id, $type, [
        "status" => -1,
    ]), 200);
}, 'get', [Scope::EDIT]);

$job_scope->run();

/*

Collections scope

 */
$collection_scope = new Scope('collection', 1);

// define capability functions
$collection_scope->can[Scope::VIEW] = function ($params) {
    return Collection::userCan($params[0], AuthService::get(), Scope::VIEW);
};
$collection_scope->can[Scope::EDIT] = function ($params) {
    return Collection::userCan($params[0], AuthService::get(), Scope::EDIT);
};
$collection_scope->can[Scope::CREATE] = function ($params) {
    return Collection::userCan(0, AuthService::get(), Scope::CREATE);
};

// list all collections of user
$collection_scope->addRoute('/list', function ($collection_id) {
    ResponseService::send(Collection::ofUser(AuthService::$id, get_limits()), 200);
}, 'get', [Scope::VIEW]);
// create new collection
$collection_scope->addRoute('/new', function ($collection_id) {
    $title = $_POST["title"];
    $comment = (isset($_POST["comment"])) ? $_POST["comment"] : '';
    ResponseService::send(Collection::new ($title, $comment), 200);
}, 'post', [Scope::CREATE]);
// get info on specific collection
$collection_scope->addRoute('/info', function ($collection_id) {
    ResponseService::send(Collection::getByID($collection_id), 200);
}, 'get', [Scope::VIEW]);
// remove collection
$collection_scope->addRoute('/remove', function ($collection_id) {
    ResponseService::send(Collection::update($collection_id, ['status' => 9]), 200);
}, 'get', [Scope::EDIT]);
// recover collection
$collection_scope->addRoute('/recover', function ($collection_id) {
    ResponseService::send(Collection::update($collection_id, ['status' => 0]), 200);
}, 'get', [Scope::EDIT]);
// update meta information on collection
$collection_scope->addRoute('/update', function ($collection_id) {
    ResponseService::send(Collection::update($collection_id, $_POST, true), 200);
}, 'post', [Scope::EDIT]);
// get images of a collection
$collection_scope->addRoute('/images', function ($collection_id) {
    // search keyword
    $query = (isset($_GET['query'])) ? $_GET['query'] : '';

    // get specified year range
    $year_range = [];
    if (isset($_GET['year_from']) || isset($_GET['year_to'])) {
        $year_range[] = (isset($_GET['year_from'])) ? intval($_GET['year_from']) : -1000;
        $year_range[] = (isset($_GET['year_to'])) ? intval($_GET['year_to']) : 5000;
    }
    ResponseService::send(Image::ofCollection($collection_id, 0, true, get_limits(), $query, $year_range), 200);
}, 'get', [Scope::VIEW]);
// get trash
$collection_scope->addRoute('/trash', function ($collection_id) {
    ResponseService::send(Image::ofCollection($collection_id, 9, true, $limits, '', []), 200);
}, 'get', [Scope::VIEW]);

// upload files to a a collection
$collection_scope->addRoute('/upload', function ($collection_id) {
    ResponseService::send(UploadService::processFile($collection_id), 200);
}, 'post', [Scope::EDIT]);
// list indices of a collection
$collection_scope->addRoute('/indices', function ($collection_id) {
    ResponseService::send(Index::ofCollection($collection_id), 200);
}, 'get', [Scope::VIEW]);
// create an index inside this collection
$collection_scope->addRoute('/indices/create', function ($collection_id) {
    ResponseService::send(Index::new ($collection_id, $_POST), 200);
}, 'post', [Scope::EDIT]);
// get available index types --> TD: why collection specific?
$collection_scope->addRoute('/indices/types', function ($collection_id) {
    ResponseService::send(Index::getSupportedIndexTypes(), 200);
}, 'get', [Scope::VIEW]);
// get searches of a collection
$collection_scope->addRoute('/searches', function ($collection_id) {
    $query = (isset($_GET['query'])) ? $_GET['query'] : '';
    ResponseService::send(Search::ofCollection($collection_id, $query, get_limits()), 200);
}, 'get', [Scope::VIEW]);
// get data to review of a collection
$collection_scope->addRoute('/searches/review', function ($collection_id) {
    $indexids = (isset($_GET['index'])) ? explode(',', $_GET['index']) : [];
    $searchids = (isset($_GET['search'])) ? explode(',', $_GET['search']) : [];
    $max_retrievals = (isset($_GET['max_retrievals']) && $_GET['max_retrievals'] != 'null') ? $_GET['max_retrievals'] : 100;
    ResponseService::send(SearchResult::unreviewedOf($collection_id, $indexids, $searchids, $max_retrievals), 200);
}, 'get', [Scope::EDIT]);

$collection_scope->run();

/*

Image Files
--> Serves the images

 */
$img_file_scope = new Scope('img', 1);
$img_file_scope->can[Scope::VIEW] = function ($params) {
    return Collection::userCan($params[0], AuthService::get(), Scope::VIEW);
};
$img_file_scope->addRoute('/full/([a-zA-Z0-9\._]+)', function ($collection_id, $image_name) {
    Image::show($collection_id, $image_name);
}, 'get', [Scope::VIEW]);

$img_file_scope->addRoute('/thumb/([a-zA-Z0-9\._]+)', function ($collection_id, $image_name) {
    Image::show($collection_id, $image_name, 'thumbs');
}, 'get', [Scope::VIEW]);

$img_file_scope->run();

/*

Image Endpoints

 */

$image_scope = new Scope('image', 1);
// capability functions
$image_scope->can[Scope::VIEW] = function ($params) {
    $collection_id = Image::getByID($params[0])->collection_id;
    return Collection::userCan($collection_id, AuthService::get(), Scope::VIEW);
};
$image_scope->can[Scope::EDIT] = function ($params) {
    $collection_id = Image::getByID($params[0])->collection_id;
    return Collection::userCan($collection_id, AuthService::get(), Scope::EDIT);
};
// get info of an image
$image_scope->addRoute('/info', function ($image_id) {
    ResponseService::send(Image::getByID($image_id), 200);
}, 'get', [Scope::VIEW]);
// update meta information of image
$image_scope->addRoute('/update', function ($image_id) {
    ResponseService::send(Image::update($image_id, $_POST, true), 200);
}, 'post', [Scope::EDIT]);
// delete image
$image_scope->addRoute('/remove', function ($image_id) {
    ResponseService::send(Image::remove($image_id), 200);
}, 'get', [Scope::EDIT]);
// recover image
$image_scope->addRoute('/recover', function ($image_id) {
    ResponseService::send(Image::recover($image_id), 200);
}, 'get', [Scope::EDIT]);
// get searches the image occurs in
$image_scope->addRoute('/retrievals', function ($image_id) {
    $query = (isset($_GET['query'])) ? $_GET['query'] : '';
    ResponseService::send(Search::ofImage($image_id, $query, get_limits()), 200);
}, 'get', [Scope::VIEW]);
// get searches of this image
$image_scope->addRoute('/searches', function ($image_id) {
    $query = (isset($_GET['query'])) ? $_GET['query'] : '';
    ResponseService::send(Search::inImage($image_id, $query, get_limits()), 200);
}, 'get', [Scope::VIEW]);

$image_scope->run();

/*

Index endpoints

 */

$index_scope = new Scope('index', 1);
// capability functions
$index_scope->can[Scope::VIEW] = function ($params) {
    $collection_id = Index::getByID($params[0])->collection_id;
    return Collection::userCan($collection_id, AuthService::get(), Scope::VIEW);
};
$index_scope->can[Scope::EDIT] = function ($params) {
    $collection_id = Index::getByID($params[0])->collection_id;
    return Collection::userCan($collection_id, AuthService::get(), Scope::EDIT);
};
// get info of single index
$index_scope->addRoute('/info', function ($index_id) {
    ResponseService::send(Index::getByID($index_id), 200);
}, 'get', [Scope::VIEW]);
// update meta information
$index_scope->addRoute('/update', function ($index_id) {
    ResponseService::send(Index::update($index_id, $_POST, true), 200);
}, 'post', [Scope::EDIT]);
// rerun if images changed
$index_scope->addRoute('/rerun', function ($index_id) {
    ResponseService::send(Index::rerun($index_id), 200);
}, 'get', [Scope::EDIT]);
// cancel running
$index_scope->addRoute('/stop', function ($index_id) {
    ResponseService::send(Index::stop($index_id), 200);
}, 'get', [Scope::EDIT]);
// create new search on this index
$index_scope->addRoute('/searches/create', function ($index_id) {
    ResponseService::send(Search::new ($index_id, $_POST), 200);
}, 'post', [Scope::EDIT]);

$index_scope->run();

/*

Search endpoints

 */

$search_scope = new Scope('search', 1);
// capability functions
$search_scope->can[Scope::VIEW] = function ($params) {
    $collection_id = Search::getByID($params[0])->collection_id;
    return Collection::userCan($collection_id, AuthService::get(), Scope::VIEW);
};
$search_scope->can[Scope::EDIT] = function ($params) {
    $collection_id = Search::getByID($params[0])->collection_id;
    return Collection::userCan($collection_id, AuthService::get(), Scope::EDIT);
};
// refine search with votes and improvements
$search_scope->addRoute('/refine', function ($search_id) {
    ResponseService::send(Search::refineSearch($search_id), 200);
}, 'get', [Scope::EDIT]);
// get results of search
$search_scope->addRoute('/results', function ($search_id) {
    ResponseService::send(SearchResult::ofSearch($search_id, null, get_limits()), 200);
}, 'get', [Scope::VIEW]);
// get favorites of search
$search_scope->addRoute('/favorites', function ($search_id) {
    ResponseService::send(SearchFavorite::ofSearch($search_id, null, get_limits()), 200);
}, 'get', [Scope::VIEW]);
// update favorites
$search_scope->addRoute('/favorites/update', function ($search_id) {
    ResponseService::send(SearchFavorite::update($search_id, $_POST['new_favorites']), 200);
}, 'post', [Scope::VIEW]);
// get siblings of search
$search_scope->addRoute('/siblings', function ($search_id) {
    ResponseService::send(Search::getSiblings($search_id), 200);
}, 'get', [Scope::VIEW]);
// get related searches
$search_scope->addRoute('/related', function ($search_id) {
    ResponseService::send(Search::getRelated($search_id), 200);
}, 'get', [Scope::VIEW]);
// update meta information
$search_scope->addRoute('/update', function ($search_id) {
    ResponseService::send(Search::update($search_id, $_POST, true), 200);
}, 'post', [Scope::EDIT]);
$search_scope->run();

/*

Search results endpoints

 */
$searchresult_scope = new Scope('searchresult', 1);
// capability functions
$searchresult_scope->can[Scope::EDIT] = function ($params) {
    $search_id = SearchResult::getByID($params[0])->search_id;
    $search_data = Search::getByID($search_id);
    $collection_id = $search_data->collection_id;
    return Collection::userCan($collection_id, AuthService::get(), Scope::EDIT);
};
// change vote
$searchresult_scope->addRoute('/vote', function ($searchresult_id) {
    ResponseService::send(SearchResult::vote($searchresult_id, $_POST['vote']), 200);
}, 'post', [Scope::EDIT]);
// save refinement
$searchresult_scope->addRoute('/refine', function ($searchresult_id) {
    ResponseService::send(SearchResult::refine($searchresult_id, $_POST['refinement']), 200);
}, 'post', [Scope::EDIT]);

$searchresult_scope->run();

/*

User scope

 */
$user_scope = new Scope('user', 1);
// define capabiliity functions
$user_scope->can[Scope::VIEW] = function ($params) {
    return User::userCan($params[0], AuthService::get(), Scope::VIEW);
};
$user_scope->can[Scope::EDIT] = function ($params) {
    return User::userCan($params[0], AuthService::get(), Scope::EDIT);
};
$user_scope->can[Scope::CREATE] = function ($params) {
    return User::userCan(0, AuthService::get(), Scope::CREATE);
};

// create user
$user_scope->addRoute('/new', function ($user_id) {
    // $user_id must be 'all'
    $user_id = User::new ($_POST['name'], date('Y-m-d H:i:s'), $_POST['password'], 1, 1, 1);
    ResponseService::send($user_id, 200);
}, 'post', [Scope::CREATE]);
// list users
$user_scope->addRoute('/list', function ($user_id) {
    ResponseService::send(User::listAll(get_limits()), 200);
}, 'get', [Scope::VIEW]);
// get info for a given user
$user_scope->addRoute('/info', function ($user_id) {
    // TD
    ResponseService::send([
        "data" => User::editInfo($user_id),
        "total" => 1,
    ], 200);
}, 'get', [Scope::VIEW]);
// update infos for user
$user_scope->addRoute('/update', function ($user_id) {
    ResponseService::send(User::update($user_id, $_POST, true), 200);
}, 'post', [Scope::EDIT]);

$user_scope->run();

Scope::finish();
