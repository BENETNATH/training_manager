import os
import subprocess
from rich.table import Table
from .utils import console, IS_WINDOWS, run_command
from .config import ConfigManager

class PortManager:
    """Advanced port management with availability checking and conflict resolution."""
    
    @staticmethod
    def check_port_available(port: str, host: str = 'localhost') -> bool:
        """Check if a port is available."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, int(port)))
                return result != 0
        except Exception as e:
            console.print(f"[warning]Error checking port {port}: {e}[/warning]")
            return False
    
    @staticmethod
    def suggest_alternative_ports(port: str, count: int = 3) -> list:
        """Suggest alternative ports near the requested one."""
        suggestions = []
        for offset in [1, 10, 100]:
            candidate = int(port) + offset
            if PortManager.check_port_available(str(candidate)) and candidate < 65535:
                suggestions.append(candidate)
                if len(suggestions) >= count:
                    break
        return suggestions
    
    @staticmethod
    def get_port_info(port: str) -> str:
        """Get information about what's using a port (Linux/Mac only)."""
        if IS_WINDOWS:
            try:
                cmd = f'netstat -ano | findstr :{port}'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return result.stdout.strip() if result.stdout else "Port in use (details unavailable)"
            except:
                return "Unable to determine"
        else:
            try:
                cmd = f"lsof -i :{port} -sTCP:LISTEN || ss -ltnp | grep :{port}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return result.stdout.strip() if result.stdout else "Port in use (details unavailable)"
            except:
                return "Unable to determine"

class DatabaseManager:
    """Database connectivity testing."""
    
    @staticmethod
    def test_connection(db_config: dict) -> tuple:
        """Test database connection. Returns (success, message)."""
        db_type = db_config.get('DB_TYPE', 'sqlite')
        
        if db_type == 'sqlite':
            db_path = db_config.get('DATABASE_URL', 'instance/app.db')
            if db_path.startswith('sqlite:///'):
                db_path = db_path.replace('sqlite:///', '')
            
            db_dir = os.path.dirname(db_path) if '/' in db_path else 'instance'
            if not os.path.exists(db_dir):
                return False, f"Directory '{db_dir}' does not exist"
            return True, f"SQLite database path: {db_path}"
        
        elif db_type in ['mysql', 'mariadb']:
            try:
                import pymysql
                conn = pymysql.connect(
                    host=db_config.get('DB_HOST', 'localhost'),
                    port=int(db_config.get('DB_PORT', 3306)),
                    user=db_config.get('DB_USER'),
                    password=db_config.get('DB_PASSWORD'),
                    database=db_config.get('DB_NAME'),
                    connect_timeout=5
                )
                conn.close()
                return True, f"Successfully connected to {db_config.get('DB_HOST')}:{db_config.get('DB_PORT')}"
            except ImportError:
                return False, "pymysql not installed"
            except Exception as e:
                return False, f"Connection failed: {str(e)}"
        
        return False, f"Unknown database type: {db_type}"

    @staticmethod
    def create_database_if_not_exists(db_config):
        """Create database if it doesn't exist (MySQL only)."""
        if db_config.get('DB_TYPE') not in ['mysql', 'mariadb']:
            return True, "SQLite - database will be created automatically"
        
        try:
            import pymysql
            conn = pymysql.connect(
                host=db_config.get('DB_HOST'),
                port=int(db_config.get('DB_PORT', 3306)),
                user=db_config.get('DB_USER'),
                password=db_config.get('DB_PASSWORD'),
                connect_timeout=5
            )
            cursor = conn.cursor()
            db_name = db_config.get('DB_NAME')
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            cursor.close()
            conn.close()
            return True, f"Database '{db_name}' is ready"
        except Exception as e:
            return False, f"Failed to create database: {str(e)}"

def check_health():
    """Run system health check."""
    table = Table(title="System Health Check")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Details")
    
    config = ConfigManager.load_env()
    
    # 1. Config
    if os.path.exists(".env"):
        table.add_row("Configuration", "[green]OK[/green]", f"{len(config)} parameters")
    else:
        table.add_row("Configuration", "[red]Missing[/red]", "Run setup")
        
    # 2. Database
    success, msg = DatabaseManager.test_connection(config)
    status = "[green]Connected[/green]" if success else "[red]Failed[/red]"
    table.add_row("Database", status, msg)
    
    console.print(table)
