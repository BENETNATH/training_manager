import argparse
import sys
from .utils import console, print_banner
from .config import ConfigManager
from .diagnostics import check_health
from .deploy import DockerDeployer, NativeDeployer
from .wizard import ConfigWizard

def main():
    parser = argparse.ArgumentParser(description="Training Manager CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("setup", help="Run Configuration Wizard")
    subparsers.add_parser("deploy", help="Full Install/Deploy")
    subparsers.add_parser("update", help="Update Code & Dependencies")
    subparsers.add_parser("start", help="Start Services")
    subparsers.add_parser("stop", help="Stop Services")
    subparsers.add_parser("logs", help="View Logs")
    subparsers.add_parser("health", help="Run comprehensive health checks")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        ConfigWizard().run()

    elif args.command == "health":
        print_banner("System Health Check")
        check_health()
        
    elif args.command == "deploy":
        config = ConfigManager.load_env()
        mode = config.get('DEPLOYMENT_MODE', 'docker')
        deployer = DockerDeployer() if mode == 'docker' else NativeDeployer()
        deployer.deploy()
        
    elif args.command == "start":
        config = ConfigManager.load_env()
        mode = config.get('DEPLOYMENT_MODE', 'docker')
        deployer = DockerDeployer() if mode == 'docker' else NativeDeployer()
        deployer.start()
        
    elif args.command == "stop":
        config = ConfigManager.load_env()
        mode = config.get('DEPLOYMENT_MODE', 'docker')
        deployer = DockerDeployer() if mode == 'docker' else NativeDeployer()
        deployer.stop()

    elif args.command == "logs":
        config = ConfigManager.load_env()
        mode = config.get('DEPLOYMENT_MODE', 'docker')
        deployer = DockerDeployer() if mode == 'docker' else NativeDeployer()
        deployer.logs()
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
