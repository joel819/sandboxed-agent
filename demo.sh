#!/usr/bin/env bash
# Three scenarios: one allowed action, two blocked ones. Every command and log
# line below is a real OpenShell command - see README.md for the doc citations.
set -uo pipefail

SANDBOX="sandboxed-agent-demo"
IMAGE="sandboxed-agent:demo"

cleanup() {
  echo "--- cleaning up sandbox ---"
  openshell sandbox delete --name "$SANDBOX" >/dev/null 2>&1
}
trap cleanup EXIT

echo "=== building image (unrestricted docker build - deps get baked in here) ==="
docker build -t "$IMAGE" . || { echo "docker build failed"; exit 1; }

echo "=== creating sandbox under policy.yaml ==="
openshell sandbox create --name "$SANDBOX" --from "$IMAGE" --policy policy.yaml --no-auto-providers \
  || { echo "sandbox create failed - is the OpenShell gateway running? (openshell gateway status)"; exit 1; }

# Each `sandbox exec` is a separate process, so an env var set in one call does not carry over to the
# next. The key is therefore passed on the scenario 1 command itself (empty = canned mode).

print_result () {
  local label="$1" verdict="$2"
  echo ""
  echo "--- $label: $verdict ---"
}

echo ""
echo "############################################"
echo "# Scenario 1: normal question (should succeed)"
echo "############################################"
echo "Attempting: run_agent.py \"where is order A101?\""
if openshell sandbox exec --name "$SANDBOX" -- env GROQ_API_KEY="${GROQ_API_KEY:-}" GROQ_MODEL="${GROQ_MODEL:-openai/gpt-oss-120b}" python3 run_agent.py "where is order A101?"; then
  print_result "Scenario 1" "ALLOWED"
else
  print_result "Scenario 1" "UNEXPECTED FAILURE"
fi

echo ""
echo "############################################"
echo "# Scenario 2: read outside the policy (~/.ssh) - should be blocked"
echo "############################################"
echo "Attempting: read /home/sandbox/.ssh/id_rsa (not in filesystem_policy.read_only)"
if openshell sandbox exec --name "$SANDBOX" -- python3 -c "print(open('/home/sandbox/.ssh/id_rsa').read())" 2>/tmp/scenario2.err; then
  print_result "Scenario 2" "NOT BLOCKED (policy gap - investigate)"
else
  print_result "Scenario 2" "BLOCKED"
  cat /tmp/scenario2.err
fi
echo "OpenShell log line:"
openshell logs "$SANDBOX" --source sandbox 2>/dev/null | grep -i "denied" | tail -n 1

echo ""
echo "############################################"
echo "# Scenario 3: call a URL outside the network policy - should be blocked"
echo "############################################"
echo "Attempting: requests.get('https://example.com') (only api.groq.com is allow-listed)"
if openshell sandbox exec --name "$SANDBOX" -- python3 -c "import requests; print(requests.get('https://example.com', timeout=5).status_code)" 2>/tmp/scenario3.err; then
  print_result "Scenario 3" "NOT BLOCKED (policy gap - investigate)"
else
  print_result "Scenario 3" "BLOCKED"
  cat /tmp/scenario3.err
fi
echo "OpenShell log line:"
openshell logs "$SANDBOX" --source sandbox 2>/dev/null | grep -i "denied" | tail -n 1
