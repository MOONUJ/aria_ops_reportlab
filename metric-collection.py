#!/usr/bin/python

import nagini
import requests
import json
import os, sys
import base64
import time
from datetime import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning

def get_script_path():
    return os.path.dirname(os.path.realpath(sys.argv[0]))

def get_korean_timestamp():
    weekdays = {
        'Monday': '월요일',
        'Tuesday': '화요일',
        'Wednesday': '수요일',
        'Thursday': '목요일',
        'Friday': '금요일',
        'Saturday': '토요일',
        'Sunday': '일요일'
    }
    
    now = datetime.now()
    weekday = weekdays[now.strftime('%A')]
    timestamp = now.strftime(f'%Y년 %m월 %d일 {weekday} %H시 %M분 %S초')
    return timestamp

def get_resource_properties(vrops, resource_id, property_keys):
    properties = {}
    try:
        resource_data = vrops.get_resource_properties(resourceId=resource_id, id=resource_id)
    # After test remove #    
        if 'property' in resource_data:
            for prop in resource_data['property']:
    #            if prop['name'] in property_keys:
                    properties[prop['name']] = prop['value']
    except Exception as e:
        print(f"Error getting properties for resource {resource_id}: {str(e)}")
    
    return properties

def get_metric_stats(vrops, resource_id, metric_keys, sampleno):
    stats = {}
    try:
        for key in metric_keys:
            # After test add statKey=[key]
            allvalues = vrops.get_latest_stats(resourceId=resource_id,maxSamples=sampleno, id=resource_id) 
            
            if allvalues["values"]:
                if int(sampleno) == 1:
                    for value in allvalues["values"][0]["stat-list"]["stat"]:
                        stats[value["statKey"]["key"]] = value["data"][0]
                else:
                    for singlevalue in allvalues["values"][0]["stat-list"]["stat"]:
                        all_metric_data = []
                        sample = len(singlevalue["data"])
                        for i in range(sample):
                            metric_data = {
                                "value": singlevalue["data"][i],
                                "timestamp": singlevalue["timestamps"][i]
                            }
                            all_metric_data.append(metric_data)
                        stats[singlevalue["statKey"]["key"]] = all_metric_data
    except Exception as e:
        print(f"Error getting metrics for resource {resource_id}: {str(e)}")
    
    return stats

def get_resource_data(vrops, resource, metric_keys, property_keys, sampleno):
    resourcedata = {}
    name = resource['identifier']
    
    stats = get_metric_stats(vrops, name, metric_keys, sampleno)
    properties = get_resource_properties(vrops, name, property_keys)
    
    if stats or properties:
        resourcedata["identifier"] = name
        resourcedata["name"] = resource['resourceKey']['name']
        resourcedata["stats"] = stats
        resourcedata["properties"] = properties
    
    return resourcedata

def get_vrops_connection(server_config):
    passwd = base64.b64decode(server_config["password"].encode('utf-8')).decode('utf-8')
    return nagini.Nagini(
        host=server_config["name"],
        user_pass=(server_config["userid"], passwd)
    )

def process_configuration(collection, server_config):
    adapter = collection["adapterKind"]
    resourceknd = collection["resourceKind"]
    sampleno = collection["sampleno"]
    metric_keys = collection.get("metricKeys", [])
    property_keys = collection.get("propertyKeys", [])
    
    vrops = get_vrops_connection(server_config)
    
    outdata = []
    resources = vrops.get_resources(resourceKind=resourceknd, adapterKindKey=adapter)['resourceList']
    
    for resource in resources:
        resource_data = get_resource_data(vrops, resource, metric_keys, property_keys, sampleno)
        if resource_data:
            outdata.append(resource_data)
    
    outstat = {
        "allstats": outdata,
        "timestamp": get_korean_timestamp(),
        "resourceKind": resourceknd,
        "adapterKind": adapter,
        "metricKeys": metric_keys,
        "propertyKeys": property_keys,
        "server": server_config["name"]
    }
    
    return outstat

def main():
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    
    path = get_script_path()
    fullpath = path + "/" + "config.json"
    
    with open(fullpath) as data_file:
        config = json.load(data_file)
    
    # Create server lookup dictionary
    servers = {server["name"]: server for server in config["servers"]}
    
    all_results = []
    
    for collection in config["collections"]:
        server_config = servers[collection["serverId"]]
        result = process_configuration(collection, server_config)
        all_results.append(result)
    
    outpath = path + "/" + "metric-data.json"
    
    with open(outpath, 'w') as outfile:
        json.dump(all_results, outfile, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()