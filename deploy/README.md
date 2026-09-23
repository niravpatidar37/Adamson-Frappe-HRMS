# Local spike stack

Brings up Frappe HR for the Phase 0 spike. Not production.

The stock `frappe/erpnext` image does not contain `hrms`, so a custom image
is built first.

## 1. Build `custom:16`

`apps.json` is already written into the `frappe_docker` clone. It pins
erpnext and hrms to `version-16`, matching the v16 line `pwd.yml` uses.

```powershell
cd F:\frappe_docker
docker build `
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe `
  --build-arg=FRAPPE_BRANCH=version-16 `
  --secret=id=apps_json,src=apps.json `
  --tag=custom:16 `
  --file=images/layered/Containerfile .
```

Needs Docker Engine 23+ — the build uses BuildKit secrets so repository
tokens never land in image layers. Takes a while; it compiles frontend assets.

Note `--secret`, not `--build-arg`, for `apps.json`. Build arguments stay
visible in `docker image history` forever.

## 2. Start it

```powershell
cd "F:\Adamson Frappe HRMS"
docker compose -f deploy\compose\pwd-hrms.yml up -d
```

Site creation runs once and installs both erpnext and hrms. Watch it:

```powershell
docker compose -f deploy\compose\pwd-hrms.yml logs -f create-site
```

Then open <http://localhost:8080> — Administrator / admin.

## 3. What to check

Work through [`../docs/phase-0-spike.md`](../docs/phase-0-spike.md).
Question 2 is already answered; start at 3.

Quickest confirmation that hrms installed: search the awesomebar for
**Job Applicant**. If it resolves, recruitment is present.

## Stopping and resetting

```powershell
docker compose -f deploy\compose\pwd-hrms.yml down          # stop, keep data
docker compose -f deploy\compose\pwd-hrms.yml down -v       # destroy volumes
```

`down -v` deletes the database and the sites volume, including any uploaded
files. Fine during the spike, worth thinking twice about later.

## Why this file exists

`pwd.yml` in frappe_docker is upstream's and will be overwritten on `git pull`.
This copy is Adamson's, with two changes: the image is `custom:16`, and site
creation installs hrms. Diff them after upgrading frappe_docker.

Passwords here are `admin`. It is a throwaway local stack — never expose it.
