#!/bin/bash

NUM_TH=10
export OMP_NUM_THREADS=$NUM_TH
export OPENBLAS_NUM_THREADS=$NUM_TH
export MKL_NUM_THREADS=$NUM_TH
export VECLIB_MAXIMUM_THREADS=$NUM_TH
export NUMEXPR_NUM_THREADS=$NUM_TH
export WORKER_NAME=$HOSTNAME
export SERVER_ADDRESS=     # <--------- adjust
export API_SECRET=         # <--------- adjust
export CONDA_PATH=         # <--------- adjust
export CONDA_ENV_NAME=     # <--------- adjust

# Activate environment
source $CONDA_PATH/etc/profile.d/conda.sh
if [[ $CONDA_DEFAULT_ENV != $CONDA_ENV_NAME ]]
then
    echo "Activate environtment"
    conda activate $CONDA_ENV_NAME
fi

# Start worker
echo "Start initialization worker"
if [[ $1 == "localhost" ]]
then
    # - run local for development
    python worker.py localhost 0 0 $API_SECRET $WORKER_NAME ./configs_worker/config_local_$2.json
elif [[ $1 == "server" ]]
then
    # - run on server
    python worker.py $SERVER_ADDRESS 0 0 $API_SECRET $WORKER_NAME ./configs_worker/config_server_$2.json
else
    echo 'Choose either localhost or server mode -> stop execution!'
    exit 1
fi


