# Deploy Legal Ground to AWS App Runner (from GitHub)

Public, always-on URL with **no AWS keys in your code** — App Runner runs your repo
and calls Bedrock through an IAM instance role. Region: **us-east-1**. Image: **hybrid**
(BM25 + vectors). No Docker required.

Files used by this guide (already in the repo):
- `apprunner.yaml` (repo root) — build/run config (venv in `/app`, model pre-cache).
- `deploy/iam-instance-role-trust.json` — who may assume the role (App Runner).
- `deploy/iam-bedrock-invoke-policy.json` — `bedrock:InvokeModel` permission.
- `deploy/create-bedrock-role.ps1` — creates the role via AWS CLI.

---

## Step 0 — Enable Bedrock model access (one time, easy to forget)

App Runner can only call a model your account is allowed to use.

1. AWS Console → **Bedrock** (region **us-east-1**) → **Model access**.
2. Enable access for **Anthropic Claude Haiku 4.5**.
3. Wait until status shows **Access granted**.

> If skipped, the app deploys fine but every question returns a 503 / AccessDenied.

## Step 1 — Create the Bedrock instance role (AWS CLI)

From the repo root, with the AWS CLI configured (`aws configure` or SSO):

```powershell
.\deploy\create-bedrock-role.ps1
```

Copy the **Role ARN** it prints (looks like `arn:aws:iam::<account-id>:role/LegalGroundBedrockRole`).
You'll paste it in Step 4.

## Step 2 — Push the config to GitHub

`apprunner.yaml` must be on the branch App Runner deploys.

```powershell
git add apprunner.yaml deploy/
git commit -m "Add App Runner deploy config"
git push origin main
```

## Step 3 — Connect the repo in App Runner

1. AWS Console → **App Runner** (us-east-1) → **Create service**.
2. **Source** → *Source code repository*.
3. **Add new** GitHub connection → authorize the AWS Connector for GitHub (one-time
   OAuth) → select repo **Akhilasiddamsetti/Legal-Ground**, branch **main**.
4. **Deployment trigger**: *Automatic* (redeploys on every push) is convenient; *Manual*
   gives you more control. Either is fine.

## Step 4 — Configure build & service

1. **Build settings** → choose **Use a configuration file** (it reads `apprunner.yaml`).
2. **Service settings**:
   - **Service name**: `legal-ground`
   - **Virtual CPU**: `1 vCPU`
   - **Memory**: `2 GB` (torch needs headroom — bump to 3–4 GB if you hit out-of-memory)
   - **Port**: `8080` (matches `apprunner.yaml`)
   - **Instance role**: select / paste the **Role ARN** from Step 1
   - Environment variables are already set in `apprunner.yaml` — nothing to add here.
3. (Optional) **Health check** → Protocol **HTTP**, Path `/health`.
4. **Create & deploy**.

## Step 5 — Wait, then test

First build takes ~5–10 min (it installs torch and caches the embedding model).
When status is **Running**, App Runner shows a **Default domain** like
`https://abcd1234.us-east-1.awsapprunner.com`.

```powershell
# health check (should return ok)
curl https://<your-id>.us-east-1.awsapprunner.com/health
```

Open the domain in a browser, ask a question, confirm you get a cited answer.
**That domain is the link you share for interviews.**

---

## Cost & safety (please read)

- **Bedrock is billed per question, and this URL is public (no auth).** Anyone with the
  link can ask questions and spend your Bedrock budget. For interviews that's usually
  fine, but: set an **AWS Budgets** alert, and **pause or delete the service** when you're
  not actively demoing (App Runner also bills a small amount for provisioned compute while
  running).
- **Pause when idle**: App Runner → service → **Pause** (stops request billing; resume in
  ~1 min before a call). **Delete** to stop all charges.
- **Self-declared identity**: visitors can pick any role/matter in the UI. The corpus is
  synthetic demo data, so this is safe — just never point `LG_CORPUS_DIR` at real client
  documents while the URL is public.

## Tightening the IAM policy (optional, later)

`iam-bedrock-invoke-policy.json` uses `"Resource": "*"` for simplicity. To scope it to
just the Haiku model, replace `*` with the model + inference-profile ARNs, e.g.:

```json
"Resource": [
  "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
  "arn:aws:bedrock:us-east-1:<account-id>:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0"
]
```

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Questions return 503 / AccessDenied | Bedrock model access not granted (Step 0), or instance role missing/forgot to attach. |
| `model not found` / not supported | The default id is the **global** inference profile. Uncomment `BEDROCK_MODEL` in `apprunner.yaml` (use the `us.` region-scoped id) and redeploy. |
| Out-of-memory / instance restarts | Raise Memory to 3–4 GB in service config. |
| Build fails importing sentence-transformers | Confirm the build used `apprunner.yaml` (venv in `/app`), not auto-detected commands. |
| Corpus empty / no evidence | Confirm `sample-docs/**/_retrieval/*` is committed and pushed (it is in this repo). |
