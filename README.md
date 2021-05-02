# AcmeTool WAPI Hook

This is an [AcmeTool](https://github.com/hlandau/acmetool) hook for
[Wedos](https://www.wedos.com/)'s API (WAPI) for the
[DNS-01 ACME challenge](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge).

It aims to support regular challenges (although there are faster/better verification methods for those) as well as **wildcard certificate** verification, including ones for subdomains (to be fair there's really no difference to regular challenges, but whatever).

---

## Discontinued

This hook never worked very well and AcmeTool seems to be mostly abandoned by its author, so I wanted to migrate to something else, something more reliable and less ... wrong.

I would like to encourage you to migrate to a better way to manage certificates: use CNAME delegation (setting up records like `_acme-challenge.example.com CNAME some.zone.example.net`) to a dedicated DNS server that is for ACME DNS-01 validation only. You can easily set up bind9 to do this, or you can use dedicated software like [acme-dns](https://github.com/joohoi/acme-dns). This allows you to *remotely, reliably and securely* set records on a DNS server that - even if it were compromised - would not be of any use to the attacker. It can also make cert management easier since you only set up the CNAME records once and you can even point them to just one (sub)domain in the dedicated zone, so you are changing just one domain's TXT records instead of manipulating with actual, live domain.

If you don't feel like running your own DNS server you can instead use CNAME delegation to pass validation to some other provider that is natively supported by whichever ACME client you choose to use.

Personally I use bind9 for serving the TXT records, it only serves one zone and all CNAME records point to a subdomain in that zone. Then I use (nsupdate)[https://linux.die.net/man/8/nsupdate] as a client to update these TXT records through a simple [hook](https://github.com/dehydrated-io/dehydrated/wiki/example-dns-01-nsupdate-script) for the [Dehydrated](https://github.com/dehydrated-io/dehydrated) ACME client. It's elegant, reliable, way faster and I can even set up multiple clients (with different credentials and access to different subdomains in that zone) to allow anyone to make certificates for their own domains and such.

---

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
