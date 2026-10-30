# Deploying Questionize

One Linux server runs everything through [Kamal 2](https://kamal-deploy.org): the Rails app (`web` and `job` roles behind kamal-proxy with Let's Encrypt TLS), PostgreSQL (`db` accessory) and the AI service (`ai` accessory, no public port). GitHub Actions builds both images on every push to `main` and pushes them to GHCR; you deploy from your own machine.

Nothing environment-specific is committed: the server address and every secret come from your shell environment.

## 1. Prepare the server (once)

1. Create or rebuild a server with **Ubuntu 24.04** and add your SSH public key. A 2 vCPU / 2 GB machine is enough to start; resize to 4 GB if memory gets tight.
2. Firewall: allow inbound TCP **22** (ideally only from your IP), **80** and **443**, plus ICMP. Nothing else; PostgreSQL is bound to localhost.
3. Add swap, which helps a 2 GB machine absorb spikes:

   ```bash
   ssh root@$KAMAL_HOST 'fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo "/swapfile none swap sw 0 0" >> /etc/fstab'
   ```

Kamal installs Docker itself on the first `kamal setup`.

## 2. DNS

Point the domain at the server before the first deploy so the TLS certificate can be issued:

| Type | Name | Value |
|---|---|---|
| A | `@` | server IPv4 |
| AAAA | `@` | server IPv6 |
| CNAME | `www` | `questionize.org` |

If the DNS provider proxies traffic (e.g. Cloudflare), keep the proxy off until the certificate is issued.

## 3. Environment on your machine

Install Ruby 3.3 and run `bundle install` in `api/`. Then export (for example from a password manager or a local, untracked file you `source`):

```bash
export KAMAL_HOST=...                     # server IPv4
export KAMAL_REGISTRY_USERNAME=...        # your GitHub username
export KAMAL_REGISTRY_PASSWORD=...        # GitHub token with read:packages (write:packages to build locally)
export SECRET_KEY_BASE=...                # bin/rails secret
export QUESTIONIZE_DATABASE_PASSWORD=...  # openssl rand -hex 24
export AI_INTERNAL_TOKEN=...              # openssl rand -hex 32
export MODEL_API_KEY=...                  # Meta Model API
export FACEBOOK_APP_ID=...                # Facebook Login (optional until the Meta app exists)
export FACEBOOK_APP_SECRET=...
export BASETEN_API_KEY=                   # optional
export ANTHROPIC_API_KEY=                 # optional, development provider
```

`api/.kamal/secrets` only references these variables; never write values into it.

## 4. Deploy

Wait for the **Images** workflow on the commit you want to finish, then from `api/`:

```bash
# First time: installs Docker, starts kamal-proxy, the accessories and the app
bin/kamal setup --skip-push --version $(git rev-parse HEAD)

# Every later deploy
bin/kamal deploy --skip-push --version $(git rev-parse HEAD)
```

The AI service accessory runs the `latest` image; after an AI change, refresh it with `bin/kamal accessory reboot ai`.

Pushing to `main` builds images; it does not deploy the running app. Both web and job roles must use the intended commit after a deploy. The image includes the separate Vue + TypeScript research console at `/admin`, served from its own entry point with the aggregate export in `research/results/dashboard.json`. Regenerate that export with `python -m questionize.scoreboard` in `ai/` before committing new experiment records.

The learner app shows GMAT, LSAT and GRE by default. `VITE_ALL_LEVELS=true` during the web build restores all seven choices; the complete level catalog and existing profiles remain intact. The service worker is served with `Cache-Control: no-cache` so installed apps can discover releases, and it does not cache the research console as the learner app's offline shell.

### Research policy cycles

The Evolution console needs both current app and AI images. After an AI source change, refresh the `ai` accessory as well as deploying the app. E8's migration adds a cycle registry and immutable versions; it does not import any questions or change learner records.

Prepare a private replay pack with `python -m questionize.build_evolution_benchmark --help` in `ai/`. The builder reads private E1 inputs but exports only abstract decision records with hashed identifiers and answer letters. From `api/`, the operator can import that pack on stdin with `bin/rails questionize:research_import`, queue one cycle with `bin/rails questionize:research_cycle`, and inspect it with `bin/rails questionize:research_status`. In production these commands run inside the app container. Do not place the private pack or environment values in the repository.

`RESEARCH_EVOLUTION_ENABLED=true` enables usage-triggered eligibility checks. The initial scope waits for three new independent keyed GMAT CR observations or twenty new rated answers, with a 24-hour automatic cooldown, one in-flight cycle and a daily two-proposal limit. Delayed checks coalesce events; the recurring job also checks readiness. These are proposal gates, not assertions that a learner miss proves a bad item. A held or failed cycle does not advance the active policy. An operator-requested research replay is visibly labeled separately from a usage batch.

Useful commands: `bin/kamal logs`, `bin/kamal console`, `bin/kamal accessory logs ai`, `bin/kamal app details`.

## 5. Check

- `https://questionize.org/up` returns 200.
- `bin/kamal accessory exec ai "python -c \"import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())\""` shows the configured models.
