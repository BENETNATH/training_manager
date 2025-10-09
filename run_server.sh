#!/bin/bash

# Linux startup script for Quote Creator Flask app
# This script handles virtual environment activation, dependency checks, and background execution

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="Quote Creator"
APP_PORT="${PORT:-5000}"
APP_HOST="${HOST:-0.0.0.0}"
VENV_DIR=".venv"

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python() {
    if ! command_exists python3; then
        print_error "Python3 is not installed"
        exit 1
    fi

    local python_version=$(python3 --version 2>&1 | awk '{print $2}')
    print_info "Using Python $python_version"
}

# Function to activate virtual environment
activate_venv() {
    if [ -d "$VENV_DIR" ]; then
        print_info "Activating virtual environment..."
        source "$VENV_DIR/bin/activate"

        # Check if pip is available in the virtual environment
        if [ ! -f "$VIRTUAL_ENV/bin/pip" ]; then
            print_warning "Pip not found in virtual environment. Installing pip..."
            if command_exists python3; then
                # Try to install pip using get-pip.py
                curl -s https://bootstrap.pypa.io/get-pip.py | python3 || {

                    # Fall back to using ensurepip module
                    python3 -m ensurepip --upgrade --default-pip 2>/dev/null || {

                        # Final fallback - try system pip to install in venv
                        print_warning "Trying system pip installation..."
                        if command_exists pip3; then
                            pip3 install --user pip || pip3 install pip
                        fi
                    }
                }
            fi
            print_info "Pip installation attempt completed."
        fi
    else
        print_warning "No virtual environment found at $VENV_DIR"
        print_warning "Installing dependencies globally with pip3 (not recommended for production)"
        if ! command_exists pip3; then
            print_error "pip3 is not available. Please install pip3 or create a virtual environment."
            exit 1
        fi
    fi
}

# Function to install dependencies if requirements.txt exists
install_dependencies() {
    if [ -f "requirements.txt" ]; then
        print_info "Installing dependencies from requirements.txt..."

        # Simplified approach - always try system pip if venv pip fails
        local install_success=false

        if [ -n "$VIRTUAL_ENV" ]; then
            print_info "Trying to use virtual environment pip..."

            # First, try to install pip in the venv if missing
            if [ ! -f "$VIRTUAL_ENV/bin/pip" ]; then
                print_warning "Installing pip in virtual environment..."

                # Try the simplest method first
                if command_exists python3; then
                    print_info "Installing pip using ensurepip..."
                    "$VIRTUAL_ENV/bin/python3" -m ensurepip --upgrade --quiet 2>/dev/null || {
                        print_info "Installing pip using get-pip.py..."
                        curl -s https://bootstrap.pypa.io/get-pip.py | "$VIRTUAL_ENV/bin/python3" 2>/dev/null || {
                            print_warning "Pip installation failed, will use system pip instead"
                        }
                    }
                fi
                # Re-activate to pick up newly installed pip
                source "$VIRTUAL_ENV/bin/activate" 2>/dev/null || true
            fi

            # Now try to use pip from venv
            if [ -f "$VIRTUAL_ENV/bin/pip" ] || [ -f "$VIRTUAL_ENV/bin/pip3" ]; then
                print_info "Using virtual environment pip"
                local pip_cmd="$VIRTUAL_ENV/bin/pip"
                if [ ! -f "$pip_cmd" ] && [ -f "$VIRTUAL_ENV/bin/pip3" ]; then
                    pip_cmd="$VIRTUAL_ENV/bin/pip3"
                fi

                # Try to install requirements
                "$pip_cmd" install --quiet -r requirements.txt 2>/dev/null && install_success=true
            fi
        fi

        # If venv pip failed or no venv, try system pip
        if [ "$install_success" = false ]; then
            print_warning "Falling back to system pip..."
            if command_exists pip3; then
                pip3 install --quiet -r requirements.txt 2>/dev/null && install_success=true
            elif command_exists pip; then
                pip install --quiet -r requirements.txt 2>/dev/null && install_success=true
            fi
        fi

        if [ "$install_success" = true ]; then
            print_success "Dependencies installed successfully"
        else
            print_error "Failed to install dependencies with any available pip method"
            print_error "Please install pip manually and run: pip install -r requirements.txt"
            exit 1
        fi
    else
        print_warning "requirements.txt not found"
    fi
}

# Function to check if Flask app can be imported
check_app() {
    print_info "Checking Flask application..."
    if [ ! -f "flask_app.py" ]; then
        print_error "flask_app.py not found in current directory"
        print_info "Please run this script from the Flask application directory"
        exit 1
    fi

    # Use the active Python (could be venv or system Python)
    local python_cmd="python3"
    if [ -n "$VIRTUAL_ENV" ]; then
        python_cmd="$VIRTUAL_ENV/bin/python3"
    fi

    # Get current Python path for debugging
    local python_path="$($python_cmd -c "import sys; print(sys.executable)" 2>/dev/null || echo "unknown")"
    print_info "Using Python: $python_path"

    # Test if app can be imported (basic syntax check)
    if $python_cmd -c "import app" 2>/dev/null; then
        print_success "Flask application syntax is valid"
    else
        local import_error="$($python_cmd -c "import app" 2>&1 || true)"
        print_error "Flask application has syntax errors or missing dependencies"
        print_info "Import error details: $import_error"

        # Provide more specific error checking
        if echo "$import_error" | grep -q "No module named"; then
            print_info "Hint: Missing dependencies. Run 'pip install -r requirements.txt'"
        elif echo "$import_error" | grep -q "SyntaxError"; then
            print_info "Hint: Check app.py for syntax errors"
        fi

        # Don't exit if we're in skip-venv mode, just warn
        if [ "$skip_venv" = true ]; then
            print_warning "Continuing with skip-venv option despite import issues..."
            return 0
        fi
        exit 1
    fi
}

# Function to create logs directory
setup_logs() {
    if [ ! -d "logs" ]; then
        print_info "Creating logs directory..."
        mkdir -p logs
        chmod 755 logs
    fi
}

# Function to start the application
start_app() {
    print_info "Starting $APP_NAME on $APP_HOST:$APP_PORT"

    # Export environment variables
    export PORT="$APP_PORT"
    export HOST="$APP_HOST"

    print_info "Application will be available at: http://localhost:$APP_PORT"
    print_info "Logs will be written to: logs/quote_manager.log"

    # Use the active Python (could be venv or system Python)
    local python_cmd="python3"
    if [ -n "$VIRTUAL_ENV" ]; then
        python_cmd="$VIRTUAL_ENV/bin/python3"
    fi

    # Start the application in foreground (for production, consider using process managers like systemd)
    print_info "Starting Flask application with waitress..."
    print_info "Using Python executable: $($python_cmd -c "import sys; print(sys.executable)")"
    exec $python_cmd flask_app.py
}

# Function to start in background
start_app_background() {
    print_info "Starting $APP_NAME in background mode"

    # Check if nohup is available
    if ! command_exists nohup; then
        print_warning "nohup not found. Starting in foreground..."
        start_app
        return
    fi

    export PORT="$APP_PORT"
    export HOST="$APP_HOST"

    # Use the active Python (could be venv or system Python)
    local python_cmd="python3"
    if [ -n "$VIRTUAL_ENV" ]; then
        python_cmd="$VIRTUAL_ENV/bin/python3"
    fi

    # Start in background with nohup
    nohup $python_cmd flask_app.py > app.out 2>&1 &

    local app_pid=$!
    echo $app_pid > app.pid

    print_success "Application started in background with PID: $app_pid"
    print_info "PID saved to app.pid file"
    print_info "Output redirected to app.out"
    print_info "Use 'kill $app_pid' or './stop_server.sh' to stop the application"
    print_info "Using Python executable: $($python_cmd -c "import sys; print(sys.executable)")"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -f, --foreground    Start application in foreground
    -p, --port PORT     Set port (default: 5000)
    -h, --host HOST     Set host (default: 0.0.0.0)
    --skip-venv         Skip virtual environment activation
    --help              Show this help message

Environment variables:
    PORT                Override default port
    HOST                Override default host

Examples:
    ./$0                    # Start in background (default)
    ./$0 -f                 # Start in foreground
    ./$0 -p 8000            # Start on port 8000 in background
    PORT=8080 ./$0          # Start on port 8080 in background using environment variable

EOF
}

# Main script logic
main() {
    local background=true
    local skip_venv=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--foreground)
                background=false
                shift
                ;;
            -p|--port)
                APP_PORT="$2"
                shift 2
                ;;
            -h|--host)
                APP_HOST="$2"
                shift 2
                ;;
            --skip-venv)
                skip_venv=true
                shift
                ;;
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

    print_info "=== $APP_NAME Startup Script ==="

    # Run checks
    check_python

    if [ "$skip_venv" = false ]; then
        activate_venv
    fi

    # Install dependencies FIRST, then check app
    install_dependencies
    check_app
    setup_logs

    # Start application
    if [ "$background" = true ]; then
        start_app_background
    else
        start_app
    fi

    print_success "=== Setup complete ==="
}

# Run main function with all arguments
main "$@"
