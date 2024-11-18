__author__ = 'VMware'
__version__ = '1.0'

import argparse
import logging
import os
import sys
import time

import csv

from argparse import RawDescriptionHelpFormatter
from nagini import Nagini, NaginiException
from optparse import OptionParser, OptParseError
from pprint import pformat


# root logger.
logger = logging.getLogger(__name__)


def main(argv):
    try:
        parser = argparse.ArgumentParser(
            description="Use vROps Suite API to merge Object data identified by a specified file.\nThe file format:\n"
                        "  Line 1: {OLD VC UUID},{NEW VC UUID}\n"
                        "For the remaining lines there are two format options:\n"
                        " Option 1 matches Objects by resource identifiers\n"
                        "  Line 2+: {ResourceKindKey},{Old MOID},{Old Name},{New MOID},{New Name}\n"
                        " Option 2 matches Objects by the Object UUID.\n"
                        "  Line 2+: {Old Object UUID},{New Object UUID}",
            epilog="File example:\n"
                   "A0DB4B81-E891-4DB4-95C6-334BA183B100,5951C07B-45D7-47FA-8510-00DBEF6C4ABD\n"
                   "VirtualMachine,vm-1436,VM Temp,vm-236,\"VM Temp Name with,Comma\""
                   "\n\nExample:\npython %(prog)s -i -u user1 -p pass1 -a 127.0.0.1 ./data.txt",
            formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("file", metavar="file", type=str,
                            help="Specify the file that contains the identity information of specific objects to merge")
        parser.add_argument("-a", "--address", dest="address", metavar="<address>", required=True,
                            help="Specify the server IP address.  Required.")
        parser.add_argument("-u", "--user", dest="username", metavar="<username>", required=True,
                            help="Specify the username.  Required.")
        parser.add_argument("-p", "--pass", dest="password", metavar="<password>", required=True,
                            help="Specify the password.  Required.")
        parser.add_argument("-c", "--cert-file", type=str, dest="cert_file", metavar="<file>", required=False,
                            default=False,
                            help="Certificate file to use for SSL verification.  If omitted then certificate verification is disabled")
        parser.add_argument("-i", "--ignore-host", dest="ignore_hostname", action="store_true",
                            help="Ignore host name during SSL verification")
        parser.add_argument("-t", "--test-input", dest="test", action="store_true",
                            help="Test parsing of data file and display output but do not make calls to server")
        parser.add_argument("-m", "--mode", dest="mode", type=str, choices=["batch", "single"], default="batch",
                            help="Batch mode sends all merge requests in a single call to the server. Single mode sends each merge request, outputs any error and then continues to the next request.  Default is batch.")
        parser.add_argument("--delimiter", dest="delimiter", type=str, choices=["comma", "tab", "space"],
                            default="comma",
                            help="Value delimiter used to parse data from the file.  Default is comma.")
        parser.add_argument("--quote", dest="quote", type=str, choices=["double", "single", "pipe"], default="double",
                            help="Value quote character used for the csv file.  Default is double quote.")
        parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Log more output")
        opts = parser.parse_args()
    except OptParseError:
        parser.print_usage()
        sys.exit(2)
    configure_logger(__name__, opts.verbose)
    verify_certificates = opts.cert_file
    delimiter = ","
    if not verify_certificates:
        verify_certificates = False
    if opts.delimiter == "space":
        delimiter = " "
    elif opts.delimiter == "tab":
        delimiter = "\t"
    quote_char = "\""
    if opts.quote == "single":
        quote_char = "'"
    elif opts.quote == "pipe":
        quote_char = "|"
    client = Nagini(host=opts.address, user_pass=[opts.username, opts.password], refresh_token=opts.refresh_token,
                    refresh_token_host=opts.refresh_token_host, verify=verify_certificates, ignoreHostName=opts.ignore_hostname,
                    useInternalApis=True)
    merge_resources_using_file(client, opts.file, as_batch=(opts.mode == "batch"), quote_char=quote_char,
                               display_only=opts.test, delimiter=delimiter)


def get_resource_key(guid, rkKey, moid, name):
    return {
        'name': name,
        'resourceKindKey': rkKey,
        'adapterKindKey': 'VMWARE',
        'resourceIdentifiers': [{
            'identifierType': {
                'name': 'VMEntityObjectID',
                'dataType': 'STRING',
                'isPartOfUniqueness': True
            },
            'value': moid
        }, {
            'identifierType': {
                'name': 'VMEntityVCID',
                'dataType': 'STRING',
                'isPartOfUniqueness': True
            },
            'value': guid
        }, {
            'identifierType': {
                'name': 'VMEntityName',
                'dataType': 'STRING',
                'isPartOfUniqueness': False
            },
            'value': name
        }]
    }


def merge_request_info(oldGuid, rkKey, oldMoid, oldName, newGuid, newMoid, newName):
    return {
        'newResourceKey': get_resource_key(newGuid, rkKey, newMoid, newName),
        'oldResourceKey': get_resource_key(oldGuid, rkKey, oldMoid, oldName)
    }


def merge_request_info_uuid(oldUuid, newUuid):
    return {
        'newResourceId': newUuid,
        'oldResourceId': oldUuid
    }


def append_resource_merge_info(merge_infos, oldVCUuid, newVCUuid, parts):
    if (len(parts) == 2):
        merge_infos.append(merge_request_info_uuid(parts[0], parts[1]))
    elif (len(parts) == 5):
        rkKey = parts[0]
        oldMoid = parts[1]
        oldName = parts[2]
        newMoid = parts[3]
        newName = parts[4]
        merge_infos.append(merge_request_info(oldVCUuid, rkKey, oldMoid, oldName, newVCUuid, newMoid, newName))
    else:
        return False
    return True


def execute_merge_resources(client, merge_infos):
    # call api
    request_body = {"resourceMergeRequests": merge_infos}
    client.merge_resources(request_body)


def configure_logger(project_root, verbose):
    """
    Generate and configure logger.
    Args:
        project_root: Project root directory path.
    Return:
        Logger object
    """
    log_dir = os.path.join(project_root, "logs")
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    logging.Formatter.converter = time.gmtime
    logging.basicConfig(
        filename=os.path.join(log_dir, "postAdapter.log"),
        format='%(asctime)s %(levelname)s - %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    console = logging.StreamHandler()
    if verbose:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    global logger
    logger = logging.getLogger('Main')
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger.addHandler(console)
    return logger


def display_merge_infos(merge_infos):
    for entry in merge_infos:
        entry['newResourceKey']


def merge_resources_using_file(client, file_name, delimiter, quote_char, as_batch=True, display_only=False):
    # do something
    delimiter_long = "space"
    if delimiter == ",":
        delimiter_long = "comma"
    elif delimiter == "\t":
        delimiter_long = "tab"
    logger.info("read file merge data from [{0}]".format(file_name))
    logger.debug("  delimiter [{0}] a {1}".format(delimiter, delimiter_long))
    logger.debug("  quote char [{0}]".format(quote_char))
    logger.debug("  test parsing [{0}]".format(display_only))
    logger.debug("  batch processing [{0}]".format(as_batch))
    logger.debug("OLD --> NEW")
    firstLine = True
    oldGuid = ""
    newGuid = ""
    merge_infos = []
    try:
        with open(file_name, "r") as merge_file:
            csv_reader = csv.reader(merge_file, quotechar=quote_char, delimiter=delimiter)
            for parts in csv_reader:
                if firstLine:
                    firstLine = False
                    try:
                        oldGuid = parts[0]
                        newGuid = parts[1]
                        logger.debug("VMEntityVCID {0} -> {1}".format(oldGuid, newGuid))
                    except Exception as e:
                        logger.error('Failed to merge line [{0}], error: {1}'.format(delimiter.join(parts),
                                                                                     extract_simple_error(e)))
                else:
                    appended = append_resource_merge_info(merge_infos, oldGuid, newGuid, parts)
                    if appended:
                        if not as_batch:
                            logger.info("Executing merge request for 1 object")
                            logger.debug("Merge Request {0}".format(merge_infos))
                            if not display_only:
                                try:
                                    execute_merge_resources(client, merge_infos)
                                    logger.debug("Request execution successful")
                                except Exception as e:
                                    logger.error(
                                        'Failed to merge line [{0}], error: {1}'.format(parts, extract_simple_error(e)))
                            merge_infos = []
                    else:
                        logger.error(
                            'Invalid line.  Check delimiter and quote character. Skipping merge request for tokens {0}'.format(
                                parts))
        if as_batch:
            logger.info("Executing batch for {0} objects".format(len(merge_infos)))
            logger.debug("Merge Request {0}".format(merge_infos))
            if not display_only:
                execute_merge_resources(client, merge_infos)
                logger.debug("Request execution successful")
    except IOError as e:
        logger.error('Failed to open the file: "{0}" caused by exception: {1}'.format(file_name, str(e)))
    except Exception as e:
        logger.error('Failed to process merge requests, error {0}'.format(str(e)))


def extract_simple_error(e):
    errorMessage = None
    localizedMessage = None
    if hasattr(e, "error_object"):
        error_object = e.error_object
    else:
        return str(e)
    if error_object and "moreInformation" in error_object and error_object["moreInformation"]:
        for item in error_object["moreInformation"]:
            if "name" in item and item["name"] == "localizedMessage":
                localizedMessage = item["value"]
            elif "name" in item and item["name"] == "errorMessage":
                errorMessage = item["value"]
    if not errorMessage:
        errorMessage = pformat(e.error_object)
    if errorMessage:
        return errorMessage
    elif localizedMessage:
        return localizedMessage
    else:
        return errorMessage


if __name__ == '__main__':
    main(sys.argv)
