#!/usr/bin/env bash
# Load the last N days of cost history so the detector has data on day 1.
# Usage: ./scripts/backfill.sh [days] [function-name]
set -euo pipefail
DAYS="${1:-8}"
FN="${2:-ai-cost-guardian-collector}"
for i in $(seq "$DAYS" -1 1); do
  D=$(date -d "-$i day" +%F 2>/dev/null || date -v-"$i"d +%F)
  echo "Backfilling $D"
  aws lambda invoke --function-name "$FN" --cli-binary-format raw-in-base64-out \
    --payload "{\"date\":\"$D\",\"skip_detection\":true}" /dev/null >/dev/null
done
echo "Done."
