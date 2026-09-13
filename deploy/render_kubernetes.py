"""Emit Kubernetes resources from Compose's .env-resolved environment.

Pipe stdout directly to kubectl. It contains credentials; do not save or commit it.
Nothing is deployed by this script.
"""
from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from typing import Any


def resources(env: Mapping[str, str]) -> dict[str, Any]:
    namespace = env.get('MIJOBS_KUBE_NAMESPACE', 'workforce')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', namespace):
        raise ValueError('MIJOBS_KUBE_NAMESPACE must be a valid DNS label')
    try:
        port = int(env.get('MIJOBS_MCP_PORT', '8000'))
    except ValueError as exc:
        raise ValueError('MIJOBS_MCP_PORT must be an integer') from exc
    if not 1 <= port <= 65535:
        raise ValueError('MIJOBS_MCP_PORT must be in 1..65535')
    image = env.get('MIJOBS_KUBE_IMAGE', 'michigan-workforce-intelligence:local')
    storage = env.get('MIJOBS_KUBE_STORAGE', '10Gi')
    if not image or not re.fullmatch(r'[1-9][0-9]*(?:Mi|Gi|Ti)', storage):
        raise ValueError('Set a nonempty image and positive storage quantity, e.g. 10Gi')
    name = 'workforce-mcp'
    metadata = {'name': name, 'namespace': namespace}
    labels = {'app.kubernetes.io/name': name}
    runtime = {key: env.get(key, '') for key in (
        'BLS_API_KEY', 'CENSUS_API_KEY', 'ONET_USERNAME', 'ONET_PASSWORD')}
    runtime.update({
        'MIJOBS_DATABASE_URL': env.get('MIJOBS_DATABASE_URL', 'sqlite:////data/mijobs.db'),
        'MIJOBS_ARTIFACT_ROOT': env.get('MIJOBS_ARTIFACT_ROOT', '/data/artifacts'),
        'MIJOBS_MCP_WRITE_ENABLED': env.get('MIJOBS_MCP_WRITE_ENABLED', 'false'),
        'MIJOBS_MCP_PORT': str(port),
    })
    probe = {'exec': {'command': ['python', '-m', 'mijobs.healthcheck']}, 'timeoutSeconds': 5,
             'periodSeconds': 15, 'failureThreshold': 4}
    return {'apiVersion': 'v1', 'kind': 'List', 'items': [
        {'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': namespace}},
        {'apiVersion': 'v1', 'kind': 'Secret', 'metadata': metadata, 'type': 'Opaque', 'stringData': runtime},
        {'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim', 'metadata': metadata, 'spec': {
            'accessModes': ['ReadWriteOnce'], 'resources': {'requests': {'storage': storage}}}},
        {'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': metadata, 'spec': {
            'replicas': 1, 'strategy': {'type': 'Recreate'}, 'selector': {'matchLabels': labels},
            'template': {'metadata': {'labels': labels}, 'spec': {
                'automountServiceAccountToken': False,
                'securityContext': {'runAsNonRoot': True, 'runAsUser': 10001, 'runAsGroup': 10001,
                                    'fsGroup': 10001, 'seccompProfile': {'type': 'RuntimeDefault'}},
                'containers': [{'name': name, 'image': image, 'imagePullPolicy': 'IfNotPresent',
                    'ports': [{'name': 'mcp', 'containerPort': port}],
                    'envFrom': [{'secretRef': {'name': name}}],
                    'volumeMounts': [{'name': 'evidence', 'mountPath': '/data'}],
                    'resources': {'requests': {'cpu': '100m', 'memory': '128Mi'},
                                  'limits': {'cpu': '1', 'memory': '512Mi'}},
                    'securityContext': {'allowPrivilegeEscalation': False,
                                        'capabilities': {'drop': ['ALL']}},
                    'readinessProbe': probe,
                    'startupProbe': {**probe, 'failureThreshold': 12}}],
                'volumes': [{'name': 'evidence', 'persistentVolumeClaim': {'claimName': name}}],
            }}}},
        {'apiVersion': 'v1', 'kind': 'Service', 'metadata': metadata, 'spec': {
            'type': 'ClusterIP', 'selector': labels,
            'ports': [{'name': 'mcp', 'port': port, 'targetPort': 'mcp'}]}},
    ]}


def main() -> None:
    print(json.dumps(resources(os.environ), indent=2))


if __name__ == '__main__':
    main()
