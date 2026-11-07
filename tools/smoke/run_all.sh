#!/bin/bash
# Run every headless smoke script; fail on a non-zero exit, a traceback, or a 'tick error' / 'failed:' line in
# THIS run's capri.log files (each run gets its own TMPDIR, so the scripts' mkdtemp homes land there).
# Usage: tools/smoke/run_all.sh [pattern]   e.g. tools/smoke/run_all.sh 'smoke3*'
cd "$(dirname "$0")/../.." || exit 2
PY=${PY:-/usr/bin/python3.12}
RUN=$(mktemp -d); bad=0; n=0
for f in tools/smoke/${1:-smoke*}.py; do
  name=$(basename "$f" .py); n=$((n + 1)); d="$RUN/$name"; mkdir -p "$d"
  TMPDIR="$d" timeout 240 xvfb-run -a -s "-screen 0 1280x1400x24" "$PY" "$f" > "$d/out.txt" 2>&1; rc=$?
  logs=$(grep -l -h -E "tick error|failed:" "$d"/tmp*/.capri/capri.log 2>/dev/null | wc -l)
  tb=$(grep -c Traceback "$d/out.txt")
  if [ $rc -ne 0 ] || [ "$tb" -gt 0 ] || [ "$logs" -gt 0 ]; then
    bad=$((bad + 1)); echo "FAIL $name (exit $rc, tracebacks $tb, bad logs $logs)  -> $d"
    grep -h -A6 -E "tick error|failed:" "$d"/tmp*/.capri/capri.log 2>/dev/null | head -12
    tail -5 "$d/out.txt"
  fi
done
echo "smoke: $((n - bad))/$n passed  (output in $RUN)"
[ $bad -eq 0 ]
