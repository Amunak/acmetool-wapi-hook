# AcmeTool WAPI Hook

This is an [AcmeTool](https://github.com/hlandau/acmetool) hook for
[Wedos](https://www.wedos.com/)'s API (WAPI) for the
[DNS-01 ACME challenge](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge).


## Requirements

- Python 3.7 (and [Pipenv](https://pipenv.kennethreitz.org/))

Pipenv further downloads dependencies specified in [Pipfile](./Pipfile).


## Installation

0. Install Pipenv if you don't have it yet: try your distribution's repositories or - if you have `pip` -
run `sudo pip install pipenv`
0. Clone this repository on your target system that's running AcmeTool
0. Run `pipenv install` in the cloned directory to install dependencies
0. **Configure** the script by copying [config.ini.dist](./config.ini.dist) to `config.ini`
and modify the variables there
0. Symlink [wedos_hook.sh](./wedos_hook.sh) - a wrapper script that runs the python script -
into your AcmeTool Hooks directory (run `sudo acmetool status` to find its location)
0. *Optionally* test that the script itself works by running it manually with `./wedos_hook.sh test`
(try `./wedos_hook.sh --help` for more)
