#!/bin/sh

if [ -f '/usr/bin/realpath' ]; then
    realpath="/usr/bin/realpath"
else if [ -f '/bin/realpath' ]; then
    realpath="/bin/realpath"
else
    echo "Your system is missing core utility 'realpath', aborting."
    exit 30
fi
fi

if [ -f '/usr/bin/dirname' ]; then
    dirname="/usr/bin/dirname"
else if [ -f '/bin/dirname' ]; then
    dirname="/bin/dirname"
else
    echo "Your system is missing core utility 'dirname', aborting."
    exit 31
fi
fi

script_path=$("${realpath}" "$0")
script_dir=$("${dirname}" "$script_path")

if [ -f '/usr/bin/pipenv' ]; then
    pipenv="/usr/bin/pipenv"
else if [ -f '/bin/pipenv' ]; then
    pipenv="/bin/pipenv"
else
    echo 'Failed to locate Pipenv executable'
    echo ''
    echo 'Do you have Pipenv installed?'
    echo 'Try running `pip install pipenv` or read the documentation at'
    echo 'https://pypi.org/project/pipenv/'
    exit 32
fi
fi

\cd "$script_dir"

${pipenv} run wedos_hook "$@"
