# Initialization and Search Worker

This directory contains the python code for the initialization and search worker

## Sofware
Install general dependencies (use requirements.txt):
- Python 3.6
- Python packages:
    - pytorch 1.2
    - torchvision 0.4 
    - faiss-gpu 1.6
    - scipy, scikit-image, scikit-learn, opencv-python
    - cython, easydict, h5py, hdfdict, pillow, pandas, requests

## Usage of python search backend
- adjust python environment, api secret and server address in start_init_worker_template.sh and start_worker_template.sh 
- start initialization and search worker with the abjusted bash scripts, i.e.
```./start_init_worker_template.sh local gpu ``` or  ```./start_search_worker_template.sh local gpu ```

### Usage of worker.py: 
```python worker.py WORKER_ID WORKER_TYPE API_TOKEN WORKER_NAME [PATH_TO_CONFIG]```
where ```WORKER_ID``` is a unique, numeric id, ```WORKER_TYPE``` is 0 for indexing and 1 for searching, ```API_TOKEN``` is the API secret of the webserver (find in ```/path/to/api/config.php```) and ```WORKER_NAME``` is a readable identifier for the users. ```PATH_TO_CONFIG``` must be specified for indexing workers.