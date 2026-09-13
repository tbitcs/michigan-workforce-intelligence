# Agent connections and optional Kubernetes

## Use Docker Compose now

The MCP service joins the network named by `MIJOBS_NETWORK_NAME` in the root `.env` (default `michigan-workforce`). It is reachable at `http://workforce-mcp:8000/mcp` inside that network. Substitute the configured port if changed.

In the **agent's** Compose project, attach its service to that existing network:

```yaml
services:
  agent:
    # Keep your existing agent image, command and settings.
    networks: [workforce]

networks:
  workforce:
    external: true
    name: michigan-workforce
```

Start this MCP service first so the network exists. Configure your agent's MCP client with Streamable HTTP and the internal URL above. The exact agent setting name depends on its framework; this project does not assume one. An agent container's `localhost` refers to itself, so use the service DNS name. The agent needs neither the evidence volume nor the Docker socket.

## Kubernetes later

`render_kubernetes.py` generates Kubernetes resources from the **same root `.env`**, resolved by Compose. Nothing is deployed during normal setup.

It emits a Namespace, runtime Secret, persistent volume claim, a single-replica Deployment with Recreate updates, and an internal ClusterIP Service. SQLite stays on one writer pod; do not increase replicas. The cluster needs a default storage class. Compose data is not automatically migrated to the new PVC.

When you choose to deploy:

1. Make the runtime image available to the cluster: load `michigan-workforce-intelligence:local` into your local cluster, or publish a versioned image to your chosen registry. Set `MIJOBS_KUBE_IMAGE` accordingly in `.env`.
2. Set `MIJOBS_KUBE_NAMESPACE` and `MIJOBS_KUBE_STORAGE` in `.env` if needed.
3. With `kubectl` configured for the intended cluster, render inside Docker and pipe directly to Kubernetes:

```sh
docker compose run --build --rm -T --entrypoint python cli deploy/render_kubernetes.py | kubectl apply -f -
```

The stream includes source credentials as a Kubernetes Secret; do not save it to a tracked file or paste it into chat. Use your cluster's normal secret access controls. Rendering itself does not create a cluster, push an image, or run kubectl.

The agent pod in the same namespace connects to `http://workforce-mcp:8000/mcp`. Across namespaces, use `http://workforce-mcp.workforce.svc.cluster.local:8000/mcp` (substitute your namespace/port/cluster domain). The MCP endpoint is internal; no Ingress or public service is created. Put only trusted agents in its allowed network; add your cluster's NetworkPolicy/authentication before sharing it with untrusted tenants.

After changing `.env`, reapply the generated resources and restart the deployment so pods receive the changed Secret values:

```sh
kubectl -n workforce rollout restart deployment/workforce-mcp
kubectl -n workforce rollout status deployment/workforce-mcp
```

Kubernetes replaces the local manager for service lifecycle: use your cluster's tooling for logs and deployments. Keep using the Docker CI target for local quality checks.

References: [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/), [service DNS](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/), [persistent volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/).
