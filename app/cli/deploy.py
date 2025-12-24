import os
import shutil
import time
import subprocess
from .utils import console, run_command, get_architecture, confirm_action, IS_WINDOWS
from .config import ConfigManager

class DockerDeployer:
    """Docker-based deployment manager."""
    
    def __init__(self):
        self.compose_file = "docker-compose.yml"
        if get_architecture() == 'armv7l':
             self.compose_file = "docker-compose-rpi2.yml"
             console.print("[info]Detected Raspberry Pi (ARMv7). Using optimized configurations.[/info]")

    def deploy(self):
        console.rule("[bold cyan]Docker Deployment[/bold cyan]")
        
        # Ensure directories
        for d in ["logs", "instance", "migrations"]:
            if not os.path.exists(d):
                os.makedirs(d)
                console.print(f"[green]Created directory: {d}[/green]")
        
        # Check network
        console.print("[info]Checking Docker network...[/info]")
        result = run_command("docker network ls --format '{{.Name}}'", capture_output=True)
        if "lab_ecosystem" not in result:
            console.print("[info]Creating lab_ecosystem network...[/info]")
            run_command("docker network create lab_ecosystem")

        run_command(f"docker compose -f {self.compose_file} build")
        run_command(f"docker compose -f {self.compose_file} up -d")
        
        console.print("[bold green]Application Deployed (Docker)[/bold green]")
        config = ConfigManager.load_env()
        port = config.get('APP_PORT', '5001')
        console.print(f"[info]Application should be available at http://localhost:{port}[/info]")

    def update(self):
        console.print("[info]Pulling latest code...[/info]")
        run_command("git pull", check=False)
        self.deploy()

    def start(self): run_command(f"docker compose -f {self.compose_file} up -d")
    def stop(self): run_command(f"docker compose -f {self.compose_file} stop")
    def logs(self): run_command(f"docker compose -f {self.compose_file} logs -f --tail=100", capture_output=False)


class NativeDeployer:
    """Manual deployment manager."""
    
    def deploy(self):
        console.rule("[bold cyan]Native Deployment[/bold cyan]")
        
        # venv
        venv_dir = ".venv" if os.path.exists(".venv") else "venv"
        if not os.path.exists(venv_dir):
            console.print("[info]Creating virtual environment...[/info]")
            import venv
            venv.create(venv_dir, with_pip=True)
            
        if IS_WINDOWS:
            python_exec = os.path.join(venv_dir, "Scripts", "python.exe")
            pip_exec = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:
            python_exec = os.path.join(venv_dir, "bin", "python")
            pip_exec = os.path.join(venv_dir, "bin", "pip")
            
        console.print("[info]Installing dependencies...[/info]")
        run_command(f'"{pip_exec}" install -r requirements.txt')
        
        # Directories
        for d in ["logs", "instance", "migrations"]:
            if not os.path.exists(d):
                os.makedirs(d)

        # Migrations
        console.print("[info]Initializing database...[/info]")
        migrations_env = os.path.join("migrations", "env.py")
        if os.path.exists(migrations_env):
             run_command(f'"{python_exec}" -m flask db upgrade', check=False)
        else:
             if os.path.exists("migrations"): shutil.rmtree("migrations")
             run_command(f'"{python_exec}" -m flask db init', check=False)
             run_command(f'"{python_exec}" -m flask db migrate -m "Initial"', check=False)
             run_command(f'"{python_exec}" -m flask db upgrade', check=False)
             
        console.print("[bold green]Native deployment complete![/bold green]")

    def start(self):
        config = ConfigManager.load_env()
        port = config.get('APP_PORT', '5001')
        
        venv_dir = ".venv" if os.path.exists(".venv") else "venv"
        if IS_WINDOWS:
            python_exec = os.path.join(venv_dir, "Scripts", "python.exe")
            log_file = os.path.join("logs", "app.log")
            cmd = f'start /B "" "{python_exec}" -c "from waitress import serve; from app import create_app; serve(create_app(), host=\'0.0.0.0\', port={port})" > "{log_file}" 2>&1'
            subprocess.run(cmd, shell=True)
            console.print(f"[success]Started on http://localhost:{port} (Waitress)[/success]")
        else:
            python_exec = os.path.join(venv_dir, "bin", "python")
            pid_file = os.path.join("logs", "gunicorn.pid")
            log_file = os.path.join("logs", "gunicorn.log")
            cmd = f'"{python_exec}" -m gunicorn -w 4 -b 0.0.0.0:{port} --pid "{pid_file}" --access-logfile "{log_file}" --daemon "app:create_app()"'
            run_command(cmd, check=False)
            console.print(f"[success]Started on http://localhost:{port} (Gunicorn)[/success]")

    def stop(self):
        pid_file = os.path.join("logs", "gunicorn.pid")
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            if IS_WINDOWS:
                subprocess.run(f'taskkill /PID {pid} /F', shell=True)
            else:
                os.kill(pid, 15)
            console.print("[info]Stopped application[/info]")
        else:
            console.print("[warning]PID file not found[/warning]")
