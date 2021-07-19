# compvis-worker

Usage: 
```python3 worker.py WORKER_ID WORKER_TYPE API_TOKEN WORKER_NAME [PATH_TO_CONFIG]```
where ```WORKER_ID``` is a unique, numeric id, ```WORKER_TYPE``` is 0 for indexing and 1 for searching, ```API_TOKEN``` is the API secret of the webserver (find in ```/path/to/api/config.php```) and ```WORKER_NAME``` is a readable identifier for the users. ```PATH_TO_CONFIG``` must be specified for indexing workers.