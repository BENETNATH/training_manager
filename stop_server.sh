#!/bin/bash

# Script to stop the Quote Creator Flask application
# This script can stop applications started by run_server.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PID_FILE="app.pid"
OUTPUT_FILE="app.out"
APP_NAME="Quote Creator"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if process is running
is_process_running() {
    local pid=$1
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to get process name
get_process_name() {
    local pid=$1
    ps -p "$pid" -o comm= 2>/dev/null || echo "unknown"
}

# Function to kill process gracefully
stop_app_gracefully() {
    local pid=$1
    local process_name=$(get_process_name "$pid")

    print_info "Stopping process $pid ($process_name) gracefully..."

    # Send SIGTERM first
    kill -TERM "$pid" 2>/dev/null || true

    # Wait up to 10 seconds for graceful shutdown
    local count=0
    while [ $count -lt 10 ] && is_process_running "$pid"; do
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    echo ""

    if is_process_running "$pid"; then
        print_warning "Process did not respond to SIGTERM, sending SIGKILL..."
        kill -KILL "$pid" 2>/dev/null || true
        sleep 1

        if is_process_running "$pid"; then
            print_error "Failed to kill process $pid"
            return 1
        else
            print_warning "Process $pid was forcefully killed"
        fi
    else
        print_success "Process $pid stopped gracefully"
    fi

    return 0
}

# Function to find Python processes related to our app
find_app_processes() {
    # Look for Python processes running flask_app.py
    ps aux | grep "python.*flask_app.py" | grep -v grep | awk '{print $2}' || true
}

# Main script logic
main() {
    print_info "=== $APP_NAME Stop Script ==="

    local stopped_count=0

    # Method 1: Check PID file
    if [ -f "$PID_FILE" ]; then
        local saved_pid=$(cat "$PID_FILE")
        print_info "Found PID file with PID: $saved_pid"

        if is_process_running "$saved_pid"; then
            if stop_app_gracefully "$saved_pid"; then
                stopped_count=$((stopped_count + 1))
            fi
        else
            print_warning "PID $saved_pid from file is not running"
        fi

        # Remove PID file
        rm -f "$PID_FILE"
        print_info "Removed PID file"
    else
        print_info "No PID file found"
    fi

    # Method 2: Search for running app processes
    local running_pids=$(find_app_processes)

    if [ -n "$running_pids" ]; then
        print_info "Found running Python flask_app.py processes: $running_pids"

        for pid in $running_pids; do
            # Skip the current script's own process if it matches
            if [ "$pid" != "$$" ]; then
                if stop_app_gracefully "$pid"; then
                    stopped_count=$((stopped_count + 1))
                fi
            fi
        done
    else
        print_info "No running flask_app.py processes found"
    fi

    # Clean up output file if empty
    if [ -f "$OUTPUT_FILE" ] && [ ! -s "$OUTPUT_FILE" ]; then
        rm -f "$OUTPUT_FILE"
        print_info "Removed empty output file"
    fi

    if [ $stopped_count -gt 0 ]; then
        print_success "Successfully stopped $stopped_count process(es)"
    else
        print_warning "No processes were stopped"
        print_info "Either the application is not running, or it was started without run_server.sh"
    fi

    print_info "=== Application stop attempt complete ==="
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Stop the Quote Creator Flask application.

This script will:
1. Check for a saved PID file (app.pid)
2. Look for running Python processes executing flask_app.py
3. Attempt to stop processes gracefully (SIGTERM)
4. Force kill if necessary (SIGKILL)

Options:
    --help          Show this help message

Files used:
    app.pid         Contains the process ID saved by run_server.sh
    app.out         Contains application output (may be cleaned up)

Examples:
    ./$0            # Stop the application
    ./$0 --help     # Show this help

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Run main function
main
