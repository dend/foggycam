#!/usr/bin/env bash

# Checks for conda
which conda

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
    source $(pwd)/miniconda3/etc/profile.d/conda.sh
else
   echo "You have conda"
fi

# Check for foggycam env
source activate base
echo "conda detected in: "${CONDA_PREFIX}

CONDA_ENV="foggy"
# Bug on my mac conda env list does not print envs anymore... 
# this is a work around
source activate ${CONDA_ENV}

if [[ $(which python) == *${CONDA_ENV}* ]]; then
    echo "You have foggy env, great!"
else
    echo "Creating conda env ${CONDA_ENV} for foggy cam"
    ${CONDA_EXE} create -n ${CONDA_ENV} python=3.6 ffmpeg x264
fi

source activate ${CONDA_ENV}

# Test for ffmpeg
FFMPEG=$(which gffmpeg)
echo "WHIFF FFMPEG SAYS"$?
if [ $? == 0 ]; then
   echo "FFMPEG detected at "${FFMPEG}
else
   echo "Adding FFMPEG to your "${CONDA_ENV}" environment"
   ${CONDA_EXE} install -n ${CONDA_ENV} ffmpeg
fi


# ok cloning git repo if not here
GIT=$(which git)
if [ $? == 0 ]; then
    echo "Git present good"
else
    echo "We need to add git"
    ${CONDA_EXE} install -n ${CONDA_ENV} git
fi
if [[ $(pwd) == *"foggycam" ]]; then
    echo "Good directory"
    SRC_DIR=$(pwd)
else
    git clone git://github.com/dend/foggycam
    SRC_DIR=$(pwd)/foggycam
fi

cd ${SRC_DIR}
python setup.py install

# Extra packages?
if [ $# -ge 1 ]; then
   for var in "$@"
    do
        if [ $var == "azure" ]; then
            echo "Azure needed adding to env"
            pip install -r ${SRC_DIR}/src/requirements.txt
        fi
    done
fi
echo "Foggycam installed "
echo "run:"
echo "source activate foggycam"
echo "foggycam --config=/path/to/your/config/file"
echo "e.g"
echo "foggycam --config=config.json"
echo "for full list of options run:"
echo "foggycam --help"