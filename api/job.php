<?php

defined( 'ABSPATH' ) or die( 'No script kiddies please!' );


require_once 'response.php';
require_once 'dbservice.php';

require_once 'util.php';
require_once 'auth.php';
require_once 'index_manager.php';
require_once 'search.php';

class Job
{


    public static function userCan(User $user, int $action)
    {
		/*
        r = read access
        w = write access

        GLOBAL RIGHTS: defined by user->resource_priv
          r w
        0 x x
        1 y x
        2 y y
        
        */

        switch ($action) {
            case Scope::VIEW:
                return $user->resource_priv >= 1;
                break;
            case Scope::EDIT:
                return $user->resource_priv == 2;
                break;
            default:
                ResponseService::throw(APIError::E_SERVER_UNKNOWN_PERMISSION_REQUEST);
                return false;
                break;
        }
    }

    public static function getNextIndexJob($worker_id)
    {
		// CACHE: is disabled
        $data = DBService::getData(
            'Job-getNextIndexJob',
            "SELECT * FROM `vis_indices` WHERE `vis_indices`.`status` = 0 AND (`vis_indices`.`worker_id` < 0 OR `vis_indices`.`worker_id` = :workerid) ORDER BY `vis_indices`.`creation_date` ASC LIMIT 1",
            [":workerid" => $worker_id],
            [PDO::FETCH_CLASS, "Index"],
			[],
			false
		);
		if (count($data["data"]) > 0) {
            Index::update($data["data"][0]->id, array('status' => 1, 'worker_id' => $worker_id));
        }
        return $data["data"];
    }

    public static function getNextSearchJob($worker_id, $index_id = 0)
    {
        $index_cond = '';
		$bindings = [":workerid" => $worker_id];
		// should be of a given index?
        if ($index_id > 0) {
            $index_cond = ' AND `vis_searches`.`index_id` = :indexid';
            $bindings[":indexid"] = $index_id;
        }
		// CACHE: is disabled
        $data = DBService::getData(
            'Job-getNextSearchJob:' . $index_id,
            "SELECT * FROM `vis_searches` WHERE `vis_searches`.`status` = 0 AND (`vis_searches`.`worker_id` < 0 OR `vis_searches`.`worker_id` = :workerid)" . $index_cond . " ORDER BY `vis_searches`.`creation_date` ASC LIMIT 1",
            $bindings,
            [PDO::FETCH_CLASS, "Search"],
			[],
			false
        );
        if (count($data["data"]) > 0) {
            Search::update($data["data"][0]->id, array('status' => 1, 'worker_id' => $worker_id));
        }
        return $data["data"];
    }

    public static function getWorkers()
    {
		// list all registrated workers
        $workers = [];
        $all = new APCUIterator('/^ISE_WORKER/');
        foreach ($all as $key => $worker) {
            $workers[] = $worker["value"];
        }
        return $workers;
    }

    public static function getPendingJobs()
    {
        $indices = DBService::getData(
            'Job-getPendingIndexJobs',
            "SELECT `vis_indices`.`id`, 0 AS type, `vis_indices`.`creation_date`, `vis_indices`.`creator_id`, `vis_users`.`name` AS username, `vis_indices`.`collection_id`, `vis_indices`.`status`, `vis_indices`.`start_time`, `vis_indices`.`end_time`, `vis_indices`.`exitcode`, `vis_indices`.`worker_id` FROM `vis_indices` INNER JOIN `vis_users` ON `vis_users`.`id` = `vis_indices`.`creator_id` WHERE `vis_indices`.`status` = 0",
            [],
            [PDO::FETCH_ASSOC],
            []
		);
		// CACHE: cleared in 
		// - Index::update()
		// - Index::new()
		// - Collection::markIndicesAsModified
        $searches = DBService::getData(
            'Job-getPendingSearchJobs',
            "SELECT `vis_searches`.`id`, 1 AS type, `vis_searches`.`creation_date`, `vis_searches`.`creator_id`, `vis_users`.`name` AS username, `vis_searches`.`collection_id`, `vis_searches`.`status`, `vis_searches`.`start_time`, `vis_searches`.`end_time`, `vis_searches`.`exitcode`, `vis_searches`.`worker_id` FROM `vis_searches` INNER JOIN `vis_users` ON `vis_users`.`id` = `vis_searches`.`creator_id` WHERE `vis_searches`.`status` = 0",
            [],
            [PDO::FETCH_ASSOC],
            []
		);
		// CACHE: cleared in 
		// - Search::update (TD)
		// - Search::new (TD)
        return array_merge($indices["data"], $searches["data"]);
    }

    public static function getRunningJobs()
    {
        // TD: reset this caches
        $indices = DBService::getData(
            'Job-getRunningIndexJobs',
            "SELECT `vis_indices`.`id`, 0 AS type, `vis_indices`.`creation_date`, `vis_indices`.`creator_id`, `vis_users`.`name` AS username, `vis_indices`.`collection_id`, `vis_indices`.`status`, `vis_indices`.`start_time`, `vis_indices`.`end_time`, `vis_indices`.`exitcode`, `vis_indices`.`worker_id` FROM `vis_indices` INNER JOIN `vis_users` ON `vis_users`.`id` = `vis_indices`.`creator_id` WHERE `vis_indices`.`status` >= 1 AND `vis_indices`.`status` <= 2",
            [],
            [PDO::FETCH_ASSOC],
            []
		);
		// CACHE: cleared in 
		// - Index::update()
		// - Index::new()
		// - Collection::markIndicesAsModified
        $searches = DBService::getData(
            'Job-getRunningSearchJobs',
            "SELECT `vis_searches`.`id`, 1 AS type, `vis_searches`.`creation_date`, `vis_searches`.`creator_id`, `vis_users`.`name` AS username, `vis_searches`.`collection_id`, `vis_searches`.`status`, `vis_searches`.`start_time`, `vis_searches`.`end_time`, `vis_searches`.`exitcode`, `vis_searches`.`worker_id` FROM `vis_searches` INNER JOIN `vis_users` ON `vis_users`.`id` = `vis_searches`.`creator_id` WHERE `vis_searches`.`status` >= 1 AND `vis_searches`.`status` <= 2",
            [],
            [PDO::FETCH_ASSOC],
            []
		);
		// CACHE: cleared in 
		// - Search::update (TD)
		// - Search::new (TD)
        return array_merge($indices["data"], $searches["data"]);
    }

    public static function getFinishedJobs()
    {
        $indices = DBService::getData(
            'Job-getPendingIndexJobs',
            "SELECT `vis_indices`.`id`, 0 AS type, `vis_indices`.`creation_date`, `vis_indices`.`creator_id`, `vis_users`.`name` AS username, `vis_indices`.`collection_id`, `vis_indices`.`status`, `vis_indices`.`start_time`, `vis_indices`.`end_time`, `vis_indices`.`exitcode`, `vis_indices`.`worker_id` FROM `vis_indices` INNER JOIN `vis_users` ON `vis_users`.`id` = `vis_indices`.`creator_id` WHERE `vis_indices`.`status` >= 3 ORDER BY `end_time` DESC LIMIT 50",
            [],
            [PDO::FETCH_ASSOC],
            []
		);
		// CACHE: cleared in 
		// - Index::update()
		// - Index::new()
		// - Collection::markIndicesAsModified
        $searches = DBService::getData(
            'Job-getPendingSearchJobs',
            "SELECT `vis_searches`.`id`, 1 AS type, `vis_searches`.`creation_date`, `vis_searches`.`creator_id`, `vis_users`.`name` AS username, `vis_searches`.`collection_id`, `vis_searches`.`status`, `vis_searches`.`start_time`, `vis_searches`.`end_time`, `vis_searches`.`exitcode`, `vis_searches`.`worker_id` FROM `vis_searches` INNER JOIN `vis_users` ON `vis_users`.`id` = `vis_searches`.`creator_id` WHERE `vis_searches`.`status` >= 3 ORDER BY `end_time` DESC LIMIT 50",
            [],
            [PDO::FETCH_ASSOC],
            []
		);
		// CACHE: cleared in 
		// - Search::update (TD)
		// - Search::new (TD)
        return array_merge($indices["data"], $searches["data"]);
    }

    public static function updateWorkerStatus($id, $data)
    {
		// get worker info from cache and update the new values
        $local_worker_info = apcu_fetch('ISE_WORKER:' . $id);
        $local_worker_info["last_update"] = time();
        $local_worker_info["status"] = $data["status"];
        if(isset($data["description"])) {
            $local_worker_info["description"] = $data["description"];
        }
        apcu_store('ISE_WORKER:' . $id, $local_worker_info, 3 * 3600);

		// if worker is empty
        if ($data["status"] == 10) {
			// retrieve next job
            $next_job = null;
            if ($data["type"] == 0) {
                $next_job = Job::getNextIndexJob($id);
            }
            if ($data["type"] == 1) {
                $last_index = (isset($data["loaded_index"])) ? $data["loaded_index"] : 0;
                $next_job = Job::getNextSearchJob($id, $last_index);
			}
			// if there is a new job
            if (count($next_job) > 0) {
				// save in cache worker info
                $local_worker_info["current_job"] = $next_job[0]->id;
				apcu_store('ISE_WORKER:' . $id, $local_worker_info, 3 * 3600);
				// update/reset the job item
                Job::updateJobItem($next_job[0]->id, $data["type"], [
                    'start_time' => null,
                    'end_time' => null,
                    'exitcode' => null,
				]);
				// notify
                return [
                    "action" => "new_job",
                    "job" => $next_job[0],
                ];
            } else {
                return [
                    "action" => "none",
                ];
            }
        }

		// load current job info
        $job_info = ($data["type"] == 0) ? Index::getByID($local_worker_info["current_job"]) : Search::getByID($local_worker_info["current_job"]);

		// worker is running
        if ($data["status"] == 21) {
			// was deletion requested?
            if ($job_info->status == -1) {
                return [
                    "action" => "cancel",
                ];
            }

			// if job has another status than running: update with start time
            $toupdate = array('status' => 2);
            if (!$job_info->start_time) {
                $toupdate['start_time'] = date('Y-m-d H:i:s');
            }
            if ($job_info->status != 2) {
                Job::updateJobItem($job_info->id, $data["type"], $toupdate);
            }
            return [
                "action" => "none",
            ];
        }

		// worker stopped with errors
        if ($data["status"] == 31) {
			// update job item
			Job::updateJobItem($job_info->id, $data["type"], [
                'status' => 3,
                'exitcode' => $data["exitcode"],
                'end_time' => date('Y-m-d H:i:s'),
            ]);
            return [
                "action" => "none",
            ];
        }

		// worker stopped for user request
        if ($data["status"] == 32) { // stopped for user
			// update job item
			Job::updateJobItem($job_info->id, $data["type"], [
                'status' => 4,
                'exitcode' => $data["exitcode"],
                'end_time' => date('Y-m-d H:i:s'),
            ]);
            return [
                "action" => "none",
            ];
        }

		// worker finished succesfully
        if ($data["status"] == 40) { // finished
			// update job item
			Job::updateJobItem($job_info->id, $data["type"], [
                'status' => 5,
                'exitcode' => $data["exitcode"],
                'end_time' => date('Y-m-d H:i:s'),
            ]);
            return [
                "action" => "none",
            ];
        }
    }

    public static function updateJobItem(int $id, int $type, $toupdate)
    {
        if ($type == 0) { // indexing
            return Index::update($id, $toupdate);
        }
        if ($type == 1) { // search
            $updateresult = Search::update($id, $toupdate);
            if ($toupdate["status"] == 5) { // if finished without errors load results from file
                SearchResult::parseResultJSON($id);
            }
            return $updateresult;
        }
    }

}
