import os, sys, time
import os.path as osp
import json
import multiprocessing
import requests
import yaml
import logging
from enum import Enum

sys.path.append("external/PreciseRoIPooling/pytorch/prroi_pool")

from src.interface import search


logging.basicConfig(level=logging.INFO)

# status of worker
class Status(Enum):
    EMPTY = 10
    JOB_RUNNING = 21
    STOPPED_WITH_ERRORS = 31
    STOPPED_ON_REQUEST = 32
    FINISHED = 40


# this function is exictued in a new process
def helper_initialization(cfg):
    """ Start initialization process """
    from src.interface import initialization
    initialization(cfg)


def data_merge(a, b):
    """ merge two dictionaries for the configuration """
    key = None
    try:
        if a is None or isinstance(a, (str, float, int)):
            a = b
        elif isinstance(a, list):
            if isinstance(b, list):
                a.extend(b)
            else:
                a.append(b)
        elif isinstance(a, dict):
            if isinstance(b, dict):
                for key in b:
                    if key in a:
                        a[key] = data_merge(a[key], b[key])
                    else:
                        a[key] = b[key]
            else:
                raise RuntimeError('Cannot merge non-dict "%s" into dict "%s"' % (b, a))
        else:
            raise RuntimeError('NOT IMPLEMENTED "%s" into "%s"' % (b, a))
    except TypeError as e:
        raise TypeError('TypeError "%s" in key "%s" when merging "%s" into "%s"' % (e, key, b, a))
    return a


class Worker:
    """ Initialization/Search Worker Class """
    API_TOKEN = ''  # authenticate at API
    DATA_ROOT = ''  # root folder for indices and searches, taken from worker config
    TYPE = 0  # type of worker --> Index-Worker

    def __init__(self, restapi_server, id, main_config_path, description):
        logging.info('{}'.format(restapi_server))
        self.restapi_server = restapi_server
        self.id = id
        logging.info('Created Worker (id: {}, type: {})'.format(id, self.TYPE))
        # load config data
        self.main_config_path = main_config_path
        with open(self.main_config_path) as f:
            self.main_config = yaml.safe_load(f)
        logging.info('Main config loaded (path: {})'.format(main_config_path))
        Worker.DATA_ROOT = self.main_config["DATA_ROOT"]
        self.description = description
        self.status = Status.EMPTY
        self.proc = None
        self.thread = None

    def loop(self):
        while True:
            # - proc should be None
            if self.proc is None:
                # - set status to empty and request API for new jobs
                self.status = Status.EMPTY
                resp = self.request({
                    "description": self.description
                })
                logging.debug('Response from Webserver: take action '+resp["action"])
                # if got a new job, tstart this
                if resp["action"] == "new_job":
                    self.run_job(resp["job"])
            else:
                logging.error('Method loop called without self.proc beeing None, this should not happen!')

            # execute after 5s again
            time.sleep(1)

    def request(self, data):
        # add default data to request
        req_data = {** {'status': self.status.value, 'token': self.API_TOKEN, 'type': self.TYPE}, ** data}
        # perform request
        r = requests.post("http://{}/api/job/{}/update".format(self.restapi_server, self.id), json=req_data)
        response = json.loads(r.text)
        return response

    def set_status_by_exitcode(self, exitcode):
        if exitcode < 0:
            self.status = Status.STOPPED_ON_REQUEST
        elif exitcode == 0:
            self.status = Status.FINISHED
        else:
            self.status = Status.STOPPED_WITH_ERRORS

    def run_job(self, job):
        # create params by merging job-specific params into provided config
        defaults = self.main_config.copy()
        job_params = json.loads(job["params"])
        params = data_merge(defaults, job_params)
        # - adjust parameters
        params["DATA_DIR_BASE"] = params['DATA_ROOT']
        params["OUTPUT_DIR_BASE"] = params['DATA_ROOT']
        params["DATA_DIR"] = osp.join(params["DATA_DIR_BASE"], 'images_{}'.format(job["collection_id"]))
        params["OUTPUT_DIR"] = osp.join(params["DATA_DIR_BASE"],
                                        'images_{}'.format(job["collection_id"]), 'index_{}'.format(job["id"]))
        params["DATASET_NAME"] = 'images_{}'.format(job["collection_id"])
        params["TRANS"]["STYLE_PATH"] = osp.join(params["OUTPUT_DIR"],
                                                 "style_transfer/ncluster_%d" % params["TEMP"]["NCLUSTER"])
        logging.info('Start new index generation (path: {})'.format(params["OUTPUT_DIR"]))
        with open(os.path.join(params["OUTPUT_DIR"], 'index_config.json'), 'w') as f:
            json.dump(params, f, indent=4)

        # start initialization in new process
        multiprocessing.set_start_method('spawn', force=True)  # required for pytorch + multiprocessing
        self.proc = multiprocessing.Process(target=helper_initialization, args=(params, ))
        self.proc.start()
        self.status = Status.JOB_RUNNING

        while True:
            # while process is running...
            # ... perform request
            resp = self.request({
            })
            # ... check if should cancel
            try:
                if resp["action"] == "cancel":
                    logging.info('Webserver requested end of job, terminate process now')
                    self.proc.terminate()
            except KeyError:
                logging.error("No action specified in response")
                logging.error(str(resp))
            # ... if not running, get out of loop
            if not self.proc.is_alive():
                break
            time.sleep(1)

        # wait until finished
        self.proc.join()
        exitcode = self.proc.exitcode
        self.set_status_by_exitcode(exitcode)
        logging.info('Process finished with exitcode {}, set status to {}'.format(exitcode, self.status))
        # inform api on finished job
        resp = self.request({
            "exitcode": exitcode
        })
        # set proc to none to enable loop function
        self.proc = None


class SearchWorkerParallelIndex(Worker):
    """ One worker blocked for index for some time to keep index in memory """
    TYPE = 1  # type of worker --> search worker

    def __init__(self, restapi_server, id, main_config_path, description):
        # load config data
        self.main_config_path = main_config_path
        with open(self.main_config_path) as f:
            self.main_config = yaml.safe_load(f)
        logging.info('Main config loaded (path: {})'.format(main_config_path))
        self.DATA_ROOT = self.main_config["DATA_ROOT"]
        self.restapi_server = restapi_server
        self.id = id
        logging.info('Created SearchWorker (id: {}, type: {})'.format(id, self.TYPE))
        self.description = description
        self.status = Status.EMPTY
        self.proc = None

    def run_job(self, job):
        # in comparison to the Index-Worker we can not run the task in a subprocess, because
        # otherwise the index is not kept in memory
        counter = 0
        self.current_index = 0
        while True:
            # is there a job?
            if job is not None:
                # build root path
                search_params = json.loads(job["params"])
                self.current_index = job["index_id"]
                output_dir = os.path.join(self.DATA_ROOT,
                                          'images_{}'.format(job["collection_id"]), 'index_{}'.format(job["index_id"]))
                # inform api that new job starts
                self.status = Status.JOB_RUNNING
                resp = self.request({

                })
                # perform search
                exitcode = self.run_search(output_dir, job["id"])
                # inform api that job finished
                self.set_status_by_exitcode(exitcode)
                resp = self.request({
                    "exitcode": exitcode
                })
                job = None
                self.status = Status.EMPTY

            else:
                # ask api for new job for loaded index
                resp = self.request({
                    "loaded_index": self.current_index
                })
                logging.debug('Response from Webserver: take action '+resp["action"])
                if(resp["action"] == "new_job"):
                    job = resp["job"]
                    counter = 0
                else:
                    counter += 1
                    logging.debug('No new job found, increase counter to {}'.format(counter))
                # ask at maximum 1800 times for new job of same index
                if counter == 1800:
                    break
                time.sleep(1)
        self.proc = None

    def run_search(self, search_root, search_id):
        # just a helper function
        logging.info('Start search with id {} and config {}'.format(search_id, os.path.join(search_root, 'config.json')))
        exitcode = search(os.path.join(search_root, 'index_config.json'), search_id)
        logging.info('Process finished with exitcode {}'.format(exitcode))
        return exitcode


if __name__ == "__main__":

    # get server listing from command line
    restapi_server = sys.argv[1]
    # get id from command line
    worker_id = sys.argv[2]
    # get type from command line
    worker_type = int(sys.argv[3])
    # set the token
    Worker.API_TOKEN = sys.argv[4]
    # get name from command line
    worker_description = sys.argv[5]
    # set up logger
    logging.basicConfig(filename='worker_'+worker_id+'.log', level=logging.ERROR)

    worker = None
    if worker_type == 0:  # index worker
        # get config path from command line
        worker_config = sys.argv[6]
        worker = Worker(restapi_server, worker_id, worker_config, worker_description)
    elif worker_type == 1:  # index worker
        worker_config = sys.argv[6]
        worker = SearchWorkerParallelIndex(restapi_server, worker_id, worker_config, worker_description)
    else:
        # Search worker
        raise ValueError(f'Unknown worker type: {worker_type}')

    worker.loop()


