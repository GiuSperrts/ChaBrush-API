import os
import sys
import subprocess
import requests
import schedule
import time
import logging
from datetime import datetime
import psutil
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(filename='auto_fix.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class AutoFix:
    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.requirements_file = os.path.join(self.project_root, 'requirements.txt')
        self.app_file = os.path.join(self.project_root, 'app.py')
        self.test_file = os.path.join(self.project_root, 'test_app.py')
        self.emergency_email = "sharemyloc.official@gmail.com"
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        self.last_emergency_report = None

    def check_dependencies(self):
        """Check if all dependencies are installed and up to date"""
        try:
            import pkg_resources
            with open(self.requirements_file, 'r') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}

            missing_deps = []
            outdated_deps = []

            for req in requirements:
                if '==' in req:
                    package, version = req.split('==')
                    if package.lower() not in installed_packages:
                        missing_deps.append(req)
                    elif installed_packages[package.lower()] != version:
                        outdated_deps.append((package, installed_packages[package.lower()], version))

            if missing_deps:
                logging.warning(f"Missing dependencies: {missing_deps}")
                self.install_dependencies(missing_deps)

            if outdated_deps:
                logging.info(f"Outdated dependencies: {outdated_deps}")
                # Optionally update them
                # self.update_dependencies(outdated_deps)

            return True
        except Exception as e:
            logging.error(f"Error checking dependencies: {str(e)}")
            return False

    def install_dependencies(self, deps):
        """Install missing dependencies"""
        try:
            for dep in deps:
                logging.info(f"Installing {dep}")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep])
            logging.info("Dependencies installed successfully")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to install dependencies: {str(e)}")

    def check_code_syntax(self):
        """Check Python syntax of main files"""
        files_to_check = [self.app_file, self.test_file]
        syntax_errors = []

        for file_path in files_to_check:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        code = f.read()
                    compile(code, file_path, 'exec')
                except SyntaxError as e:
                    syntax_errors.append(f"{file_path}: {str(e)}")
                    logging.error(f"Syntax error in {file_path}: {str(e)}")
                except Exception as e:
                    logging.error(f"Error checking {file_path}: {str(e)}")

        if syntax_errors:
            logging.warning(f"Syntax errors found: {syntax_errors}")
            return False
        return True

    def run_tests(self):
        """Run the test suite"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pytest', self.test_file, '-v'],
                                  capture_output=True, text=True, cwd=self.project_root)
            if result.returncode != 0:
                logging.warning(f"Tests failed: {result.stdout}")
                return False
            else:
                logging.info("All tests passed")
                return True
        except Exception as e:
            logging.error(f"Error running tests: {str(e)}")
            return False

    def check_app_health(self):
        """Check if the Flask app can start without errors"""
        try:
            # Try to import the app
            sys.path.insert(0, self.project_root)
            import app
            logging.info("App imported successfully")
            return True
        except ImportError as e:
            logging.error(f"Import error: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"App health check failed: {str(e)}")
            return False

    def check_memory_usage(self):
        """Monitor memory usage"""
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        if memory_mb > 500:  # If using more than 500MB
            logging.warning(f"High memory usage: {memory_mb:.2f} MB")
            # Could implement memory cleanup here
        return memory_mb

    def backup_files(self):
        """Create backups of critical files"""
        backup_dir = os.path.join(self.project_root, 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        files_to_backup = [self.app_file, self.requirements_file, self.test_file]

        for file_path in files_to_backup:
            if os.path.exists(file_path):
                backup_name = f"{os.path.basename(file_path)}.{timestamp}.bak"
                backup_path = os.path.join(backup_dir, backup_name)
                with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
                    dst.write(src.read())
                logging.info(f"Backed up {file_path} to {backup_path}")

    def auto_fix(self):
        """Main auto-fix routine"""
        logging.info("Starting auto-fix routine")

        issues_found = []
        critical_issues = []

        # Backup files first
        try:
            self.backup_files()
        except Exception as e:
            issues_found.append(f"Backup failed: {str(e)}")

        # Check and fix dependencies
        try:
            if not self.check_dependencies():
                issues_found.append("Dependency check failed")
        except Exception as e:
            issues_found.append(f"Dependency check error: {str(e)}")
            critical_issues.append(f"Dependency system failure: {str(e)}")

        # Check code syntax
        try:
            if not self.check_code_syntax():
                issues_found.append("Syntax check failed")
                critical_issues.append("Code syntax errors detected")
        except Exception as e:
            issues_found.append(f"Syntax check error: {str(e)}")
            critical_issues.append(f"Syntax validation failure: {str(e)}")

        # Check app health
        try:
            if not self.check_app_health():
                issues_found.append("App health check failed")
                critical_issues.append("Application cannot start properly")
        except Exception as e:
            issues_found.append(f"App health check error: {str(e)}")
            critical_issues.append(f"Application health failure: {str(e)}")

        # Run tests
        try:
            if not self.run_tests():
                issues_found.append("Tests failed")
                critical_issues.append("Test suite failures detected")
        except Exception as e:
            issues_found.append(f"Test execution error: {str(e)}")
            critical_issues.append(f"Testing system failure: {str(e)}")

        # Check memory usage
        try:
            memory_usage = self.check_memory_usage()
            logging.info(f"Memory usage: {memory_usage:.2f} MB")
            if memory_usage > 800:  # Increased threshold for critical
                critical_issues.append(f"Critical memory usage: {memory_usage:.2f} MB")
        except Exception as e:
            issues_found.append(f"Memory check error: {str(e)}")

        # Handle critical issues
        if critical_issues:
            self.consecutive_failures += 1
            logging.warning(f"Critical issues detected: {len(critical_issues)}")
            for issue in critical_issues:
                logging.critical(issue)

            if self.consecutive_failures >= self.max_consecutive_failures:
                logging.critical(f"EMERGENCY: {self.consecutive_failures} consecutive failures detected")
                emergency_description = f"Multiple critical failures ({self.consecutive_failures} consecutive)"
                emergency_details = "\n".join(critical_issues + issues_found)
                self.send_emergency_report(emergency_description, emergency_details)
                self.consecutive_failures = 0  # Reset after emergency report
        else:
            self.consecutive_failures = 0  # Reset on success

        if issues_found:
            logging.warning(f"Issues found: {len(issues_found)}")
            for issue in issues_found:
                logging.warning(issue)

        logging.info("Auto-fix routine completed")

    def start_monitoring(self):
        """Start background monitoring"""
        def monitor():
            while True:
                self.auto_fix()
                time.sleep(3600)  # Check every hour

        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        logging.info("Auto-fix monitoring started")

    def check_for_updates(self):
        """Check for library updates"""
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--outdated'],
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                outdated = result.stdout.strip().split('\n')[2:]  # Skip header
                if outdated:
                    logging.info(f"Outdated packages: {outdated}")
                    # Optionally auto-update
                    # self.update_packages(outdated)
        except Exception as e:
            logging.error(f"Error checking for updates: {str(e)}")

    def send_emergency_report(self, issue_description, error_details):
        """Send emergency email report for critical issues"""
        try:
            # Only send if it's been more than 24 hours since last report
            if self.last_emergency_report:
                time_since_last = datetime.now() - self.last_emergency_report
                if time_since_last.total_seconds() < 86400:  # 24 hours
                    logging.info("Emergency report throttled - too soon since last report")
                    return

            msg = MIMEMultipart()
            msg['From'] = 'auto-fix-system@localhost'
            msg['To'] = self.emergency_email
            msg['Subject'] = f'EMERGENCY: Chat App API Critical Issue - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

            body = f"""
CRITICAL ISSUE REPORT - Chat App API

Issue: {issue_description}

Error Details:
{error_details}

System Information:
- Project Root: {self.project_root}
- Python Version: {sys.version}
- Platform: {sys.platform}
- Current Time: {datetime.now().isoformat()}

Recent Log Entries:
"""
            # Get recent log entries
            try:
                with open('auto_fix.log', 'r') as f:
                    lines = f.readlines()[-20:]  # Last 20 lines
                    body += ''.join(lines)
            except:
                body += "Could not read log file"

            body += "\n\nThis is an automated emergency report. Please investigate immediately."

            msg.attach(MIMEText(body, 'plain'))

            # Note: In a real implementation, you'd need proper SMTP configuration
            # For now, we'll just log the attempt
            logging.critical(f"EMERGENCY REPORT ATTEMPTED: {issue_description}")
            logging.critical(f"Would send email to {self.emergency_email} with details: {error_details}")

            # In production, uncomment and configure:
            # server = smtplib.SMTP('smtp.gmail.com', 587)
            # server.starttls()
            # server.login("your-email@gmail.com", "your-password")
            # server.sendmail(msg['From'], msg['To'], msg.as_string())
            # server.quit()

            self.last_emergency_report = datetime.now()
            logging.info("Emergency report sent (logged)")

        except Exception as e:
            logging.error(f"Failed to send emergency report: {str(e)}")

def main():
    fixer = AutoFix()

    # Run initial check
    fixer.auto_fix()

    # Start monitoring
    fixer.start_monitoring()

    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Auto-fix monitoring stopped")

if __name__ == "__main__":
    main()
