#!/usr/bin/python

"""
#
# set-config - a small python program to setup the configuration environment for data-collect.py
# data-collect.py contain the python program to gather Metrics from vROps
# Author Sajal Debnath <sdebnath@vmware.com> 
# Modified to handle multiple configurations and separate metric/property keys
"""

import json
import base64
import os, sys

def get_script_path():
    return os.path.dirname(os.path.realpath(sys.argv[0]))

def get_keys(key_type):
    keys = []
    num_keys = input(f"Please enter the number of {key_type} to monitor: ")
    for i in range(int(num_keys)):
        keys.append(input(f"Enter the {key_type} key: "))
    return keys

def get_single_config():
    adapterkind = input("Please enter Adapter Kind: ")
    resourceKind = input("Please enter Resource Kind: ")
    servername = input("Enter Server IP/FQDN: ")
    serveruid = input("Please enter user id: ")
    serverpasswd = input("Please enter vRops password: ")
    encryptedvar = base64.b64encode(serverpasswd.encode('utf-8')).decode('utf-8')
    maxsamples = input("Please enter the maximum number of samples to collect: ")

    print("\n=== Metric Keys Configuration ===")
    metricKeys = get_keys("metric")
    
    print("\n=== Property Keys Configuration ===")
    propertyKeys = get_keys("property")
    
    data = {}

    if int(maxsamples) < 1:
        maxsamples = 1

    data["adapterKind"] = adapterkind
    data["resourceKind"] = resourceKind
    data["sampleno"] = int(maxsamples)
    data["metricKeys"] = metricKeys
    data["propertyKeys"] = propertyKeys
    
    serverdetails = {}
    serverdetails["name"] = servername
    serverdetails["userid"] = serveruid
    serverdetails["password"] = encryptedvar

    data["server"] = serverdetails

    return data

def get_the_inputs():
    configs = []
    while True:
        print("\n=== Adding New Configuration ===")
        config = get_single_config()
        configs.append(config)
        
        add_more = input("\nWould you like to add another configuration? (y/n): ")
        if add_more.lower() != 'y':
            break
    
    return configs

def main():
    # Getting the path where config.json file should be kept
    path = get_script_path()
    fullpath = path + "/" + "config.json"

    # Getting the data for the config.json file
    final_data = get_the_inputs()

    # Saving the data to config.json file
    with open(fullpath, 'w') as outfile:
        json.dump(final_data, outfile, indent=2)

    print(f"\nConfiguration saved to {fullpath}")

if __name__ == "__main__":
    main()