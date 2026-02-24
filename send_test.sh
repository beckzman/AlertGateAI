#!/bin/bash
# Testmeldungen an den AlertGateAI Syslog-Receiver senden (macOS/Linux)
# Voraussetzung: nc (netcat) installiert
# Verwendung: ./send_test.sh [critical|high|info|all]

HOST="127.0.0.1"
PORT=5140

send_syslog() {
    local msg="$1"
    echo -n "$msg" | nc -u -w1 "$HOST" "$PORT"
    echo "→ Gesendet: $msg"
}

case "${1:-all}" in
  critical)
    send_syslog "CRITICAL: Out of memory - OOM Killer terminated process db_server on host prod-db-01"
    send_syslog "CRITICAL: Disk usage at 99% on /dev/sda1 - filesystem full on storage-node-03"
    ;;
  high)
    send_syslog "ERROR: Connection timeout to upstream api-gateway after 30s retries exhausted"
    send_syslog "ERROR: Service crash detected - nginx worker process failed on web-01"
    ;;
  info)
    send_syslog "WARNING: CPU load above threshold (85%) on app-server-02"
    send_syslog "INFO: Scheduled backup completed with warnings on backup-host-01"
    ;;
  all)
    echo "--- Sende CRITICAL Meldungen ---"
    send_syslog "CRITICAL: Out of memory - OOM Killer terminated process db_server on host prod-db-01"
    sleep 0.5
    send_syslog "CRITICAL: Disk usage at 99% on /dev/sda1 - filesystem full on storage-node-03"
    sleep 0.5
    echo "--- Sende HIGH Meldungen ---"
    send_syslog "ERROR: Connection timeout to upstream api-gateway after 30s retries exhausted"
    sleep 0.5
    send_syslog "ERROR: Service crash detected - nginx worker process failed on web-01"
    sleep 0.5
    echo "--- Sende INFO Meldungen ---"
    send_syslog "WARNING: CPU load above threshold (85%) on app-server-02"
    sleep 0.5
    send_syslog "INFO: Scheduled backup completed with warnings on backup-host-01"
    ;;
  *)
    echo "Verwendung: $0 [critical|high|info|all]"
    exit 1
    ;;
esac

echo ""
echo "Dashboard: http://localhost"
echo "Mailpit:   http://localhost:8025"
