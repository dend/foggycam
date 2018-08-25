#!/usr/bin/env bash

# Checks for conda
$(which conda)

if [ $? != 0 ]; then
    echo "You need to install conda, installing locally"
    if [ $(uname) == "Darwin" ]; then
      os="MacOSX"
    elif [ $(uname) == "Linux" ]; then
      os="Linux"
    else
      echo "Cannot automatically install conda on "$(uname)" please install conda manually and follow conda install in README.md";
      exit 1;
    fi
    conda_url="https://repo.continuum.io/miniconda/"
    tarball="Miniconda3-latest-"${os}"-x86_64.sh"
    echo "Downloading conda from "${conda_url}${tarball}
    curl -o conda.sh ${conda_url}${tarball}
    bash conda.sh -p $(pwd)/miniconda3 -b
    export PATH=$(pwd)/miniconda3/bin:${PATH}
else
   echo "You have conda"
fi

# Check for foggycam env
CONDA=$(which conda)
CONDA_PATH=$(dirname ${CONDA})
echo "conda detected in: "${CONDA_PATH}

source activate base
${CONDA} activate base
CONDA_ENV="foggy"
# Bug on my mac conda env list does not print envs anymore... 
# this is a work around
${CONDA} activate ${CONDA_ENV}

if [[ $(which python) == *${CONDA_ENV}* ]]; then
    echo "You have foggy env, great!"
else
    echo "Creating conda env ${CONDA_ENV} for foggy cam"
    ${CONDA} create -n {CONDA_ENV} python=3.6 ffmpeg
fi

# Test for ffmpeg
FFMPEG=$(which gffmpeg)
if [ $? == 0 ]; then
   echo "FFMPEG detected at "${FFMPEG}
else
   echo "Adding FFMPEG to your "${CONDA_ENV}" environment"
   ${CONDA} install ffmpeg
fi

