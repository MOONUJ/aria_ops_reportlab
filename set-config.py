#!/usr/bin/python

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

def get_server_config():
    servername = input("Enter Server IP/FQDN: ")
    serveruid = input("Please enter user id: ")
    serverpasswd = input("Please enter vRops password: ")
    encryptedvar = base64.b64encode(serverpasswd.encode('utf-8')).decode('utf-8')
    
    return {
        "name": servername,
        "userid": serveruid,
        "password": encryptedvar
    }

def get_collection_config(existing_servers):
    adapterkind = input("Please enter Adapter Kind: ")
    resourceKind = input("Please enter Resource Kind: ")
    maxsamples = input("Please enter the maximum number of samples to collect: ")

    # Show available servers
    print("\nAvailable servers:")
    for idx, server in enumerate(existing_servers, 1):
        print(f"{idx}. {server['name']}")
    
    # Allow user to select existing server or add new one
    choice = input("\nSelect an existing server (enter number) or type 'new' to add a new server: ")
    
    if choice.lower() == 'new':
        server = get_server_config()
        existing_servers.append(server)
        server_id = server['name']
    else:
        server_id = existing_servers[int(choice)-1]['name']

    print("\n=== Metric Keys Configuration ===")
    metricKeys = get_keys("metric")
    
    print("\n=== Property Keys Configuration ===")
    propertyKeys = get_keys("property")
    
    return {
        "adapterKind": adapterkind,
        "resourceKind": resourceKind,
        "sampleno": int(maxsamples) if int(maxsamples) >= 1 else 1,
        "serverId": server_id,
        "metricKeys": metricKeys,
        "propertyKeys": propertyKeys
    }

def get_the_inputs():
    servers = []
    collections = []
    
    while True:
        print("\n=== Adding New Configuration ===")
        collection = get_collection_config(servers)
        collections.append(collection)
        
        add_more = input("\nWould you like to add another configuration? (y/n): ")
        if add_more.lower() != 'y':
            break
    
    return {
        "servers": servers,
        "collections": collections
    }

def main():
    path = get_script_path()
    fullpath = path + "/" + "config.json"

    final_data = get_the_inputs()

    with open(fullpath, 'w') as outfile:
        json.dump(final_data, outfile, indent=2)

    print(f"\nConfiguration saved to {fullpath}")

if __name__ == "__main__":
    main()