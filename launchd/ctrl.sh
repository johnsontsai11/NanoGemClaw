#!/bin/bash
# NanoGemClaw Launchd Management Script

PLIST_NAME="com.nanoclaw.plist"
PLIST_SRC_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/${PLIST_NAME}"
PLIST_DEST_PATH="${HOME}/Library/LaunchAgents/${PLIST_NAME}"
LOGS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../logs" && pwd)"

# Helper for timestamped script output (local time)
ts_echo() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $@"
}

show_help() {
    echo "Usage: $0 {start|stop|restart|status|logs|errors|all|install}"
    echo ""
    echo "Commands:"
    echo "  start    - Load and start the launchd service"
    echo "  stop     - Stop and unload the launchd service"
    echo "  restart  - Restart the launchd service"
    echo "  status   - Check if the service is currently running"
    echo "  logs     - Tail the standard output log"
    echo "  errors   - Tail the error log"
    echo "  verbose  - Tail both output and error logs"
    echo "  install  - Copy the plist from this project directly to LaunchAgents"
}

case "$1" in
    help)
        show_help
        exit 0
        ;;
    start)
        ts_echo "Starting launchd service..."
        launchctl load "$PLIST_DEST_PATH"
        ts_echo "Started."
        ;;
    stop)
        ts_echo "Stopping launchd service..."
        launchctl unload "$PLIST_DEST_PATH" &>/dev/null
        ts_echo "Stopped."
        ;;
    restart)
        $0 stop
        $0 start
        ;;
    status)
        if launchctl list | grep -q "com.nanogemclaw"; then
            ts_echo "Status: Running"
            launchctl list | grep "com.nanogemclaw"
        else
            ts_echo "Status: Not running"
        fi
        ;;
    logs)
        tail -f "$LOGS_DIR/nanoclaw.log"
        ;;
    errors)
        tail -f "$LOGS_DIR/nanoclaw.error.log"
        ;;
    verbose)
        tail -f "$LOGS_DIR/nanoclaw.error.log" "$LOGS_DIR/nanoclaw.log"
        ;;
    install)
        echo "Installing $PLIST_NAME to $PLIST_DEST_PATH"
        mkdir -p "${HOME}/Library/LaunchAgents"
        cp "$PLIST_SRC_PATH" "$PLIST_DEST_PATH"
        echo "Done! Run '$0 start' to load the new config."
        ;;
    *)
        show_help
        exit 1
        ;;
esac
