#!/usr/bin/env python3
"""
Training Manager Management CLI
Handles setup, deployment, and maintenance operations.
"""

import argparse
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

def run_command(cmd, check=True, capture_output=False):
    """Run a shell command with proper error handling."""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=capture_output, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {cmd}")
        print(f"Error: {e}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        sys.exit(1)

def check_docker():
    """Check if Docker is running."""
    try:
        run_command("docker info", capture_output=True)
        return True
    except:
        print("Docker is not running or not accessible. Please start Docker first.")
        return False

def setup_env_file():
    """Interactive setup wizard for .env file."""
    env_sample = Path("env-sample")
    env_file = Path(".env")

    if env_file.exists():
        response = input(".env file already exists. Overwrite? (y/N): ").strip().lower()
        if response != 'y':
            print("Setup cancelled.")
            return

    if not env_sample.exists():
        print("env-sample file not found. Cannot proceed with setup.")
        return

    # Copy env-sample to .env
    shutil.copy(env_sample, env_file)
    print("Created .env file from env-sample template.")

    # Interactive configuration
    print("\n=== Training Manager Setup Wizard ===\n")

    # Deployment mode
    deployment_mode = input("Deployment mode (docker/native) [docker]: ").strip() or "docker"
    update_env_var(env_file, "DEPLOYMENT_MODE", deployment_mode)

    # Generate secret key
    secret_key = secrets.token_hex(32)
    update_env_var(env_file, "SECRET_KEY", secret_key)
    print("Generated secure SECRET_KEY.")

    # Admin credentials
    admin_email = input("Admin email [admin@example.com]: ").strip() or "admin@example.com"
    admin_password = input("Admin password (leave empty to generate): ").strip()
    if not admin_password:
        admin_password = secrets.token_hex(16)
        print(f"Generated admin password: {admin_password}")
    update_env_var(env_file, "ADMIN_EMAIL", admin_email)
    update_env_var(env_file, "ADMIN_PASSWORD", admin_password)

    # Service API Key
    service_api_key = secrets.token_hex(32)
    update_env_var(env_file, "SERVICE_API_KEY", service_api_key)
    print("Generated SERVICE_API_KEY for inter-app communication.")

    # SSO Secret Key
    sso_secret_key = secrets.token_hex(32)
    update_env_var(env_file, "SSO_SECRET_KEY", sso_secret_key)
    print("Generated SSO_SECRET_KEY for seamless login.")

    # Database configuration
    db_type = input("Database type (sqlite/mysql) [sqlite]: ").strip() or "sqlite"
    update_env_var(env_file, "DB_TYPE", db_type)

    if db_type == "mysql":
        db_host = input("Database host [db]: ").strip() or "db"
        db_port = input("Database port [3306]: ").strip() or "3306"
        db_name = input("Database name [training_manager]: ").strip() or "training_manager"
        db_user = input("Database user [appuser]: ").strip() or "appuser"
        db_password = input("Database password: ").strip()
        db_root_password = input("Database root password: ").strip()

        update_env_var(env_file, "DB_HOST", db_host)
        update_env_var(env_file, "DB_PORT", db_port)
        update_env_var(env_file, "DB_NAME", db_name)
        update_env_var(env_file, "DB_USER", db_user)
        update_env_var(env_file, "DB_PASSWORD", db_password)
        update_env_var(env_file, "DB_ROOT_PASSWORD", db_root_password)

    # Email configuration
    configure_email = input("Configure email settings? (y/N): ").strip().lower()
    if configure_email == 'y':
        mail_server = input("Mail server [smtp.example.com]: ").strip() or "smtp.example.com"
        mail_port = input("Mail port [587]: ").strip() or "587"
        mail_use_tls = input("Use TLS? (True/False) [True]: ").strip() or "True"
        mail_username = input("Mail username: ").strip()
        mail_password = input("Mail password: ").strip()

        update_env_var(env_file, "MAIL_SERVER", mail_server)
        update_env_var(env_file, "MAIL_PORT", mail_port)
        update_env_var(env_file, "MAIL_USE_TLS", mail_use_tls)
        update_env_var(env_file, "MAIL_USERNAME", mail_username)
        update_env_var(env_file, "MAIL_PASSWORD", mail_password)

    print("\nSetup complete! Review and edit .env file as needed.")

def update_env_var(env_file, key, value):
    """Update an environment variable in the .env file."""
    content = env_file.read_text()
    lines = content.split('\n')
    updated = False

    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            updated = True
            break

    if not updated:
        # Add new line if key not found
        lines.append(f"{key}={value}")

    env_file.write_text('\n'.join(lines))

def deploy():
    """Deploy the application using Docker Compose."""
    if not check_docker():
        return

    print("Checking Docker network...")
    result = run_command("docker network ls --format 'table {{.Name}}'", capture_output=True)
    if "lab_ecosystem" not in result.stdout:
        print("Creating lab_ecosystem network...")
        run_command("docker network create lab_ecosystem")

    print("Building and starting services...")
    run_command("docker compose build")
    run_command("docker compose up -d")

    print("Deployment complete!")
    print("Application should be available at http://localhost:5001")

def start():
    """Start the application."""
    if not check_docker():
        return
    run_command("docker compose up -d")

def stop():
    """Stop the application."""
    if not check_docker():
        return
    run_command("docker compose stop")

def restart():
    """Restart the application."""
    if not check_docker():
        return
    stop()
    start()

def logs():
    """Show application logs."""
    if not check_docker():
        return
    run_command("docker compose logs -f")

def create_admin():
    """Create admin user."""
    if not check_docker():
        return
    run_command("docker compose exec web flask create-admin")

def main():
    parser = argparse.ArgumentParser(description="Training Manager Management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Setup command
    subparsers.add_parser('setup', help='Initial setup wizard')

    # Deploy command
    subparsers.add_parser('deploy', help='Deploy application with Docker')

    # Lifecycle commands
    subparsers.add_parser('start', help='Start the application')
    subparsers.add_parser('stop', help='Stop the application')
    subparsers.add_parser('restart', help='Restart the application')
    subparsers.add_parser('logs', help='Show application logs')

    # Admin command
    subparsers.add_parser('create-admin', help='Create admin user')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Execute command
    if args.command == 'setup':
        setup_env_file()
    elif args.command == 'deploy':
        deploy()
    elif args.command == 'start':
        start()
    elif args.command == 'stop':
        stop()
    elif args.command == 'restart':
        restart()
    elif args.command == 'logs':
        logs()
    elif args.command == 'create-admin':
        create_admin()

if __name__ == '__main__':
    main()
