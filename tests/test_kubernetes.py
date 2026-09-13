from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('render_kubernetes', Path(__file__).parents[1] / 'deploy/render_kubernetes.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_kubernetes_defaults_preserve_local_contract():
    items = {item['kind']: item for item in module.resources({})['items']}
    assert items['Deployment']['spec']['replicas'] == 1
    assert items['Deployment']['spec']['strategy']['type'] == 'Recreate'
    assert items['Service']['spec']['type'] == 'ClusterIP'
    assert items['Secret']['stringData']['MIJOBS_MCP_WRITE_ENABLED'] == 'false'
    assert items['PersistentVolumeClaim']['spec']['accessModes'] == ['ReadWriteOnce']
    pod = items['Deployment']['spec']['template']['spec']
    assert not pod['automountServiceAccountToken']
    assert pod['containers'][0]['volumeMounts'][0]['mountPath'] == '/data'


def test_kubernetes_custom_env_and_secrets():
    items = {item['kind']: item for item in module.resources({
        'MIJOBS_KUBE_NAMESPACE': 'agents', 'MIJOBS_MCP_PORT': '8123',
        'MIJOBS_KUBE_IMAGE': 'registry.example/workforce:1', 'BLS_API_KEY': 'test$quoted',
    })['items']}
    assert items['Secret']['stringData']['BLS_API_KEY'] == 'test$quoted'
    assert items['Service']['spec']['ports'][0]['port'] == 8123
    container = items['Deployment']['spec']['template']['spec']['containers'][0]
    assert container['ports'][0]['containerPort'] == 8123
    assert container['image'] == 'registry.example/workforce:1'
    assert items['Deployment']['metadata']['namespace'] == 'agents'


@pytest.mark.parametrize('env', [
    {'MIJOBS_KUBE_NAMESPACE': 'invalid/name'}, {'MIJOBS_MCP_PORT': '0'},
    {'MIJOBS_MCP_PORT': 'bad'}, {'MIJOBS_KUBE_STORAGE': 'zero'}, {'MIJOBS_KUBE_IMAGE': ''},
])
def test_kubernetes_invalid_config(env):
    with pytest.raises(ValueError):
        module.resources(env)
