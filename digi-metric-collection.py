#!/usr/bin/python

"""
# data-collect.py contain the python program to gather Metrics from vROps. Before you run this script
# set-config.py should be run once to set the environment
# Author Sajal Debnath <sdebnath@vmware.com> 
# Modified to handle multiple configurations, Korean timestamp, using nagini API methods
"""

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
        # nagini의 get_resource_properties API 사용 시 id 파라미터 추가
        resource_data = vrops.get_resource_properties(resourceId=resource_id, id=resource_id)
        
        # 요청된 속성 키에 대한 값만 필터링
        if 'property' in resource_data:
            for prop in resource_data['property']:
                if prop['name'] in property_keys:
                    properties[prop['name']] = prop['value']
    except Exception as e:
        print(f"Error getting properties for resource {resource_id}: {str(e)}")
    
    return properties

def get_metric_stats(vrops, resource_id, metric_keys, sampleno):
    stats = {}
    try:
        for key in metric_keys:
            # nagini의 get_latest_stats API 사용
            allvalues = vrops.get_latest_stats(resourceId=resource_id, statKey=[key], maxSamples=sampleno, id=resource_id)
            
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
    
    # 메트릭과 프로퍼티 데이터를 각각의 nagini API로 수집
    stats = get_metric_stats(vrops, name, metric_keys, sampleno)
    properties = get_resource_properties(vrops, name, property_keys)
    
    if stats or properties:  # 메트릭이나 속성 데이터가 있는 경우만 추가
        resourcedata["identifier"] = name
        resourcedata["name"] = resource['resourceKey']['name']
        resourcedata["stats"] = stats
        resourcedata["properties"] = properties
    
    return resourcedata

def process_configuration(config):
    adapter = config["adapterKind"]
    resourceknd = config["resourceKind"]
    servername = config["server"]["name"]
    passwd = base64.b64decode(config["server"]["password"].encode('utf-8')).decode('utf-8')
    uid = config["server"]["userid"]
    sampleno = config["sampleno"]
    metric_keys = config.get("metricKeys", [])
    property_keys = config.get("propertyKeys", [])
    
    vrops = nagini.Nagini(host=servername, user_pass=(uid, passwd))
    
    outdata = []
    # 리소스 목록 가져오기
    resources = vrops.get_resources(resourceKind=resourceknd, adapterKindKey=adapter)['resourceList']
    
    for resource in resources:
        resource_data = get_resource_data(vrops, resource, metric_keys, property_keys, sampleno)
        if resource_data:  # 데이터가 있는 경우만 추가
            outdata.append(resource_data)
    
    outstat = {
        "allstats": outdata,
        "timestamp": get_korean_timestamp(),
        "resourceKind": resourceknd,
        "adapterKind": adapter,
        "metricKeys": metric_keys,
        "propertyKeys": property_keys
    }
    
    return outstat

def main():
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    
    path = get_script_path()
    fullpath = path + "/" + "config.json"
    
    with open(fullpath) as data_file:
        configs = json.load(data_file)
    
    all_results = []
    
    for config in configs:
        result = process_configuration(config)
        all_results.append(result)
    
    outpath = path + "/" + "metric-data.json"
    
    with open(outpath, 'w') as outfile:
        json.dump(all_results, outfile, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()