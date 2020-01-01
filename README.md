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
0. **Configure** the script by copying [`config.ini.dist`](./config.ini.dist) to `config.ini`
and modify the variables there
0. Symlink [wedos_hook.sh](./wedos_hook.sh) - a wrapper script that runs the python script -
into your AcmeTool Hooks directory (run `sudo acmetool status` to find its location)
0. *Optionally* test that the script itself works by running it manually with `./wedos_hook.sh test`
(try `./wedos_hook.sh --help` for more)


## Example output of the `test` command

The test command tries all the steps the script does otherwise in one go,
creating a TXT record at `_test-challenge.<your-domain>` with the API, then checking that it propagates
to outside nameservers, and finally deletes this record.

If it finishes successfully you can be reasonably sure that the script works.

```text
root@example:~# /etc/acme/hooks/wedos_hook.sh test -v example.cz
INFO:root:Domain "example.cz" extracted as example.cz (TLD cz, NO SUBDOMAIN)
INFO:root:Using account "root@example.cz"
INFO:root:Pinging API to make sure basic functionality works
INFO:root:Creating record
INFO:root:Checking for DNS record propagation for a maximum of 360 tries with 10s delays (for a total of 3600 seconds)
INFO:root:Match found after 14 tries (130 seconds)
INFO:root:Looking up records for deletion
INFO:root:Deleting row IDs: 1200
INFO:root:Test success
```
