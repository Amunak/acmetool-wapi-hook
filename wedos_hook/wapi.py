import datetime
import hashlib
import json
import logging

from requests import post, codes

# WAPI endpoint
ENDPOINT_URI: str = "https://api.wedos.com/wapi/json"


class WapiException(Exception):
    pass


class Wapi:
    default_dns_record_type: str = 'TXT'
    default_dns_record_ttl: int = 300

    def __init__(self, username: str, password: str):
        """
        :param username: WAPI Username
        :param password: WAPI Password, SHA-1 encoded (you may obtain the hash in Python console using `import hashlib; print(hashlib.sha1("Your Password".encode('utf8')).hexdigest())`)
        """
        self._username = username
        self._password = password

    def _make_auth(self):
        auth = self._username + self._password + datetime.datetime.now().strftime('%H')
        return hashlib.sha1(auth.encode('utf8')).hexdigest()

    def _do_request(self, command: str, command_data: object = None):
        if command_data is None:
            command_data = {}

        request_data = {
            'request': {
                'user': self._username,
                'auth': self._make_auth(),
                'command': command,
                'data': command_data,
            }
        }

        logging.debug(request_data)
        response = post(ENDPOINT_URI, {'request': json.dumps(request_data)})
        logging.debug(response.__dict__)

        if response.status_code != codes['ok']:
            raise WapiException(f'Unexpected HTTP status code {response.status_code}, {codes["ok"]} expected.')

        command_data = response.json()
        if command_data['response']['result'] != 'OK':
            raise WapiException(f'{command_data["response"]["code"]}: {command_data["response"]["result"]}')

        return command_data

    def ping(self):
        return self._do_request('ping')

    def dns_domains_list(self):
        return self._do_request('dns-domains-list')

    def is_domain_in_dns(self, domain_name: str) -> bool:
        data: dict = self.dns_domains_list()
        domains: dict = data['response']['data']['domain']

        for domain in domains.values():
            if domain['status'] != 'active':
                continue
            if domain['name'] == domain_name:
                logging.info('Domain found in account')
                return True

        return False

    def dns_rows_list(self, domain: str):
        return self._do_request('dns-rows-list', {
            'domain': domain,
        })

    def dns_row_add(self, domain: str, record_name: str, record_data: str, auth_comment: str = None, record_type: str = None, record_ttl: int = None):
        if record_type is None:
            record_type = self.default_dns_record_type

        if record_ttl is None:
            record_ttl = self.default_dns_record_ttl

        data = {
            'domain': domain,
            'name': record_name,
            'type': record_type,
            'ttl': record_ttl,
            'rdata': record_data,
        }

        if auth_comment is not None:
            data['auth_comment'] = auth_comment

        return self._do_request('dns-row-add', data)

    def dns_row_delete(self, domain: str, row_id: int):
        return self._do_request('dns-row-delete', {
            'domain': domain,
            'row_id': row_id,
        })

    def dns_domain_commit(self, domain: str):
        return self._do_request('dns-domain-commit', {
            'name': domain,
        })
