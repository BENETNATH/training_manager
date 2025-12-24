import os
import shutil
from rich.prompt import Prompt, Confirm
from .utils import console, confirm_action, get_architecture
from .config import ConfigManager, generate_secret, ENV_FILE
from .diagnostics import DatabaseManager, PortManager

class ConfigWizard:
    def __init__(self):
        self.config = {}

    def run(self):
        console.rule("[bold magenta]Training Manager Setup[/bold magenta]")
        if os.path.exists(ENV_FILE):
             if not Confirm.ask(f"[warning].env exists. Overwrite?[/warning]"): return

        self._ask_deployment_mode()
        self._ask_env_basic()
        self._ask_security()
        self._ask_database()
        self._ask_mail()
        self._ask_ecosystem()
        self._save()

    def _ask_deployment_mode(self):
        console.print("\n[cyan]--- Deployment Mode ---[/cyan]")
        console.print("1. Docker (Recommended)")
        console.print("2. Native")
        choice = Prompt.ask("Choice", choices=["1", "2"], default="1")
        self.config['DEPLOYMENT_MODE'] = 'docker' if choice == '1' else 'native'

    def _ask_env_basic(self):
        self.config['APP_PORT'] = Prompt.ask("Application Port", default="5001")

    def _ask_security(self):
        self.config['SECRET_KEY'] = generate_secret(50)
        
        console.print("\n[cyan]--- Admin User ---[/cyan]")
        self.config['ADMIN_EMAIL'] = Prompt.ask("Admin Email", default="admin@example.com")
        self.config['ADMIN_PASSWORD'] = Prompt.ask("Admin Password", password=True, default=generate_secret(16))
        
        self.config['SERVICE_API_KEY'] = generate_secret(32)
        console.print(f"[green]Generated SERVICE_API_KEY for ecosystem[/green]")
        
        self.config['SSO_SECRET_KEY'] = generate_secret(32)
        console.print(f"[green]Generated SSO_SECRET_KEY for login[/green]")

    def _ask_database(self):
        console.print("\n[cyan]--- Database ---[/cyan]")
        if self.config['DEPLOYMENT_MODE'] == 'docker':
            console.print("1. Internal Container (MariaDB)")
            console.print("2. External (e.g. Host/Cloud)")
            c = Prompt.ask("Choice", choices=["1", "2"], default="1")
            
            if c == '1':
                self.config['DB_TYPE'] = 'mysql'
                self.config['DB_HOST'] = 'db'
                self.config['DB_NAME'] = 'training_manager'
                self.config['DB_USER'] = 'appuser'
                self.config['DB_PASSWORD'] = generate_secret(16)
                self.config['DB_ROOT_PASSWORD'] = generate_secret(16)
                self.config['DB_PORT'] = '3306'
            else:
                self._ask_external_db()
        else:
            console.print("1. SQLite")
            console.print("2. External MySQL/MariaDB")
            c = Prompt.ask("Choice", choices=["1", "2"], default="1")
            if c == '1':
                self.config['DB_TYPE'] = 'sqlite'
            else:
                self._ask_external_db()

    def _ask_external_db(self):
        default_host = "host.docker.internal" if self.config.get('DEPLOYMENT_MODE') == 'docker' else "localhost"
        
        self.config['DB_TYPE'] = 'mysql'
        self.config['DB_HOST'] = Prompt.ask("DB Host", default=default_host)
        self.config['DB_PORT'] = Prompt.ask("DB Port", default="3306")
        self.config['DB_NAME'] = Prompt.ask("DB Name", default="training_manager")
        self.config['DB_USER'] = Prompt.ask("DB User")
        self.config['DB_PASSWORD'] = Prompt.ask("DB Password", password=True)
        
        # Test connection
        if self.config.get('DEPLOYMENT_MODE') == 'native' or self.config['DB_HOST'] in ['localhost', '127.0.0.1']:
            if Confirm.ask("Test connection now?"):
                success, msg = DatabaseManager.test_connection(self.config)
                if success:
                    console.print(f"[green]{msg}[/green]")
                    if Confirm.ask("Create database if missing?"):
                         DatabaseManager.create_database_if_not_exists(self.config)
                else:
                    console.print(f"[red]Connection failed: {msg}[/red]")
                    if not Confirm.ask("Continue anyway?"):
                        self._ask_database()
                        return

    def _ask_mail(self):
        console.print("\n[cyan]--- Email ---[/cyan]")
        if Confirm.ask("Configure Email?"):
            self.config['MAIL_SERVER'] = Prompt.ask("SMTP Server")
            self.config['MAIL_PORT'] = Prompt.ask("SMTP Port", default="587")
            self.config['MAIL_USE_TLS'] = 'True'
            self.config['MAIL_USERNAME'] = Prompt.ask("Username")
            self.config['MAIL_PASSWORD'] = Prompt.ask("Password", password=True)

    def _ask_ecosystem(self):
        console.print("\n[cyan]--- Precliniverse Integration ---[/cyan]")
        if Confirm.ask("Configure Precliniverse integration?"):
            default = "http://precliniverse:8000" if self.config.get('DEPLOYMENT_MODE') == 'docker' else "http://localhost:8000"
            self.config['PC_API_URL'] = Prompt.ask("Precliniverse API URL", default=default)
            self.config['PC_API_KEY'] = Prompt.ask("Precliniverse SERVICE_API_KEY")
            self.config['PC_ENABLED'] = 'True'
        else:
            self.config['PC_ENABLED'] = 'False'

    def _save(self):
        app_port = self.config.get('APP_PORT', '5001')
        if not PortManager.check_port_available(app_port):
             console.print(f"[warning]Port {app_port} in use[/warning]")
        
        with open(ENV_FILE, 'w') as f:
            for k, v in self.config.items():
                f.write(f"{k}={v}\n")
        console.print(f"[success]Configuration saved[/success]")
