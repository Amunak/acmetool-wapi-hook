#!/usr/bin/python3

import argparse
import logging
import sys
import time
from configparser import ConfigParser
from pathlib import Path
from random import randint
from typing import Optional, Callable

from dns import resolver, rdtypes
from tldextract import tldextract

from .wapi import Wapi

# Constants that might change at some point but that probably don't need to be configurable:

# how long to wait (in seconds) between DNS queries for validating that the record change has propagated
PROPAGATION_CHECK_DELAY: float = 10

# how many retries will be done before giving up the record validation
PROPAGATION_MAX_RETRIES: int = round(3600 / PROPAGATION_CHECK_DELAY)

# name servers used to validate DNS record addition
# those should be public servers far away from you, not your local resolver
NAMESERVERS = ['1.1.1.1', '8.8.8.8']

DOC_LINK = 'https://github.com/hlandau/acmetool/blob/master/_doc/SCHEMA.md#challenge-dns-start-challenge-dns-stop'

OPT_TEST = 'test'
OPT_DNS_CHALLENGE_STOP = 'challenge-dns-stop'
OPT_DNS_CHALLENGE_START = 'challenge-dns-start'
OPT_HTTP_CHALLENGE_START = 'challenge-http-start'
OPT_HTTP_CHALLENGE_STOP = 'challenge-http-stop'

wapi: Wapi


def test(domain: str, name: str):
    logging.info('Pinging API to make sure basic functionality works')
    wapi.ping()

    name = ('_test-challenge.' + name).rstrip('.')
    data_prefix = '_TEST-CHALLENGE.'
    data = data_prefix + str(randint(0, 10000000))

    logging.info('Creating record')
    wapi.dns_row_add(domain, name, data, 'Wedos Hook Test Record')
    wapi.dns_domain_commit(domain)

    result = wait_for_record_propagation(domain, name, data)

    if not result:
        logging.critical('Record propagation failed! Attempts timed out after all retries.')

    ids_to_delete = find_row_ids_for_delete(domain, name, lambda record_data: record_data.startswith(data_prefix))
    result = do_delete(domain, ids_to_delete)

    if not result:
        sys.exit(5)

    wapi.dns_domain_commit(domain)

    logging.info('Test success')
    sys.exit(0)


def challenge_start(domain: str, name: str, data: str):
    name = ('_acme-challenge.' + name).rstrip('.')

    logging.info('Creating record')
    wapi.dns_row_add(domain, name, data, 'AcmeTool Wedos Hook')
    wapi.dns_domain_commit(domain)

    result = wait_for_record_propagation(domain, name, data)

    if result:
        logging.info('Record created and propagated')
    else:
        logging.critical('Record propagation failed')

    sys.exit(0 if result else 42)


def challenge_stop(domain: str, name: str, data: str):
    name = ('_acme-challenge.' + name).rstrip('.')

    ids_to_delete = find_row_ids_for_delete(domain, name, lambda record_data: record_data == data)
    result = do_delete(domain, ids_to_delete)

    wapi.dns_domain_commit(domain)

    if result:
        logging.info('Record removed successfully')
    else:
        logging.critical('Record removal failure')

    sys.exit(0 if result else 42)


def find_row_ids_for_delete(domain: str, name: str, data_matches: Callable[[str], bool]):
    logging.info('Looking up records for deletion')
    rows = wapi.dns_rows_list(domain)['response']['data']['row']
    ids_to_delete = []
    for row in rows:
        # if row['ttl'] != str(wapi.default_dns_record_ttl):
        #     continue
        if row['rdtype'] != wapi.default_dns_record_type:
            continue
        if row['name'] != name:
            continue
        if not data_matches(str(row['rdata'])):
            continue
        ids_to_delete.append(row['ID'])
    return ids_to_delete


def do_delete(domain, ids_to_delete) -> bool:
    # Check that we actually found our record, otherwise something is quite wrong
    if len(ids_to_delete) == 0:
        logging.error('Found 0 rows to delete')
        return False

    logging.info(f'Deleting row IDs: {", ".join(ids_to_delete)}')
    for rid in ids_to_delete:
        wapi.dns_row_delete(domain, int(rid))

    return True


def wait_for_record_propagation(domain: str, name: str, data: str) -> bool:
    """Waits for DNS record propagation, aborting after a set amount of delayed retries

    :param domain: the domain to verify
    :param name: the name (subdomain), if any
    :param data: record data (used to verify the exact data in case there are multiple records for the same domain)
    :return: whether propagation succeeded (`True`), `False` otherwise
    """
    full_name = f'{name}.{domain}'.lstrip('.')

    my_resolver = resolver.Resolver()
    my_resolver.nameservers = NAMESERVERS
    has_propagated: Optional[bool] = None

    tries = 1
    logging.info(
        f'Checking for DNS record propagation for a maximum of {PROPAGATION_MAX_RETRIES} tries with {PROPAGATION_CHECK_DELAY}s delays (for a total of {PROPAGATION_MAX_RETRIES * PROPAGATION_CHECK_DELAY} seconds)')
    while tries <= PROPAGATION_MAX_RETRIES and (has_propagated is None or not has_propagated):
        logging.debug(f'Checking whether record propagated (try {tries} of {PROPAGATION_MAX_RETRIES})')

        try:
            answer = my_resolver.query(full_name, wapi.default_dns_record_type)
            has_propagated = record_has_propagated(answer, data)
        except (resolver.NoAnswer, resolver.NXDOMAIN):
            has_propagated = False

        if not has_propagated:
            tries += 1
            logging.debug(f'Sleeping for {PROPAGATION_CHECK_DELAY}s')
            time.sleep(PROPAGATION_CHECK_DELAY)
        else:
            logging.info(f'Match found after {tries} tries ({(tries - 1) * PROPAGATION_CHECK_DELAY} seconds)')

    return has_propagated


def record_has_propagated(answer: resolver.Answer, data: str) -> bool:
    record: rdtypes.ANY.TXT.TXT
    for record in answer:
        record_data = record.to_text().strip('"')
        logging.debug(f'Reading TXT record data: {record_data}')
        if record_data == data:
            return True

    logging.debug('No match')
    return False

    pass


def read_config() -> dict:
    base = Path(__file__).resolve().parents[1]
    dist_config_path = base.joinpath('./config.ini.dist')
    config_path = base.joinpath('./config.ini')

    if not dist_config_path.exists():
        logging.error(f'Distributable config file not found at path "{dist_config_path}".')

    if not config_path.exists():
        raise FileNotFoundError(f'Config file not found. Create file "{config_path}" (ideally by copying "{dist_config_path}") and edit it.')

    parser = ConfigParser()
    parser.read([dist_config_path, config_path])

    return {
        'wapi': {
            'username': parser.get('wapi', 'username'),
            'password_sha1': parser.get('wapi', 'password_sha1'),
        },
        'hook': {
            'verbosity': max(0, min(10, parser.getint('hook', 'override_verbosity', fallback=0))),
        },
    }


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='AcmeTool DNS-01 validation hook for Wedos API (WAPI)',
        epilog=f'Read {DOC_LINK}for more information about AcmeTool Hooks\n',
    )
    parser.add_argument('--verbose', '-v', action='count', default=0, help='log verbosity; use multiple times for higher')
    subparsers = parser.add_subparsers(title='Actions', dest='action', description='Hook actions; pick one and call it with --help for more help')

    test_parser = subparsers.add_parser(OPT_TEST, help='test the integration on a selected domain')
    test_parser.add_argument('--verbose', '-v', action='count', default=0, help='log verbosity; use multiple times for higher')
    test_parser.add_argument('domain', type=str)

    start_parser = subparsers.add_parser(OPT_DNS_CHALLENGE_START, help='hook action used before the challenge')
    start_parser.add_argument('--verbose', '-v', action='count', default=0, help='log verbosity; use multiple times for higher')
    start_parser.add_argument('domain', type=str)
    start_parser.add_argument('file', help='not used, passed here by AcmeTool')
    start_parser.add_argument('record', type=str, help='the TXT record')

    stop_parser = subparsers.add_parser(OPT_DNS_CHALLENGE_STOP, help='hook action used after the challenge')
    stop_parser.add_argument('--verbose', '-v', action='count', default=0, help='log verbosity; use multiple times for higher')
    stop_parser.add_argument('domain', type=str)
    stop_parser.add_argument('file', help='not used, passed here by AcmeTool')
    stop_parser.add_argument('record', type=str, help='the TXT record')

    # additional parsers that run a dummy function so that there are no errors in AcmeTool output
    subparsers.add_parser(OPT_HTTP_CHALLENGE_START, help='dummy hook action').add_argument('dummy', nargs=3)
    subparsers.add_parser(OPT_HTTP_CHALLENGE_STOP, help='dummy hook action').add_argument('dummy', nargs=3)

    return parser


def main():
    global wapi

    # Read config
    config = read_config()

    # Parse args
    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()
    verbosity = max(args.verbose, config['hook']['verbosity'])
    if verbosity >= 2:
        loglevel = logging.DEBUG
    elif verbosity >= 1:
        loglevel = logging.INFO
    else:
        loglevel = logging.WARNING
    logging.basicConfig(level=loglevel)

    logging.debug(args)

    # In case no arguments / action is specified, exit
    if 'action' not in args or args.action is None:
        arg_parser.print_help()
        sys.exit(3)

    # Extract domain/subdomain
    if 'domain' in args:
        extract_result = tldextract.extract(args.domain)
        info_prefix = f'Domain "{args.domain}" extracted as {extract_result.registered_domain} (TLD {extract_result.suffix}, '
        if extract_result.subdomain == '':
            logging.info(info_prefix + 'NO SUBDOMAIN)')
        else:
            logging.info(info_prefix + f'SUBDOMAIN {extract_result.subdomain})')

    # Initialize Wapi
    logging.info(f'Using account "{config["wapi"]["username"]}"')
    wapi = Wapi(config['wapi']['username'], config['wapi']['password_sha1'])

    # Finally decide what to do and run the given function
    {
        OPT_TEST: lambda: test(extract_result.registered_domain, extract_result.subdomain),
        OPT_DNS_CHALLENGE_START: lambda: challenge_start(extract_result.registered_domain, extract_result.subdomain, args.record),
        OPT_DNS_CHALLENGE_STOP: lambda: challenge_stop(extract_result.registered_domain, extract_result.subdomain, args.record),
        OPT_HTTP_CHALLENGE_START: lambda: exit_not_implemented(),
        OPT_HTTP_CHALLENGE_STOP: lambda: exit_not_implemented(),
    }[args.action]()

    # Commands should exit by themselves - if they don't, we return with error here
    logging.error('Subcommand did not exit on its own.')
    sys.exit(255)


def exit_not_implemented():
    logging.debug('Not implemented.')
    sys.exit(4)

if __name__ == '__main__':
    main()
