# FISCO-BCOS in k8s

将`FISCO-BCOS`跑在`K8s`环境

## 软件依赖

### K3s

安装方法参见[Rancher官方文档](https://docs.rancher.cn/docs/k3s/quick-start/_index/#%E5%AE%89%E8%A3%85%E8%84%9A%E6%9C%AC)。

完成之后设置环境变量：
```
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

### FISCO-BCOS

参见[官方文档](https://fisco-bcos-doc.readthedocs.io/zh-cn/latest/docs/quick_start/air_installation.html)。

目前仅支持`Air`版本的非国密链。

## 使用方法

### 生成FISCO-BCOS链的配置文件

执行[FISCO-BCOS 官方文档](https://fisco-bcos-doc.readthedocs.io/zh-cn/latest/docs/quick_start/air_installation.html)前三个步骤，生成名为`fisco`的文件夹。

形如：

```bash
$ tree -L 3 fisco
fisco
├── bin
│   ├── fisco-bcos
│   └── fisco-bcos-linux-x86_64.tar.gz
├── build_chain.sh
├── get_account.sh
└── nodes
    ├── 127.0.0.1
    │   ├── ca
    │   ├── node0
    │   ├── node1
    │   ├── node2
    │   ├── node3
    │   ├── sdk
    │   ├── start_all.sh
    │   └── stop_all.sh
    └── ca
        ├── accounts
        ├── ca.crt
        ├── ca.key
        ├── ca.srl
        └── cert.cnf
```

### 生成K8s资源文件

执行脚本，脚本会对`FISCO-BCOS`链的配置文件进行修改，并生成对应的`K8s`资源文件。

```bash
$ python fisco-bcos-k8s.py               
args: Namespace(chain_name='test-chain', image_pull_policy='IfNotPresent', storage_calss='local-path', version='v3.5.0', work_dir='.')
processing node: fisco/nodes/127.0.0.1/node2 node_id 2 ...
modify config.ini ...                                                                                    
[p2p].listen_port now is 30302, change to 30300! 
[rpc].listen_port now is 20202, change to 20200!

...

copy conf/*
create configmap form all confs ...
Done!
```

生成的文件会放在`chain_name`参数命名的文件夹下，默认为`test-chain`。

```bash
$ tree -L 2 test-chain/
test-chain/
├── node0
│   ├── conf
│   ├── node-configs.yaml
│   ├── node-sts.yaml
│   └── node-svc.yaml
├── node1
│   ├── conf
│   ├── node-configs.yaml
│   ├── node-sts.yaml
│   └── node-svc.yaml
├── node2
│   ├── conf
│   ├── node-configs.yaml
│   ├── node-sts.yaml
│   └── node-svc.yaml
└── node3
    ├── conf
    ├── node-configs.yaml
    ├── node-sts.yaml
    └── node-svc.yaml
```

### 部署

```bash
kubectl apply -f test-chain/node0/
kubectl apply -f test-chain/node1/
kubectl apply -f test-chain/node2/
kubectl apply -f test-chain/node3/
```

查看结果

```bash
$ kubectl get po
NAME                 READY   STATUS             RESTARTS         AGE
test-chain-node1-0   0/1     CrashLoopBackOff   25 (3m32s ago)   105m
test-chain-node0-0   0/1     CrashLoopBackOff   25 (2m55s ago)   105m
test-chain-node2-0   0/1     CrashLoopBackOff   25 (2m15s ago)   105m
```

这里启动不成功是因为`FISCO-BCOS`仅支持节点使用`IP`作为节点地址，而在`K8s`环境，节点之间需要通过`Service`访问。

### 删除

```bash
kubectl delete -f test-chain/node0/
kubectl delete -f test-chain/node1/
kubectl delete -f test-chain/node2/
kubectl delete -f test-chain/node3/
```
