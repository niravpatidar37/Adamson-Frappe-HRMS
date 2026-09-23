# Local stacks

Two compose files, brought up independently. That is deliberate: Frappe and
the screening engine are separate failure domains, and running them as one
stack would quietly undo the reason for the split.

| File | What it runs | Needs a GPU |
| --- | --- | --- |
| `docker-compose.engine.yml` | Screening API, migrations, Postgres, Redis | no |
| `docker-compose.frappe.yml` | Frappe HR (system of record, recruiter UI) | no |
| `docker-compose.gpu.yml` | vLLM serving qwen3-vl | yes |

---

## Screening engine

Nothing here needs a GPU, Frappe, or a model. It is the ingestion path on its
own: a signed upload becomes a receipt row and a quarantined file.

### 1. Set the shared secret

Compose refuses to start without it. An unset secret would mean an engine that
accepts unsigned requests, and a request to this service writes a hiring score.

Generated into a variable and written straight into `deploy\.env`, so there is
nothing to copy by hand:

```powershell
cd "F:\Adamson Frappe HRMS\deploy"
Copy-Item .env.example .env -Force

$secret = python -c "import secrets; print(secrets.token_urlsafe(48))"
(Get-Content .env) -replace '^SCREENING_CALLBACK_SECRET=.*', "SCREENING_CALLBACK_SECRET=$secret" | Set-Content .env
```

Keep that PowerShell window: `$secret` is reused below. Use `Set-Content`, not
`Out-File` — Windows PowerShell's `Out-File` writes UTF-16, which Compose
cannot read.

### 2. Bring it up

```powershell
docker compose -f docker-compose.engine.yml up -d --build
docker compose -f docker-compose.engine.yml ps
```

First build takes a few minutes. Postgres publishes on **5433**, not 5432, so
it does not collide with the Postgres already on this machine. The API is on
<http://127.0.0.1:8100>.

```powershell
curl.exe http://127.0.0.1:8100/healthz
```

`curl.exe`, not `curl` — in PowerShell `curl` is an alias for
`Invoke-WebRequest`, which takes different arguments.

### 3. Send a resume

`curl` cannot do this alone: the signature covers the exact multipart body, so
the body has to be built before it is sent. `scripts\post_resume.py` does that
with nothing but the standard library.

Any real PDF works. If you do not have one to hand:

```powershell
cd "F:\Adamson Frappe HRMS"
[IO.File]::WriteAllText("some-cv.pdf", "%PDF-1.7`n1 0 obj`n<<>>`nendobj`ntrailer`n%%EOF`n")
```

Then, in the same window as step 1:

```powershell
$env:SCREENING_CALLBACK_SECRET = $secret

$r = python scripts\post_resume.py some-cv.pdf --applicant HR-APP-0001 --job HR-OPN-0001 | ConvertFrom-Json
python scripts\post_resume.py --receipt $r.receipt_id
```

The script prints its body on stdout and the status on stderr, which is what
makes `ConvertFrom-Json` work and saves copying the receipt id.

`"scorecard": null` is correct for now — the parse-and-score pipeline is still
a stub. What this proves is the part that has to be right first: the request is
authenticated, the file is inside the quarantine root, and the ledger has a
row.

Without the secret the same call returns `401`, as does a body altered after
signing.

### Checking the ledger directly

```powershell
docker compose -f deploy\docker-compose.engine.yml exec postgres `
  psql -U screening -d screening -c "select id, applicant_id, status, created_at from screening_receipts order by created_at desc limit 5;"
```

### Worker

Off by default, because the task it would run is still `NotImplementedError`:

```powershell
docker compose -f docker-compose.engine.yml --profile worker up -d
```

### Stopping

```powershell
docker compose -f docker-compose.engine.yml down        # keep the ledger
docker compose -f docker-compose.engine.yml down -v     # destroy it, and the resumes
```

`down -v` deletes the quarantine volume. Those are real candidate files once
this is wired to Frappe.

---

## Frappe HR (Phase 0 spike)

Not production. The stock `frappe/erpnext` image does not contain `hrms`, so a
custom image is built first.

### 1. Build `custom:16`

First, a Windows trap worth knowing about. `frappe_docker` ships no
`.gitattributes`, and Git for Windows checks out with CRLF by default. The
layered Containerfile copies `resources/core/main-entrypoint.sh` to
`/usr/local/bin/entrypoint.sh`, so a CRLF checkout gives it a `#!/bin/bash\r`
shebang. Linux then hunts for an interpreter called `/bin/bash\r` and reports
`exec /usr/local/bin/entrypoint.sh: no such file or directory` — blaming the
script rather than the interpreter. Every container built on that image
restarts with code 255; `configurator` and `create-site` survive only because
they override the entrypoint with `bash -c`.

The nginx config templates have the same problem one step later.

```powershell
cd F:\frappe_docker
git config core.autocrlf false
git config core.eol lf
git rm --cached -r . -q
git reset --hard
```

Then build:


`apps.json` is already written into the `frappe_docker` clone. It pins erpnext
and hrms to `version-16`, matching the v16 line `pwd.yml` uses.

```powershell
cd F:\frappe_docker
docker build `
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe `
  --build-arg=FRAPPE_BRANCH=version-16 `
  --secret=id=apps_json,src=apps.json `
  --tag=custom:16 `
  --file=images/layered/Containerfile .
```

Needs Docker Engine 23+ — the build uses BuildKit secrets so repository tokens
never land in image layers. Takes a while; it compiles frontend assets.

Note `--secret`, not `--build-arg`, for `apps.json`. Build arguments stay
visible in `docker image history` forever.

### 2. Start it

```powershell
cd "F:\Adamson Frappe HRMS\deploy"
docker compose -f docker-compose.frappe.yml up -d
docker compose -f docker-compose.frappe.yml logs -f create-site
```

Site creation runs once and installs both erpnext and hrms. Then open
<http://localhost:8081> — Administrator / admin.

### 3. What to check

Work through [`../docs/phase-0-spike.md`](../docs/phase-0-spike.md). Question 2
is already answered; start at 3.

Quickest confirmation that hrms installed: search the awesomebar for **Job
Applicant**. If it resolves, recruitment is present.

### Why this file is ours

`pwd.yml` in frappe_docker is upstream's and will be overwritten on `git pull`.
This copy is Adamson's, with two changes: the image is `custom:16`, and site
creation installs hrms. Diff them after upgrading frappe_docker.

Passwords here are `admin`. It is a throwaway local stack — never expose it.
