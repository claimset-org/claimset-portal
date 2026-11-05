#!/bin/sh
# Start the portal with the newest claimset (design §10). Set PORTAL_CLAIMSET_UPDATE=0 to skip the update.
set -u
if [ "${PORTAL_CLAIMSET_UPDATE:-1}" != "0" ]; then
  pip install --user --quiet --upgrade --no-deps \
      "claimset @ git+${PORTAL_CLAIMSET_SOURCE:-https://github.com/entrylib/claimset}" \
    || echo "portal: could not update claimset; using the installed one" >&2
fi
exec portal serve --port 8000
