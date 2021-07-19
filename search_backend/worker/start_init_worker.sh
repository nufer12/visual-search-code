#!/bin/bash

NUM_TH=10
export OMP_NUM_THREADS=$NUM_TH
export OPENBLAS_NUM_THREADS=$NUM_TH
export MKL_NUM_THREADS=$NUM_TH
export VECLIB_MAXIMUM_THREADS=$NUM_TH
export NUMEXPR_NUM_THREADS=$NUM_TH

# Activate environment
source ~/programs/miniconda/etc/profile.d/conda.sh
if [[ $CONDA_DEFAULT_ENV != "visual_search" ]]
then
    echo "Activate environtment"
    conda activate visual_search
fi

# Start worker
echo "Start initialization worker"
if [[ $1 == "server" ]]
then
    # - application on server
    python worker.py [server_address] 0 0 [api_secret] $HOSTNAME ./configs/server/config_$2.json
elif [[ $1 == "local" ]]
then
    # - application on localhost
    python worker.py localhost 0 0 [api_secret] $HOSTNAME ./configs/local/config_$2.json
else
    echo 'Choose either server or local mode -> stop execution!'
    exit 1
fi

