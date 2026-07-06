# NKP Academy — Bootcamp Lab Guide

**Deploy the NKP exam-prep app to your Nutanix NKP HPOC cluster.**

This is a hands-on lab. By the end you'll have **NKP Academy** — the gamified NCP-CN
study app — running on your own Nutanix Kubernetes Platform (NKP) cluster, reachable
in your browser. Budget **~15 minutes**.

> You'll practice the exact NKP skills you trained on: pointing `kubectl` at a
> cluster, reading a Service's external IP, installing with Helm, and using
> Traefik ingress — the app you deploy is the same one you studied with.

---

## What you'll deploy

- A single container (`wnorris22/nkp:1.8.1`) that serves the API **and** the web UI.
- Exposed through your cluster's **Traefik** ingress (NKP's default).
- 20 modules / 574 questions across NCP-CN Sections 1–4, plus a Practice Exam.

## What you need

| Requirement | Notes |
|---|---|
| `kubectl` and `helm` | On your laptop. `helm version` should print v3.x. |
| Kubeconfig for your HPOC NKP cluster | Provided by your instructor (a `*.conf` file or download from the Kommander UI). |
| The `nkp-academy` repo | Cloned locally — your instructor will share the clone URL. |

You do **not** need Docker or to build anything — the image is already published.

---

## Instructor prep (before the session)

<sub>Partners can skip this — it's for whoever runs the bootcamp.</sub>

1. **Confirm the image is public and pullable.** It lives at `wnorris22/nkp:1.8.1`.
   Verify the tag exists: `curl -s "https://hub.docker.com/v2/repositories/wnorris22/nkp/tags" | grep 1.8.1`.
2. **Make the deployment assets available.** Push this repo to a Git host partners
   can reach and share the clone URL, or hand out the packaged chart
   (`helm package deploy/helm/nkp-academy`).
3. **Give each partner cluster access** — a kubeconfig for their HPOC NKP cluster.
4. **Check egress.** HPOC clusters sometimes can't reach Docker Hub. If image pulls
   fail, load `wnorris22/nkp:1.8.1` into the cluster's internal registry (e.g. Harbor)
   and have partners add `--set image.repository=<your-registry>/nkp`. *(This is the
   air-gapped registry-seeding pattern from Section 1 — a nice teachable moment.)*
5. **Decide the cluster model** (affects naming below):
   - **Own cluster per partner** → everyone uses the simple names in this guide.
   - **One shared cluster** → each partner appends their initials to the release,
     namespace, and host so deployments don't collide (shown in each step).

---

## Part 1 — Connect to your HPOC cluster

Point `kubectl` at the kubeconfig your instructor gave you, then confirm you're
talking to the right cluster:

```bash
export KUBECONFIG=~/nkp-hpoc.conf      # path to your kubeconfig
kubectl get nodes
```

You should see the cluster's nodes in `Ready` state.

## Part 2 — Find your cluster's ingress IP

NKP routes web traffic through **Traefik**. Find its external IP — this is where
your app will be reachable:

```bash
kubectl get svc -A | grep -i traefik
```

Look at the `kommander-traefik` row with type `LoadBalancer`. Note the value in the
**EXTERNAL-IP** column (the *second* IP, not the cluster IP) — call it `<LB-IP>`.

## Part 3 — Deploy NKP Academy

From the repo root, install the chart. We use a **nip.io** hostname built from your
`<LB-IP>` so it resolves automatically — no DNS or `/etc/hosts` edits needed.

```bash
helm upgrade --install nkp-academy deploy/helm/nkp-academy \
  --namespace nkp-academy --create-namespace \
  --set image.tag=1.8.1 \
  --set ingress.host=nkp-academy.<LB-IP>.nip.io
```

Replace `<LB-IP>` with the IP from Part 2.

<details>
<summary><strong>Shared cluster?</strong> Add your initials so you don't collide with others.</summary>

```bash
# example for partner "JD"
helm upgrade --install nkp-academy-jd deploy/helm/nkp-academy \
  --namespace nkp-academy-jd --create-namespace \
  --set image.tag=1.8.1 \
  --set ingress.host=nkp-academy-jd.<LB-IP>.nip.io
```
</details>

The chart already targets NKP's `kommander-traefik` ingress class and runs as a
hardened non-root pod — no extra flags required.

## Part 4 — Verify & open

```bash
kubectl -n nkp-academy rollout status deploy/nkp-academy
curl -skL https://nkp-academy.<LB-IP>.nip.io/healthz
```

The `curl` should return `{"status":"ok","version":"1.0.0","modules_loaded":20}`.
Then open it in your browser:

**`http://nkp-academy.<LB-IP>.nip.io`**

(If the browser redirects to HTTPS and warns about the certificate, accept it — the
lab uses a self-signed cert.)

## Part 5 — Try it out

1. **Log in** with your name (no password — it's a training sandbox).
2. Open a **track** (e.g. NCP-CN Section 1) and answer a few questions — you get
   instant feedback, the correct answer, an explanation, and a **link to the exact
   Nutanix doc** so you can verify it.
3. Click **Practice Exam** → **Standard (50)**. It pulls questions from every
   section and gives you a scored report with a per-section breakdown — a quick read
   on where you're exam-ready and where to review.

---

## Troubleshooting

| Symptom | Cause & fix |
|---|---|
| Browser shows **"404 page not found"** | Traefik has no matching route — usually a wrong ingress class. Confirm with `kubectl get ingressclass` (expect `kommander-traefik`) and redeploy with `--set ingress.className=<name>`. |
| **Can't reach the URL at all** | You likely used the cluster IP instead of the external IP. Re-check Part 2 (`grep traefik`, EXTERNAL-IP column). Or bypass ingress entirely — see below. |
| Pod stuck in **`ImagePullBackOff`** | The image tag is wrong or the cluster can't reach Docker Hub. Check `kubectl -n nkp-academy get pods`. If it's egress, ask your instructor about the internal-registry option. |
| **`/healthz` slow to respond** on first load | The app seeds demo data on startup — give it ~30–60s, then retry. |
| Want to skip ingress/DNS completely | Port-forward straight to the pod: `kubectl -n nkp-academy port-forward svc/nkp-academy 8080:80` then open `http://localhost:8080`. |

## Cleanup

When you're done, remove everything you created:

```bash
helm uninstall nkp-academy -n nkp-academy
kubectl delete namespace nkp-academy
```

---

<sub>NKP Academy · Built for Nutanix channel partners · Content sourced from the
Nutanix Kubernetes Platform 2.17 Administrator Guide.</sub>
