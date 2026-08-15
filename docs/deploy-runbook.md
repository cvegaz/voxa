# Deploy runbook — Voxa, Stage 1

Everything needed to put Voxa in production and keep it there. The
infrastructure is already applied; what remains is the **first deploy**, which
is manual by necessity (the server has no files yet). After that, deploys are
automatic on every merge to `main`.

For *why* the pieces look the way they do, see
[ADR-0019](adr/0019-public-demo-limits.md) and the commentary inside
`infra/terraform/`, `docker-compose.prod.yml` and `deploy/Caddyfile`.

## What exists already

| | |
|---|---|
| Domain | `tryvoxa.com` — registered at **Porkbun**, DNS delegated to Route 53 |
| Hosted zone | `Z100383221IVGAJZQDSGH` (created by hand, tagged `Project=voxa`) |
| Server | `i-0e4bb82ab4bf45264` — t4g.small, Ubuntu 24.04 ARM, `mx-central-1c` |
| Public IP | `78.13.12.185` (Elastic — survives stops and rebuilds) |
| DNS | `tryvoxa.com`, `www.`, `app.` all → the Elastic IP |
| SSH key | `~/.ssh/voxa` (passphrase-protected; only for emergencies — deploys use SSM) |
| Deploy role | `arn:aws:iam::275123487888:role/voxa-github-deploy` |
| Terraform state | `s3://playpro-tfstate-275123487888/voxa/stage1/terraform.tfstate` |
| Running cost | ≈ **$20/month** (t4g.small $12.85 + 30 GB gp3 ~$2.70 + IPv4 ~$3.65 + zone $0.50) |

Route 53 **Domains** registration is blocked on this AWS account — two attempts
rejected in under a second with an opaque message, support case open. Hence
Porkbun. Route 53 **DNS** is unaffected; registrar and DNS host are separate
services.

## Why the domain is at one vendor and the DNS at another

The delegation is what ties them: Porkbun stores only "ask AWS", and Route 53
holds the actual records so Terraform manages them.

**Consequence to remember:** the four nameservers Route 53 assigned are
referenced *externally*. Never `terraform destroy` the hosted zone — it is a
`data` source precisely so Terraform cannot — because a recreated zone gets a
**different** set of four, and DNS stays dark until someone re-pastes them at
Porkbun.

---

## One-time: a GHCR pull token

The published images are private by default even though the repo is public, so
the server needs credentials to pull them.

Create a GitHub **Personal Access Token (classic)** with the single scope
**`read:packages`**. Nothing else. Keep it out of the repo.

> **Optional simplification.** Making the three packages public
> (GitHub → your profile → Packages → each package → Package settings → Change
> visibility) removes this token entirely: `docker pull` needs no auth for a
> public image, so there is no long-lived credential sitting in
> `~/.docker/config.json` on the server and nothing to rotate. The images are
> built from a public repo with public Dockerfiles, so they reveal little that
> is not already readable. Worth doing once the first deploy is proven; do not
> change two things at once.

---

## Paso 1 — Prepare the production env file (locally)

```bash
cp .env.production.example .env.production
```

Then fill it in. The values that matter:

```bash
VOXA_DOMAIN=tryvoxa.com
POSTGRES_PASSWORD=$(openssl rand -base64 24)   # generate, do not invent
OPENAI_API_KEY=<the key from the voxa-demo OpenAI project>
TRUSTED_PROXY_HOPS=2                            # Caddy -> nginx -> backend
LANDING_ORIGINS=                                # empty: the landing is same-origin
```

Three things to get right, because each fails silently:

- **`OPENAI_API_KEY` must be the `voxa-demo` project key**, not the one shared
  with pps. That project carries the $15/month spend limit, the
  `whisper-1` + `gpt-4o-mini` allowlist and 10 RPM.
- **`TRUSTED_PROXY_HOPS=2`** must match the real topology. Too low and every
  visitor shares one rate-limit bucket; too high and it falls back to the peer
  address. Neither logs an error.
- **`LANDING_ORIGINS` stays empty.** The landing calls `/api/contact`
  same-origin through its own nginx, so there is no cross-origin request to
  allow. Filling it in would only widen CORS for no reason.

`.env.production` holds secrets and is git-ignored. Never commit it.

## Paso 2 — Copy the deploy files to the server

The compose file mounts `./deploy/Caddyfile`, so the relative layout matters.

```bash
IP=$(cd infra/terraform && terraform output -raw public_ip)

ssh -i ~/.ssh/voxa ubuntu@$IP 'mkdir -p ~/voxa/deploy'
scp -i ~/.ssh/voxa docker-compose.prod.yml ubuntu@$IP:~/voxa/
scp -i ~/.ssh/voxa deploy/Caddyfile        ubuntu@$IP:~/voxa/deploy/
scp -i ~/.ssh/voxa .env.production         ubuntu@$IP:~/voxa/
```

If SSH times out, the cause is almost always that your home IP changed. Refresh
it and re-apply:

```bash
curl https://checkip.amazonaws.com
# update ssh_ingress_cidr in infra/terraform/terraform.tfvars, then:
cd infra/terraform && terraform apply
```

## Paso 3 — Log in to GHCR and start the stack

```bash
ssh -i ~/.ssh/voxa ubuntu@$IP
cd ~/voxa

echo "<YOUR_READ_PACKAGES_PAT>" | docker login ghcr.io -u cvegaz --password-stdin

docker compose -f docker-compose.prod.yml --env-file .env.production pull
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

That `docker login` is what the automatic deploys reuse: the SSM command runs as
`ubuntu` and relies on this cached session. Do it once, here.

On first start the backend applies migrations 001→010 and then serves. Caddy
requests certificates for all three hostnames. **DNS already resolves**, so the
ACME challenge should pass on the first try — which matters, because Let's
Encrypt rate-limits failures.

## Paso 4 — Verify

```bash
docker compose -f docker-compose.prod.yml ps        # five services up, db healthy
docker compose -f docker-compose.prod.yml logs caddy | grep -i certificate
```

From your machine:

```bash
curl -sI https://tryvoxa.com            | head -1   # 200, the landing
curl -sI https://app.tryvoxa.com        | head -1   # 200, the demo SPA
curl -sI https://www.tryvoxa.com        | head -1   # 301 to the apex
curl -sI http://tryvoxa.com             | head -1   # 308 to HTTPS

# security headers present, Server banner gone
curl -sI https://tryvoxa.com | grep -iE "strict-transport|x-frame|x-content|referrer|^server"

# the contact form reaches the backend through the apex
curl -s -X POST https://tryvoxa.com/api/contact -H 'Content-Type: application/json' \
  -d '{"name":"Deploy check","email":"you@example.com","message":"First deploy verification."}'

# and the apex does NOT expose the rest of the API (expect the SPA, not JSON)
curl -sI https://tryvoxa.com/api/schemas | head -1
```

Then do the one check no script covers: **open the site and record a narration.**
The demo limits, the microphone permission and the ffprobe duration measurement
only prove themselves end to end.

---

## The release loop (automatic)

1. Open a PR, merge it to `main`.
2. **CI** runs: backend pytest, frontend and landing lint + typecheck + tests.
3. Only if CI concludes successfully, **docker-publish** builds the three
   multi-arch images, pushes them to GHCR, and sends one SSM command to the
   server: `pull && up -d`.

Nothing to do by hand. Compose recreates only the containers whose image
changed; Postgres and its volume are untouched.

Watch it in the repo's Actions tab. The deploy job prints the SSM CommandId and
the command's output, so a failed deploy is diagnosable from the log alone.

### If a deploy breaks production

Every build is tagged with its commit SHA, so a rollback is a pin and a restart:

```bash
ssh -i ~/.ssh/voxa ubuntu@$IP
cd ~/voxa
# set the three VOXA_*_IMAGE lines in .env.production to a known-good SHA tag:
#   VOXA_BACKEND_IMAGE=ghcr.io/cvegaz/voxa-backend:<sha>
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

Remember to put them back to `:latest` once the fix ships, or the next
auto-deploy will appear to do nothing.

---

## Operations

### Backups (not automated yet)

The bucket and the server's write-only permission exist; the daily `pg_dump`
cron does not. Manual snapshot:

```bash
ssh -i ~/.ssh/voxa ubuntu@$IP \
  'cd ~/voxa && docker compose -f docker-compose.prod.yml exec -T db \
   pg_dump -U postgres db_audio_excel' > voxa_backup_$(date +%F).sql
```

Worth automating before the demo has real traffic: this database holds the
captured leads and the funnel history, which is the entire answer to "did the
month work".

### The funnel report

```bash
ssh -i ~/.ssh/voxa ubuntu@$IP
cd ~/voxa
docker compose -f docker-compose.prod.yml exec -T backend python scripts/funnel_report.py
```

Sessions, aha rate, downloads, leads by capture point, walls hit, spend, and
cost per captured lead.

### Tuning the demo limits

Every cap is an environment variable, so a monthly adjustment is an edit plus a
restart — never a rebuild:

```bash
# edit ~/voxa/.env.production, then
docker compose -f docker-compose.prod.yml --env-file .env.production up -d backend
```

**Launch-day note.** The monthly ceiling ($7 ≈ 800 complete sessions) is not the
binding constraint; the daily one ($0.45 ≈ 51 sessions) is, and that is exactly
the order of magnitude of a LinkedIn post that lands well. Raising
`DEMO_BUDGET_DAILY_USD` to ~$2.00 for a launch window **does not increase total
exposure** — the monthly cap still bounds it. It only lets a good day spend
faster, which is what a good day should do.

### Stopping the meter

```bash
cd infra/terraform && terraform destroy
```

Removes the server, the IP and the records. The **hosted zone survives** by
design, so Porkbun's delegation stays valid and bringing it back is one
`terraform apply`.
