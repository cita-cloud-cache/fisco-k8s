#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright Rivtower Technologies LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import yaml
import os
from configparser import ConfigParser
import json

def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--work_dir', default='.', help='The output director of yaml files.')
    
    parser.add_argument(
        '--chain_name', default='test-chain', help='The name of chain.')
    
    parser.add_argument(
        '--version',
        default='v3.5.0',
        help='image version tag')

    parser.add_argument(
        '--image_pull_policy',
        default='IfNotPresent',
        help='image pull policy, IfNotPresent or Always')

    parser.add_argument(
        '--storage_calss',
        default='local-path',
        help='Storage class name of K8s.')

    args = parser.parse_args()
    return args

def gen_node_service(chain_name, node_name):
    node_service = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': '{}-{}'.format(chain_name, node_name)
        },
        'spec': {
            'type': 'ClusterIP',
            'ports': [
                {
                    'port': 30300,
                    'targetPort': 30300,
                    'name': 'p2p',
                },
                {
                    'port': 20200,
                    'targetPort': 20200,
                    'name': 'rpc',
                }
            ],
            'selector': {
                'app.kubernetes.io/chain-name': chain_name,
                'app.kubernetes.io/chain-node': node_name
            }
        }
    }
    return node_service

def gen_node_sts(chain_name, node_name, version, image_pull_policy, sc):
    node_sts = {
        'apiVersion': 'apps/v1',
        'kind': 'StatefulSet',
        'metadata': {
            'name': '{}-{}'.format(chain_name, node_name)
        },
        'spec': {
            'replicas': 1,
            'selector': {
                'matchLabels': {
                        'app.kubernetes.io/chain-name': chain_name,
                        'app.kubernetes.io/chain-node': node_name
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app.kubernetes.io/chain-name': chain_name,
                        'app.kubernetes.io/chain-node': node_name
                    }
                },
                'spec': {
                    'containers': [
                        {
                            'name': 'bcos',
                            'image' : "fiscoorg/fiscobcos:{}".format(version),
                            'imagePullPolicy': image_pull_policy,
                            'args' : [
                                "-c",
                                "/etc/fisco/config.ini",
                                "-g",
                                "/etc/fisco/config.genesis"
                            ],
                            'ports': [
                                {
                                    'containerPort': 30300,
                                    'name': 'p2p'
                                },
                                {
                                    'containerPort': 20200,
                                    'name': 'rpc'
                                }
                            ],
                            'volumeMounts': [
                                {
                                    'mountPath': '/data',
                                    'name': 'datadir'
                                },
                                {
                                    'mountPath': '/etc/fisco',
                                    'name': 'node-configs'
                                }
                            ]
                        }
                    ],
                    'volumes': [
                        {
                            'configMap': {
                                'name' : "{}-configs".format(node_name),
                            },
                            'name': 'node-configs'
                        }
                    ]
                }
            },
            'volumeClaimTemplates': [
                {
                    'apiVersion': 'v1',
                    'kind': 'PersistentVolumeClaim',
                    'metadata': {
                        'name': 'datadir'
                    },                        
                    'spec': {
                        'accessModes': [
                            'ReadWriteOnce'
                        ],
                        'resources': {
                            'requests': {
                                'storage': '10Gi'
                            }
                        },
                        'storageClassName': sc
                    }
                }
            ]  
        }
    }
    return node_sts


def run(args, work_dir):
    for entry in os.scandir(path='fisco/nodes/127.0.0.1/'):
        # find node dir
        if entry.is_dir() and  "node" in entry.name:
            node_name = entry.name
            node_id = int(node_name[4:])
            node_path = entry.path
            print("processing node: {} node_id {} ...".format(node_path, node_id))

            # create output dir
            node_output_dir = work_dir + "/" + args.chain_name + "/" + node_name
            if not os.path.exists(node_output_dir):
                os.makedirs(node_output_dir + "/conf")

            # modify config.ini
            print("modify config.ini ...")
            config_ini_path = entry.path + "/config.ini"
            cf = ConfigParser()
            cf.read(config_ini_path, encoding='utf-8')
            print("[p2p].listen_port now is {}, change to 30300!".format(cf.get('p2p', 'listen_port')))
            cf.set('p2p', 'listen_port', '30300')

            print("[rpc].listen_port now is {}, change to 20200!".format(cf.get('rpc', 'listen_port')))
            cf.set('rpc', 'listen_port', '20200')

            print("[p2p].nodes_path now is {}, change to /etc/fisco/!".format(cf.get('p2p', 'nodes_path')))
            cf.set('p2p', 'nodes_path', '/etc/fisco/')

            print("[cert].ca_path now is {}, change to /etc/fisco/!".format(cf.get('cert', 'ca_path')))
            cf.set('cert', 'ca_path', '/etc/fisco/')

            print("[security].private_key_path now is {}, change to /etc/fisco/node.pem!".format(cf.get('security', 'private_key_path')))
            cf.set('security', 'private_key_path', '/etc/fisco/node.pem')

            print("[storage].data_path now is {}, change to /data!".format(cf.get('storage', 'data_path')))
            cf.set('storage', 'data_path', '/data')

            print("[log].log_path now is {}, change to /data/log".format(cf.get('log', 'log_path')))
            cf.set('log', 'log_path', '/data/log')

            cf.write(open(node_output_dir+ "/conf/config.ini", "w"))

            # copy config.genesis
            print("copy config.genesis ...")
            os.system("cp " + node_path + "/config.genesis " + node_output_dir + "/conf/")

            # modify nodes.json
            print("modify nodes.json ...")
            nodes_json_path = entry.path + "/nodes.json"
            with open(nodes_json_path, 'r') as f:
                nodes_json = json.load(f)
                for (i, node) in enumerate(nodes_json["nodes"]):
                    print("old node {} address {}".format(i, node))
                    nodes_json["nodes"][i] = "{}-node{}:30300".format(args.chain_name, i)
            # remove myself
            del nodes_json["nodes"][node_id]
            with open(node_output_dir+ "/conf/nodes.json",'w',encoding='utf-8') as f:
                json.dump(nodes_json, f,ensure_ascii=False)
                 
            # copy conf/*
            print("copy conf/*")
            os.system("cp " + node_path + "/conf/* " + node_output_dir + "/conf/")

            # create configmap from files in node dir
            print("create configmap form all confs ...")
            os.system("rm -f " + node_output_dir + "/node-configs.yaml")
            os.system("kubectl create configmap {}-configs --from-file {} -o yaml --dry-run=client > {}".format(node_name, node_output_dir + "/conf/", node_output_dir + "/node-configs.yaml"))

            node_service = gen_node_service(args.chain_name, node_name)
            with open(node_output_dir + "/node-svc.yaml", 'w') as stream:
                yaml.dump(node_service, stream, sort_keys=False)

            node_sts = gen_node_sts(args.chain_name, node_name, args.version, args.image_pull_policy, args.storage_calss)
            with open(node_output_dir + "/node-sts.yaml", 'w') as stream:
                yaml.dump(node_sts, stream, sort_keys=False)
    print("Done!")


def main():
    args = parse_arguments()
    print("args:", args)
    work_dir = os.path.abspath(args.work_dir)
    run(args, work_dir)


if __name__ == '__main__':
    main()