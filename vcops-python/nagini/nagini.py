__author__ = 'VMware'
__version__ = '1.70'

import json
import logging
import re
from io import IOBase
from pprint import pformat

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from threading import Lock

# root logger.
logger = logging.getLogger(__name__)


def pp(obj):
    print(json.dumps(obj, indent=2))


class IgnoreHostNameHttpAdapter(HTTPAdapter):
    """"Transport adapter" that allows ignoring hostname verification."""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, assert_hostname=False)

    # def cert_verify(self, conn, url, verify, cert):
    #    conn.assert_hostname = False
    #    return super(IgnoreHostNameHttpAdapter, self).cert_verify(conn, url, verify, cert)


class Struct(object):
    def __init__(self, **entries):
        def convert_value(value):
            print("convert_value called with : %s, %s" % (type(value), value))
            if isinstance(value, dict):
                print("Current item is dict.")
                return Struct(**value)
            elif isinstance(value, list):
                print("current item is list, calling map to resolve items")
                if len(value) == 0:
                    return value
                else:
                    return list(map(convert_value, value))
            else:
                return value

        for (k, v) in list(entries.items()):
            print('evaluating (%s, %s)' % (k, v))
            setattr(self, k, convert_value(v))


# use 2.7 BaseException, ie .message deprecated
class NaginiException(Exception):
    """
        Parent exception of the client framework.
    """

    def __init__(self, message):
        super(NaginiException, self).__init__(message)

    def __str__(self):
        return "reason = %s" % super(NaginiException, self).__str__()

    def __repr__(self):
        return str(self)


class NaginiHttpException(NaginiException):
    """
        General exception thrown after a http call failed.
    """

    def __init__(self, error_code, message="", error_object=None):
        NaginiException.__init__(self, message)
        self.error_code = error_code
        self.error_object = error_object
        self.message=message


    def __repr__(self):
        if self.error_object:
            return "Http error code = %s\nReason = %s. Error object = %s\n " % (self.error_code, self.message, pformat(self.error_object))
        else:
            return "Http error code = %s\nReason = [%s]" % (self.error_code, self.message)

    def __str__(self):
        return self.__repr__()


class ServerSideException(NaginiHttpException):
    """
        This exception is thrown when something went wrong on the server side.
    """
    pass


class ClientSideException(NaginiHttpException):
    """
        This exception is thrown when server detected input was not valid from client side.
    """
    pass


class AuthException(ClientSideException):
    """
        This exception is thrown when user tried accessing a protected resource
        without valid credentials.
    """
    pass


class Nagini(object):
    """
        Default Python client for accessing VMware vRealize Operations Manager REST API.
        verify=False: will not verify server certificate, verify='pem file path': will verify server certificate using certificate at file path
        ignoreHostName=True: ignore host and certificate host name match, ignoreHostName=False: enforce host and certificate host name match
    """

    def __init__(self, host, user_pass=None, refresh_token=None, refresh_token_host=None, api_version='1.70',
                 verify=False, ignoreHostName=True, useInternalApis=False, enableForwardsCompatibility=False,
                 certs=False, proxies=None, generateLinks=False, enableCompression=False):
        self._add_methods()
        self._path_regex = re.compile('\{([a-zA-Z_]+)\}')
        self._api_url_regex = re.compile('https://.+?(?=/)')
        self._base_url = '%s://%s/suite-api' % ('https', host)
        self.nonJSONResponseAPIs = set(['/suite-api/api/reports/{id}/download'])

        logger.debug("Base url is : %s", self._base_url)
        self._api_version = api_version
        self._gen_links = generateLinks
        self._enable_compression = enableCompression
        self._acquire_token_in_progress = False
        self._client_acquired_token = ''
        self._lock = Lock()

        # TODO: proxies are ignored for now.
        self._certs = certs
        self._verify = verify
        self.client = requests.session()

        self.client.headers.update({
            'User-Agent': 'Nagini ' + __version__,
            'X-vRealizeOps-API-version': api_version,
            'Accept': 'application/json',
        })

        # TODO: could be done by Https
        if ignoreHostName:
            self.client.mount('https://', IgnoreHostNameHttpAdapter())

        if useInternalApis:
            self.client.headers['X-vRealizeOps-API-use-unsupported'] = 'yes'

        if enableForwardsCompatibility:
            self.client.headers['X-vRealizeOps-API-version-lax'] = 'yes'

        self.client.proxies = proxies
        self.user_pass = user_pass
        self.refresh_token = refresh_token
        self.refresh_token_host = refresh_token_host
        self.is_saas = not user_pass and refresh_token is not None and refresh_token_host is not None

    def _acquire_token(self, old_token):
        # this mean that we are already acquiring token, or have already acquired a new one
        if self._acquire_token_in_progress or old_token != self._client_acquired_token or not self.user_pass:
            return

        with self._lock:
            # checking again in case if some other thread somehow passed check above
            if old_token != self._client_acquired_token:
                return
            try:
                self._acquire_token_in_progress = True
                request_body = {'username': self.user_pass[0], 'password': self.user_pass[1]}
                response = self.acquire_token(request_body)
                self._client_acquired_token = response['token']
            finally:
                self._acquire_token_in_progress = False


    def _acquire_token_saas(self, old_token):
        # this mean that we are already acquiring token, or have already acquired a new one
        if self._acquire_token_in_progress or old_token != self._client_acquired_token or \
                not self.refresh_token or not self.refresh_token_host:
            return

        headers = {'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
        body = {'api_token': self.refresh_token}
        with self._lock:
            try:
                self._acquire_token_in_progress = True
                response = requests.post('{}://{}/csp/gateway/am/api/auth/api-tokens/authorize'.format('https', self.refresh_token_host),
                                 headers=headers, data=body)
                if response.status_code != 200:
                    raise NaginiException('Failed to authenticate. got response {}. message: {}'.format(response.status_code, response.text))
                token = json.loads(response.text)['access_token']
                print('authentication successful')
                self._client_acquired_token = token
            finally:
                self._acquire_token_in_progress = False

    def _acquire_token_if_necessary(self):
        if not self._client_acquired_token:
            if self.is_saas:
                self._acquire_token_saas('')
            else:
                self._acquire_token('')

    def _reacquire_token(self, old_token):
        if self.is_saas:
            self._acquire_token_saas(old_token)
        else :
            self._acquire_token(old_token)
        return self._client_acquired_token

    def _rest_request(self, rest_method, params={}, content=None, binary=False):
        # hacking in headers for describeupload until methods.json has headers set
        if rest_method.get('url') == "/internal/adapterkinds/describeupload":
            logger.debug('Assuming content-type != json')
            binary = True

        map_params = []
        for param in [p['name'] for p in rest_method['query_params'] if p['type'] == 'map']:
            map_params.append(param)

        encoded_params = {}
        for (k, v) in list(params.items()):
            logger.debug('Received %s => %s as param', k, v)
            if isinstance(v, (int, bool, str)):
                encoded_params[k] = '%s' % v
            elif isinstance(v, (list, tuple, set)):
                encoded_params[k] = ['%s' % value for value in v]
            elif k in map_params:
                for (subkey, subvalue) in list(v.items()):
                    logger.info("Adding Key %s[%s], Value %s" % (k, subkey, subvalue))
                    encoded_params[k + "[" + subkey + "]"] = subvalue
            else:
                encoded_params[k] = v

        # find and replace params.
        raw_url = '%s%s' % (self._base_url, rest_method['url'])
        try:
            templated_url = self._path_regex.sub(lambda m: str(encoded_params[m.group(1)]), raw_url)
            logger.debug('Going to call %s' % templated_url)
        except KeyError as e:
            raise NaginiException("Missing template parameter: [%s]" % e.args)
            return None

        try:
            api_url = self._api_url_regex.sub(lambda m: "", raw_url)
            logger.debug('API URL is %s' % api_url)
        except KeyError as e:
            pass

        # remove all template params from the final param map.
        for template_param in rest_method['template_params']:
            del encoded_params[template_param['name']]

        for param in [p['name'] for p in rest_method['query_params'] if not p['optional']]:
            if param not in encoded_params:
                logger.warning("Warning: %s required, but not provided by user." % param)

        # add _no_links query parameter with a value of true to encoded_params dictionary
        if not self._gen_links:
            encoded_params['_no_links'] = 'true'

        if self._enable_compression:
            encoded_params['compression'] = 'enabled'

        client_method = getattr(self.client, rest_method['http_method'].lower())
        if not client_method:
            raise "Method %s is not supported" % rest_method['http_method']

        # request body translation
        data = None
        files = None
        if content and content[0]:
            if isinstance(content[0], IOBase):
                data = content[0].read()
            elif isinstance(content[0], dict):
                if not binary:
                    data = json.dumps(content[0])
                else:
                    data = content[0].get('data')
                    files = content[0].get('files')
            elif isinstance(content[0], str):
                data = content[0]
            else:
                raise 'Cannot convert %s to json' % (type(content[0]))
        logger.debug('body has been passed to this api %s', data)

        return self._do_safe_request(templated_url, client_method, encoded_params, data, binary, files, api_url,
                                     'name' in rest_method and rest_method['name'] == 'acquire_token')

    def do_request(self, url, client_method, params=None, data=None, binary=False, files=None, api_url=None, *args,
                   **kwargs):
        return self._do_safe_request(url, client_method, params, data, binary, files, api_url, False)

    def _do_safe_request(self, url, client_method, params, data, binary, files, api_url, is_acquire_token):
        if not is_acquire_token:
            self._acquire_token_if_necessary()
            token = self._client_acquired_token
        else:
            token = ''

        try:
            return self._do_request(url, client_method, params, data, binary, files, api_url, token)
        except NaginiException as e:
            if self._reacquire_token(token):
                token = self._client_acquired_token
                return self._do_request(url, client_method, params, data, binary, files, api_url, token)
            raise e

    def _do_request(self, url, client_method, params, data, binary, files, api_url, token):
        try:
            self.previous_api_call = {
                "params": params,
                "url": url,
                "content": data
            }
            # if data:
            #   print(passed content is: %s" % data)

            headers = self.client.headers.copy()
            if not binary:
                headers.update({'content-type': 'application/json'})

            if api_url is not None and api_url in self.nonJSONResponseAPIs:
                headers.update({'Accept': '*/*'})

            if token:
                if self.is_saas:
                    headers.update({'Authorization': 'CSPToken %s' % token})
                else:
                    headers.update({'Authorization': 'vRealizeOpsToken %s' % token})

            result = client_method(url, data=data, params=params, headers=headers, files=files, allow_redirects=True,
                                   verify=self._verify)
            self.previous_api_call['response'] = result
            response_obj = None
            if "Content-Type" in result.headers and "application/json" not in result.headers["Content-Type"]:
                response_obj = result.content
            else:
                try:
                    response_obj = result.json()
                except Exception as e:
                    # print(e)
                    pass

            if result.status_code >= 500:
                raise ServerSideException(result.status_code, result.reason, response_obj)
            elif 400 <= result.status_code <= 499:
                if result.status_code in [401, 402, 403, 407]:
                    raise AuthException(result.status_code, result.reason, response_obj)
                else:
                    raise ClientSideException(result.status_code, result.reason, response_obj)
            elif 200 <= result.status_code < 300:
                return response_obj
            else:
                raise NaginiHttpException(result.status_code, result.reason, response_obj)
        except Exception as e:
            if isinstance(e, NaginiException):
                raise e
            else:
                raise NaginiException(e)

    def fetch_links(self, link):
        """
            Utility method to fetch contents of a link.
            :param 'link' Can be either a string or a link object or a collection of both.
        """

        def _get_link(l):
            if isinstance(l, dict):
                l = link['href']
            l = l.replace('/suite-api', '')
            return self.do_request("%s%s" % (self._base_url, l), getattr(self.client, 'get'))

        if isinstance(link, (list, set)):
            return list(map(_get_link, link))
        else:
            return _get_link(link)

    def _add_methods(self):
        def load_methods():
            try:
                import json, os
                dir_name = os.path.dirname(os.path.realpath(__file__))
                file = open(os.path.join(dir_name, "methods.json"),encoding='UTF-8')
                return json.load(file)
            except Exception as e:
                logger.error(e)
                return {"methods": []}

        def make_method(rest_method):
            new_method = lambda self, *args, **kwargs: self._rest_request(rest_method, params=kwargs, content=args)
            doc = "\nDocumentation for: %s %s\n\n%s\n" % (
                rest_method['http_method'], rest_method['url'], rest_method['doc'])
            query_params = rest_method.get('query_params', [])
            template_params = rest_method.get('template_params', [])

            def param_to_string(param):
                optional = 'optional' if param.get('optional', False) else 'mandatory'
                return "  :param '%s': (%s) %s" % (param['name'], optional, param['doc'])

            doc += '\n'.join(map(param_to_string, template_params + query_params))
            new_method.__doc__ = doc
            new_method.__name__ = str(rest_method['name'])
            new_method.__dict__['method_info'] = rest_method
            return new_method

        if not hasattr(self.__class__, "__rest_methods_initialized"):
            available_apis = load_methods()
            for method in available_apis['methods']:
                setattr(self.__class__, method['name'], make_method(method))
            setattr(self.__class__, "__rest_methods_initialized", True)
        else:
            logger.debug('Client already initialized with methods...')

    # BEGIN - Composite APIs for resource find/create
    def build_resource_key(self, resourceName, resourceKindKey, adapterKindKey, resourceIdentifiers):
        identifiers = []
        for (k, v) in list(resourceIdentifiers.items()):
            identifiers.append({'identifierType': {'name': k}, 'value': v})
        return {'name': resourceName,
                'resourceKindKey': resourceKindKey,
                'adapterKindKey': adapterKindKey,
                'resourceIdentifiers': identifiers}

    def find_create_resource_with_adapter_key(self, resourceName, resourceKindKey, adapterKindKey, resourceIdentifiers,
                                              pushAdapterKindKey):
        """
            Create a resource using name, resourceKindKey, AdapterKindKey and resource identifiers.  If a resource specified by values already
            exists then return Resource information.
        """
        if not pushAdapterKindKey:
            raise NaginiException("Missing adapterKindKey")

        # look for resource first
        resListDto = self.get_resources_with_adapter_and_resource_kind(identifiers=resourceIdentifiers,
                                                                       name=resourceName, adapterKindKey=adapterKindKey,
                                                                       resourceKindKey=resourceKindKey)
        if 'resourceList' in resListDto and len(resListDto['resourceList']) == 1:
            return resListDto['resourceList'][0]

        # create resource
        resKey = self.build_resource_key(resourceName, resourceKindKey, adapterKindKey, resourceIdentifiers)
        resDto = {'resourceKey': resKey}
        return self.create_resource_using_adapter_kind(resDto, adapterKindKey=pushAdapterKindKey)

    def find_create_resource_push_data(self, resourceName, resourceKindKey, adapterKindKey, resourceIdentifiers,
                                       pushAdapterKindKey, stats=None, properties=None, events=None):
        """
            Find or create a resource (with adapter key) and then push stats, properties and/or events to the resource.
            pushAdapterKindKey may not be none
            stats is java type StatContents
                { "stat-content" : [{ "statKey":"Metric1", "timestamps":[123456],"data":[1.0] }] }
            properties is java PropertyContents
                { "property-content" : [{ "statKey":"Property2", "timestamps":[123456],"values":["StringValue2] }] }
            events is java EventList
                { "event": [ {"eventType":"NOTIFICATION", "resourceId":"cae425ae-6d41-4bd3-810f-ff685b31a272", "message":"Test Event Message"}]}
        """
        resDto = self.find_create_resource_with_adapter_key(resourceName, resourceKindKey, adapterKindKey,
                                                            resourceIdentifiers, pushAdapterKindKey)
        if 'identifier' not in resDto:
            raise NaginiException("Returned data is missing identifier key")
        id = resDto['identifier']
        logger.debug(id)
        self.resource_push_data(id=id, pushAdapterKindKey=pushAdapterKindKey, stats=stats, properties=properties,
                                events=events)
        return resDto

    def resource_push_data(self, id, pushAdapterKindKey, stats=None, properties=None, events=None):

        if stats:
            logger.debug("push stats")
            self.add_stats_using_push_adapter_kind(stats, id=id, adapterKind=pushAdapterKindKey)

        if properties:
            logger.debug("push properties")
            self.add_properties_using_push_adapter_kind(properties, id=id, adapterKind=pushAdapterKindKey)

        if events:
            logger.debug("push events")
            if 'event' in events:
                for event in events['event']:
                    event['resourceId'] = id
            self.push_events_0(events, adapterKind=pushAdapterKindKey)

        return id

    def find_create_resource_with_adapter_uuid(self, resourceName, resourceKindKey, adapterKindKey, resourceIdentifiers,
                                               adapterInstanceId):
        """
            Create a resource using name, resourceKindKey, AdapterKindKey and resource identifiers.  If a resource specified by values already
            exists then return Resource information.
        """
        if not adapterKindKey:
            raise NaginiException("Missing adapterKindKey")
        # look for resource first
        resListDto = self.get_resources_with_adapter_and_resource_kind(identifiers=resourceIdentifiers,
                                                                       name=resourceName, adapterKindKey=adapterKindKey,
                                                                       resourceKindKey=resourceKindKey)
        if resListDto['resourceList'] and len(resListDto['resourceList']) == 1:
            return resListDto['resourceList'][0]

        # create resource
        resKey = self.build_resource_key(resourceName, resourceKindKey, adapterKindKey, resourceIdentifiers)
        resDto = {'resourceKey': resKey}
        return self.create_resource_using_adapter_instance(resDto, adapterInstanceId=adapterInstanceId)

    # END - Composite APIs for resource find/create

    def close(self):
        """
            Dispose the REST client.
        """
        self.client.close()

    def set_auth_token(self, token):
        """
            Set auth token for future REST calls. Can be either str or dict with 'token' property.
        """

        def _set_token(t):
            if self.is_saas:
                self.client.headers['Authorization'] = 'CSPToken %s' % t
            else:
                self.client.headers['Authorization'] = 'vRealizeOpsToken %s' % t

        if isinstance(token, str):
            _set_token(token)
        elif isinstance(token, dict) and 'token' in token:
            _set_token(token['token'])
        elif hasattr(token, 'token'):
            _set_token(token.token)
        else:
            raise "I don't know how to use [%s] for setting auth token." % token


if __name__ == '__main__':
    client = Nagini(host='localhost')
    dir(client)
    help(client.get_adapter)
    help(client.get_adapters)
