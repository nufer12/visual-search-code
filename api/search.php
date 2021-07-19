<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


require_once 'response.php';
require_once 'dbservice.php';

require_once 'util.php';
require_once 'auth.php';
require_once 'group.php';

class Search extends DatabaseInterface implements JsonSerializable
{

    public $id;
    public $name;
    public $index_id;
    public $collection_id;
    public $refined_search;
    public $base_search;
    public $creator_id;
    public $creator;
    public $creation_date;
    public $score;
    public $total_hits;
    public $image_id;
    public $query_bbox;
    public $filename;
    public $group_id;
    public $params;
    public $start_time;
    public $end_time;
    public $exitcode;
    public $worker_id;

    // const updateable_values = ['name', 'status', 'refined_search', 'base_search', 'score', 'total_hits', 'job', 'group_id', 'params', 'start_time', 'end_time', 'exitcode', 'worker_id'];
    const updateable_values = ['name'];
    const table_name = 'vis_searches';

    public function jsonSerialize()
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'index_id' => $this->index_id,
            'base_search' => $this->base_search,
            'refined_search' => $this->refined_search,
            'collection_id' => $this->collection_id,
            'creator_id' => $this->creator_id,
            'creator' => User::getUserName($this->creator_id),
            'creation_date' => $this->creation_date,
            'status' => $this->status,
            'score' => $this->score,
            'total_hits' => $this->total_hits,
            'image_id' => $this->image_id,
            'query_bbox' => $this->query_bbox,
            'params' => $this->params,
            'filename' => $this->filename,
            'group' => $this->group_id,
            'params' => $this->params,
            'start_time' => $this->start_time,
            'end_time' => $this->end_time,
            'exitcode' => $this->exitcode,
            'worker_id' => $this->worker_id,
        ];
    }

    public static function getDBValuesForNew($params): array
    {
        // be careful: parent::new get other values as Search::new
        return [
            'id' => null,
            'name' => $params[4],
            'index_id' => $params[1],
            'collection_id' => $params[0],
            'refined_search' => null,
            'base_search' => $params[2],
            'creator_id' => AuthService::$id,
            'creation_date' => date('Y-m-d H:i:s'),
            'score' => 0,
            'total_hits' => 0,
            'image_id' => $params[5],
            'query_bbox' => $params[3],
            'params' => $params[6],
            'status' => 0,
            'group_id' => null,
            'start_time' => null,
            'end_time' => null,
            'exitcode' => null,
            'worker_id' => $params[7],
        ];
    }

    public static function new (...$params): int {

        // convert search_boxes if necessary
        $index_id = $params[0];
        $settings = $params[1];
        if (is_array($settings['search_boxes'])) {
            $settings['search_boxes'] = json_encode($settings['search_boxes']);
        }

        // get collection id
        $collection_id = Index::getByID($index_id)->collection_id;
        $settings['params']['pos'] = 0;
        $settings['params']['neg'] = 0;

        $machine_id = (isset($settings["machine"])) ? $settings["machine"] : -1;

        // save on database
        $search_id = parent::new ($collection_id, $index_id, null, $settings['search_boxes'], $settings['name'], $settings['image_id'], json_encode($settings['params']), $machine_id);


        $retrievalDir = _DATA_ . 'images_' . $collection_id . DIRECTORY_SEPARATOR . 'index_' . $index_id . DIRECTORY_SEPARATOR . 'retrieval';
        if (!file_exists($retrievalDir)) {
            mkdir($retrievalDir, 0777, true);
        }
        $mainDirectory = $retrievalDir . DIRECTORY_SEPARATOR . 'search_' . $search_id;
        $flag0 = mkdir($mainDirectory, 0777, true);
        if (!$flag0) {
            Search::update($search_id, ['status' => 9]);
            ResponseService::throw(APIError::E_SERVER_CREATE_FOLDERS, ['type' => 'search', 'id' => 'new']);
        }

        // save configuration
        $default_config_data = array(
            "image" => intval($settings['image_id']),
            "boxes" => json_decode($settings['search_boxes']),
            "params" => $settings['params'],
            "positives" => array(),
            "negatives" => array(),
        );
        file_put_contents($mainDirectory . DIRECTORY_SEPARATOR . "config.json", json_encode($default_config_data, JSON_UNESCAPED_SLASHES | 1024));

        // if this was created by relation
        if ($settings['related']) {
            // get related search
            $related_search = Search::getByID($settings['related']);
            $group_id = 0;
            // if related search is inside group add new search to this, else create group and add both to it
            if (!$related_search->group_id) {
                $group_id = Group::new ($collection_id, '', 1);
                Search::update($settings['related'], ['group_id' => $group_id]);
            } else {
                $group_id = $related_search->group_id;
            }
            Search::update($search_id, ['group_id' => $group_id]);
            Group::addToCounter($group_id);
        }

        DBService::clearCache('Search-ofCollection');
        // CACHE: set in Search::ofCollection
        DBService::clearCache('Search-ofImage:'.$settings['image_id']);
        // CACHE: set in Search::ofImage
        DBService::clearCache('Search-inImage'.$settings['image_id']);
        // CACHE: set in Search::inImage
        DBService::clearCache('Search-related');
        // CACHE: set in Search::related
        DBService::clearCache('Search-siblings');
        // CACHE: set in Search::siblings

        return $search_id;
    }

    public static function refineSearch($base_search_id, $make_run = true)
    {
        // get info of base search
        $search_info = Search::getByID($base_search_id);
        $collection_id = $search_info->collection_id;
        $index_id = $search_info->index_id;

        // load new positives and negatives
        $new_positives = SearchResult::ofSearchForRefinement($base_search_id, 1);
        $new_negatives = SearchResult::ofSearchForRefinement($base_search_id, -1);
        // load params from old search
        $params = json_decode($search_info->params, true);
        $machine_id = (isset($settings["machine"])) ? $settings["machine"] : -1;
        // create database entry
        $search_id = parent::new ($collection_id, $index_id, $base_search_id, $search_info->query_bbox, $search_info->name, $search_info->image_id, "", $machine_id);
        // update base search and add id of new search to refined searches
        $current_ids = json_decode($search_info->refined_search, true);
        $current_ids[] = $search_id;
        Search::update($base_search_id, array('refined_search' => json_encode($current_ids)));

        // create folders
        $retrievalDir = _DATA_ . 'images_' . $collection_id . DIRECTORY_SEPARATOR . 'index_' . $index_id . DIRECTORY_SEPARATOR . 'retrieval';
        $mainDirectory = $retrievalDir . DIRECTORY_SEPARATOR . 'search_' . $search_id;
        $flag0 = mkdir($mainDirectory, 0777);
        if (!$flag0) {
            ResponseService::throw(APIError::E_SERVER_CREATE_FOLDERS, ['type' => 'search', 'id' => $base_search_id]);
        }

        // copy configuration
        $conf = json_decode(file_get_contents($retrievalDir . DIRECTORY_SEPARATOR . 'search_' . $base_search_id . DIRECTORY_SEPARATOR . 'config.json'), true);
        $conf["positives"] = array_merge($conf["positives"], $new_positives);
        $conf["negatives"] = array_merge($conf["negatives"], $new_negatives);
        $params["pos"] = count($conf["positives"]);
        $params["neg"] = count($conf["negatives"]);

        $conf["params"] = $params;

        file_put_contents($mainDirectory . DIRECTORY_SEPARATOR . "config.json", json_encode($conf, JSON_UNESCAPED_SLASHES | 1024));
        Search::update($search_id, ['params' => json_encode($params)]);
        // CACHE: this updates ofCollection, ofImage, inImage, related and siblings

        return $search_id;
    }

    public static function ofCollection($collection_id, $filter = '', $limits = [])
    {
        $filter_cond = ($filter == '') ? '' : ' AND MATCH(`' . implode('`, `', ['name']) . '`) AGAINST (:matching IN BOOLEAN MODE)';
        $bindings = [
            ":collectionid" => $collection_id,
        ];
        if ($filter != "") {
            $bindings[':matching'] = $filter . '*';
        }
        return DBService::getData(
            'Search-ofCollection:' . $collection_id, // gets updated at Search::new, Search::update, SearchResult::parseResultJSON
            "SELECT `vis_searches`.*, `vis_images`.`filename`, `vis_users`.`name` AS creator FROM `vis_searches` INNER JOIN `vis_images` ON `vis_images`.`id` = `vis_searches`.`image_id` INNER JOIN `vis_users` ON `vis_users`.`id` = `vis_searches`.`creator_id` WHERE `vis_searches`.`collection_id` = :collectionid AND `vis_searches`.`status` != 9" . $filter_cond . " ORDER BY `vis_searches`.`creation_date` DESC",
            $bindings,
            [PDO::FETCH_CLASS, __CLASS__],
            $limits
        );
        // CACHE: cleared in
        // - Search::new
        // - Search::update
        // - Search::refine
        // - Search::parseResultJSON

    }

    public static function ofImage($image_id, $filter = '', $limits = []): array
    {
        $filter_cond = ($filter == '') ? '' : ' AND MATCH(`' . implode('`, `', ['name']) . '`) AGAINST (:matching IN BOOLEAN MODE)';
        $bindings = [
            ":imageid" => $image_id,
        ];
        if ($filter != "") {
            $bindings[':matching'] = $filter . '*';
        }
        return DBService::getData(
            'Search-ofImage:' . $image_id, // gets updated at SearchResult::parseResultJSON
            "SELECT DISTINCT `vis_searches`.*, `vis_images`.`filename` FROM `vis_searches` INNER JOIN `vis_images` ON `vis_images`.`id` = `vis_searches`.`image_id` INNER JOIN `vis_search_results` ON `vis_searches`.`id` = `vis_search_results`.`search_id` WHERE `vis_search_results`.`image_id` = :imageid AND `vis_searches`.`status` != 9" . $filter_cond . " ORDER BY `vis_searches`.`creation_date` DESC",
            $bindings,
            [PDO::FETCH_CLASS, __CLASS__],
            $limits
        );
        // CACHE: cleared in
        // - Search::new
        // - Search::update
        // - Search::refine
        // - Search::parseResultJSON
    }

    public static function inImage($image_id, $filter = '', $limits = []): array
    {
        $filter_cond = ($filter == '') ? '' : ' AND MATCH(`' . implode('`, `', ['name']) . '`) AGAINST (:matching IN BOOLEAN MODE)';
        $bindings = [
            ":imageid" => $image_id,
        ];
        if ($filter != "") {
            $bindings[':matching'] = $filter . '*';
        }
        return DBService::getData(
            'Search-inImage:' . $image_id, // gets updated at Search::new, Search::update, SearchResult::parseResultJSON
            "SELECT DISTINCT `vis_searches`.*, `vis_images`.`filename` FROM `vis_searches` INNER JOIN `vis_images` ON `vis_images`.`id` = `vis_searches`.`image_id` WHERE `vis_searches`.`image_id` = :imageid AND `vis_searches`.`status` != 9" . $filter_cond . " ORDER BY `vis_searches`.`creation_date` DESC",
            $bindings,
            [PDO::FETCH_CLASS, __CLASS__],
            $limits
        );
        // CACHE: cleared in
        // - Search::new
        // - Search::update
        // - Search::refine
        // - Search::parseResultJSON
    }

    public static function getSiblings($search_id): array
    {
        $search_data = Search::getByID($search_id);
        $bindings = [
            ":basesearch" => $search_data->base_search,
            ":searchid" => $search_id,
        ];
        return DBService::getData(
            'Search-siblings:'.$search_id,
            "SELECT * FROM `vis_searches` WHERE `base_search` = :basesearch AND `id` <> :searchid",
            $bindings,
            [PDO::FETCH_CLASS, __CLASS__],
            $limits
        );
        // CACHE: cleared in
        // - Search::new
        // - Search::update
        // - Search::refine
        // - Search::parseResultJSON
    }

    public static function getRelated($search_id): array
    {
        $search_data = Search::getByID($search_id);
        $bindings = [
            ":groupid" => $search_data->group_id,
            ":searchid" => $search_id,
        ];
        return DBService::getData(
            'Search-related:'.$search_id,
            "SELECT * FROM `vis_searches` WHERE `group_id` = :groupid AND `id` <> :searchid",
            $bindings,
            [PDO::FETCH_CLASS, __CLASS__],
            $limits
        );
        // CACHE: cleared in
        // - Search::new
        // - Search::update
        // - Search::refine
        // - Search::parseResultJSON
    }

    public static function update(int $id, array $values, $safe = false): int
    {
        $search_info = Search::getByID($id);
        DBService::clearCache('Search-ofCollection:'.$search_info->collection_id);
        // CACHE: set in Search::ofCollection
        DBService::clearCache('Search-ofImage:'.$search_info->image_id);
        // CACHE: set in Search::ofImage
        DBService::clearCache('Search-inImage'.$search_info->image_id);
        // CACHE: set in Search::inImage
        DBService::clearCache('Search-related:'.$id);
        // CACHE: set in Search::related
        DBService::clearCache('Search-siblings'.$id);
        // CACHE: set in Search::siblings
        return parent::update($id, $values, $safe);
    }

}

class SearchFavorite
{

    public static function ofSearch($search_id): array
    {
        $cache_name = 'SearchFavorite-ofSearch:' . $search_id;
        if (ENABLE_CACHE && apcu_exists($cache_name)) {
            return apcu_fetch($cache_name);
        }
        // CACHE: cleared in SearchFavorite::update
        try {

            $statement = DBService::getPDO()->prepare("SELECT `element_list` FROM `vis_search_favorites` WHERE `search_id` = :searchid AND `user_id` = :userid");
            $statement->bindValue(':searchid', $search_id);
            $statement->bindValue(':userid', AuthService::$id);
            $statement->execute();
            $favorites = $statement->fetchAll(PDO::FETCH_NUM);

            if (count($favorites) == 0) {
                return ["data" => [], "total" => 0];
            }
            $favorites = json_decode($favorites[0][0]);
            $count = count($favorites);
            $data = ["data" => $favorites, "total" => $count];
            if (ENABLE_CACHE) {
                apcu_store($cache_name, $data);
            }
            return $data;
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function update($search_id, $new_list)
    {
        if ($new_list === null) {
            ResponseService::throw(APIError::E_INPUT_REQUIRED_FIELD_MISSING, ['id' => $search_id, 'missing' => 'new_list', 'type' => 'SearchFavorite']);
        }

        DBService::clearCache('SearchFavorite-ofSearch:' . $search_id);
        // CACHE: set in ofSearch

        try {

            $statement = DBService::getPDO()->prepare("SELECT `element_list` FROM `vis_search_favorites` WHERE `search_id` = :searchid AND `user_id` = :userid");
            $statement->bindValue(':searchid', $search_id);
            $statement->bindValue(':userid', AuthService::$id);
            $statement->execute();
            $favorites = $statement->fetchAll(PDO::FETCH_NUM);

            if (count($favorites) == 0) {
                $statement = DBService::getPDO()->prepare("INSERT INTO `vis_search_favorites` (`user_id`, `search_id`, `element_list`) VALUES (:userid, :searchid, :elementlist)");
            } else {
                $statement = DBService::getPDO()->prepare("UPDATE `vis_search_favorites` SET `element_list` = :elementlist WHERE `user_id` = :userid AND `search_id` = :searchid");
            }

            $statement->bindValue(':searchid', $search_id);
            $statement->bindValue(':userid', AuthService::$id);
            $statement->bindValue(':elementlist', json_encode($new_list));
            $statement->execute();

            return 1;
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

}

class SearchResult extends DatabaseInterface
{
    public $id;
    public $image_id;
    public $search_id;
    public $score;
    public $vote;
    public $total_boxes;
    public $box_data;
    public $filename; // this is from another table, so yeah :D
    public $box_scores;
    public $refined_searchbox;

    const updateable_values = [];
    const table_name = 'vis_search_results';

    public static function getDBValuesForNew($params): array
    {
        return [
            'id' => null,
            'image_id' => $params[0],
            'search_id' => $params[1],
            'score' => $params[2],
            'vote' => 0,
            'total_boxes' => count($params[3]),
            'box_data' => json_encode($params[3]),
            'box_scores' => json_encode($params[4]),
            'refined_searchbox' => json_encode($params[3]),
            'tsne' => json_encode($params[5]),
        ];
    }

    public static function ofSearch($search_id, $vote = null, $limits = []): array
    {
        $vote_cond = ($vote === null) ? "" : " AND `vis_search_results`.`vote` = :vote";
        $bindings = [
            ":searchid" => $search_id,
        ];
        if ($vote !== null) {
            $bindings[':vote'] = $vote;
        }
        return DBService::getData(
            'SearchResult-ofSearch:' . $search_id,
            "SELECT `vis_search_results`.*, `vis_images`.`filename`, (SELECT MIN(`score`) FROM `vis_search_results` WHERE `search_id` = :searchid) AS minscore, (SELECT MAX(`score`) FROM `vis_search_results` WHERE `search_id` = :searchid) AS maxscore FROM `vis_search_results` INNER JOIN `vis_images` ON `vis_images`.`id` = `vis_search_results`.`image_id` WHERE `vis_search_results`.`search_id` = :searchid" . $vote_cond . " ORDER BY `vis_search_results`.`score` ASC",
            $bindings,
            [PDO::FETCH_CLASS, __CLASS__],
            $limits
        );
        // CACHE: cleared in
        // - SearchResult::vote
        // - SearchResult::refine
        // - SearchResult::parseJSONResult
    }

    public static function ofSearchForRefinement($search_id, $vote): array
    {
        $search_info = Search::getByID($search_id);
        try {
            $statement = DBService::getPDO()->prepare("SELECT `vis_search_results`.`id`, `vis_search_results`.`image_id`, `vis_search_results`.`refined_searchbox` FROM `vis_search_results` INNER JOIN `vis_images` ON `vis_images`.`id` = `vis_search_results`.`image_id` WHERE `vis_search_results`.`search_id` = :searchid AND `vis_search_results`.`vote` = :vote");
            $statement->bindValue(':searchid', $search_id);
            $statement->bindValue(':vote', $vote);
            $statement->execute();
            $searches = $statement->fetchAll(PDO::FETCH_ASSOC);
            return $searches;
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function unreviewedOf($collection_id, $indices, $searches, $max_retrievals = 20)
    {
        $indices = (is_array($indices) && $indices[0] != null) ? $indices : [];
        $searches = (is_array($searches) && $searches[0] != null) ? $searches : [];

        if (count($indices) == 0 && count($searches) == 0) {
            return [];
        }

        $cond = "";
        $comb = 'AND';
        if (count($indices) > 0) {
            $cond .= ' AND (searches.`index_id` IN (' . str_repeat('?,', count($indices) - 1) . '?' . ')';
            if (count($searches) == 0) {
                $cond .= ')';
            } else {
                $comb = 'OR';
            }
        }
        if (count($searches) > 0) {
            $cond .= ' ' . $comb . ' searches.`id` IN (' . str_repeat('?,', count($searches) - 1) . '?' . ')';
            if (count($indices) > 0) {
                $cond .= ')';
            }
        }

        try {
            // TD: simplify !!!
            $statement = DBService::getPDO()->prepare("
      SELECT SUBQUERY.`search_id`, SUBQUERY.*, `vis_images`.`filename` AS query_filename FROM (
        SELECT
          results.*,
          images.`filename` AS filename,
          searches.`image_id` AS query_image_id,
          searches.`query_bbox`
        FROM
          `vis_search_results` AS results
          INNER JOIN `vis_images` AS images ON images.`id` = results.`image_id`
          INNER JOIN `vis_searches` AS searches ON searches.`base_search` = results.`search_id`
        WHERE searches.`collection_id` = ? AND searches.`status` != 9" . $cond . " ORDER BY results.`score`
      ) AS SUBQUERY INNER JOIN `vis_images` ON `vis_images`.`id` = SUBQUERY.`query_image_id` ORDER BY SUBQUERY.`search_id`");

            $statement->execute(array_merge([$collection_id], $indices, $searches));
            $data = $statement->fetchAll(PDO::FETCH_GROUP | PDO::FETCH_CLASS, __CLASS__);

            $filtered = array();

            foreach ($data as $search_id => $retrievals) {
                $filtered = array_merge($filtered, array_slice($retrievals, 0, $max_retrievals));
            }
            
            return $filtered;
        } catch (PDOException $exception) {
            DBService::handlePDOError(__FUNCTION__, $exception);
        }
    }

    public static function vote($result_id, $vote)
    {
        if ($vote != 1 && $vote != 0 && $vote != -1) {
            ResponseService::throw(APIError::E_INPUT_REQUIRED_FIELD_WRONG, ['type' => 'SearchResult', 'id' => $result_id, 'data' => $vote]);
        }
        $searchresult_info = SearchResult::getByID($result_id);
        DBService::clearCache('SearchResult-ofSearch:' . $searchresult_info->search_id);
        SearchResult::update($result_id, ['vote' => $vote]);
        return SearchResult::getByID($result_id)->vote;
    }

    public static function refine($result_id, $box_data_string)
    {
        $searchresult_info = SearchResult::getByID($result_id);
        DBService::clearCache('SearchResult-ofSearch:' . $searchresult_info->search_id);
        SearchResult::update($result_id, ['vote' => 1, 'refined_searchbox' => $box_data_string]);
        return true;
    }

    public static function parseResultJSON($search_id)
    {

        $search_info = Search::getByID($search_id);
        $collection_id = $search_info->collection_id;
        $index_id = $search_info->index_id;

        $retrievalDir = _DATA_ . 'images_' . $collection_id . DIRECTORY_SEPARATOR . 'index_' . $index_id . DIRECTORY_SEPARATOR . 'retrieval';
        $mainDirectory = $retrievalDir . DIRECTORY_SEPARATOR . 'search_' . $search_id;
        $path = $mainDirectory . DIRECTORY_SEPARATOR . 'retrievals.json';

        $data = file_get_contents($path);
        $data = str_replace('NaN', 0, $data);
        $data = json_decode($data, true)["data"][0];

        Search::update($search_id, ['total_hits' => count($data["retrievals"])]);
        // CACHE: clears all caches
        foreach ($data["retrievals"] as $key2 => $retrieval) {
            $retrieval_img = $retrieval[0];
            $retrieval_bbox = $retrieval[1];
            $retrieval_score = $retrieval[3];
            $retrieval_scores = $retrieval[2];
            $retrieval_tsne = $retrieval[5];
            // TD: make only one insert call
            SearchResult::new ($retrieval_img, $search_id, $retrieval_score, $retrieval_bbox, $retrieval_scores, $retrieval_tsne);
        }

        return 1;
    }

}
