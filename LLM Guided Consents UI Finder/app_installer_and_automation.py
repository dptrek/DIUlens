import os
import subprocess
import argparse
import sys
import re
import Secrets
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def remove_ansi_escape_codes(text):
    """Remove ANSI escape codes from a string."""
    ansi_escape = re.compile(r'\x1b\[([0-9;]*[mGKH])')
    return ansi_escape.sub('', text)

def login_to_ipatool(email, password):
    """Log in to IPATool using the provided email and password."""
    logging.info("Logging in to IPATool...")
    try:
        # Run the ipatool auth login command
        result = subprocess.run(
            ['ipatool', 'auth', 'login', '-e', email, '-p', password],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logging.info("Successfully logged in to IPATool.")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to log in to IPATool: {e.stderr}")
        return False

def download_ipa(bundle_id):
    """Download the .ipa file using the provided bundle ID into IPA_Files directory."""
    try:
        ipa_dir = "IPA_Files"
        os.makedirs(ipa_dir, exist_ok=True)
        
        process = subprocess.Popen(
            ['ipatool', 'download', '-b', bundle_id, '--purchase', '-o', ipa_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output = ""
        while True:
            line = process.stdout.readline()
            if not line:
                break
            output += line


        process.wait()


        last_line = output.strip().split('\n')[-1]
        last_line = remove_ansi_escape_codes(last_line)

        if 'success=true' not in last_line:
            logging.error(f"Download failed. Last line: {last_line}")
            return None

        # Fix: Extract IPA filename correctly
        filename_match = re.search(r'output=["\']?([^"\']+\.ipa)["\']?', last_line)
        if filename_match:
            ipa_filename = filename_match.group(1)
            ipa_filename = ipa_filename.strip()  # Ensure no extra whitespace

            # Check if file exists
            if not os.path.exists(ipa_filename):
                logging.error(f"Warning: File not found at extracted path: {ipa_filename}")
                basename = os.path.basename(ipa_filename)
                fallback_path = os.path.join(ipa_dir, basename)
                if os.path.exists(fallback_path):
                    logging.error(f"Found file at fallback path: {fallback_path}")
                    ipa_filename = fallback_path
                else:
                    logging.error("File not found in either location")
                    return None
            
            logging.info(f"Downloaded .ipa file: {ipa_filename}")
            return ipa_filename
        else:
            logging.error(f"Could not determine the .ipa filename from the output. Last line: {last_line}")
            return None
    except Exception as e:
        logging.error(f"Failed to download .ipa file: {str(e)}")
        return None


def install_ipa(ipa_filename):
    """Install the .ipa file using ideviceinstaller."""
    logging.info("Installing the .ipa file...")
    try:
        # Run the ideviceinstaller command
        result = subprocess.run(
            ['ideviceinstaller', '-i', ipa_filename],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logging.info(f"Successfully installed {ipa_filename} on the device.")
        return True
    except subprocess.CalledProcessError as e:
        loggint.error(f"Failed to install .ipa file: {e.stderr}")
        return False

def run_second_script(bundle_id, platform, timout=30):
    """Run the second script for UI automation."""
    logging.info("Running the llm_guided_consent_finder...")
    try:
        # Path to the second script
        second_script_path = "llm_guided_consent_finder.py"

        # Run the second script with the provided arguments
        result = subprocess.run(
            [sys.executable, second_script_path, '-b', bundle_id, '-p', platform, '-t', timout],
            check=True,
            #commenting the following two lines to make the script able to print its logs in the terminal
            # stdout=subprocess.PIPE, 
            # stderr=subprocess.PIPE,
            text=True
        )
        logging.info("Second script executed successfully.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to run the second script: {e.stderr}")
        sys.exit(1)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Download and install an .ipa file using IPATool and ideviceinstaller.")
    parser.add_argument('-b', '--bundle_id', required=True, help="The bundle ID of the app to download.")
    parser.add_argument('-p', '--platform', required=True, choices=['iOS', 'android'], help="The platform of the app (iOS or android).")
    parser.add_argument('-t', '--timeout', required=False, help='Time limit for finding the Second CMP Layer - 30 minutes by default')
    args = parser.parse_args()
    
    if args.platform not in ["iOS", "android"]:
        logging.error("Unknown platform")
        sys.exit(1)
        

    # Get App Store credentials from environment variables
    appstore_email = Secrets.AppStore_EMAIL
    appstore_password = Secrets.AppStore_PASSWORD

    if not appstore_email or not appstore_password:
        logging.error("Error: AppStore_email and AppStore_password environment variables must be set.")
        sys.exit(1)

    # Step 1: Log in to IPATool
    if not login_to_ipatool(appstore_email, appstore_password):
        sys.exit(1)

    # Step 2: Download the .ipa file
    ipa_filename = download_ipa(args.bundle_id)
    if not ipa_filename:
        sys.exit(1)

    # Step 3: Install the .ipa file
    if not install_ipa(ipa_filename):
        sys.exit(1)

    logging.info("App downloaded and installed successfully.")

    # Step 4: Run the second script for UI automation
    run_second_script(args.bundle_id, args.platform, args.timeout)

if __name__ == "__main__":
    main()
