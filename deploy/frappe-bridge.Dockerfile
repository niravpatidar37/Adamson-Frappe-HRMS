# custom:16 plus the Adamson bridge app.
#
# A bind mount on its own does not work here. apps/ is image content, not a
# volume, and configurator writes `ls -1 apps > sites/apps.txt`. An app listed
# there but missing from the bench's Python env — which also lives in the
# image — makes every container fail on import, the whole stack restarting at
# once. So the app is copied in and installed editable.
#
# Editable also means a bind mount over the same path picks up host edits
# without reinstalling, which is the convenient way to iterate on tasks.py.
#
# Build from the repository root:
#   docker build -t adamson/frappe-hr:16 -f deploy/frappe-bridge.Dockerfile .
ARG BASE_IMAGE=custom:16
FROM ${BASE_IMAGE}

COPY --chown=frappe:frappe apps/adamson_screening_bridge \
     /home/frappe/frappe-bench/apps/adamson_screening_bridge

RUN /home/frappe/frappe-bench/env/bin/pip install --no-cache-dir \
      -e /home/frappe/frappe-bench/apps/adamson_screening_bridge

# Installing the app on the site is a separate, stateful step — it writes to
# the database. See deploy/README.md.
