"""
Consent Screen Finder for iOS Apps using Appium
"""

import os
import sys
import json
import time
import logging
import argparse
from typing import List
from appium import webdriver
from appium.options.ios import XCUITestOptions
import Navigator
import Image_processor
import Helper
from ContextTracker import tracker
from selenium.webdriver.common.by import By
import LLM


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Constants
CAPABILITIES = {
    'udid': 'c3d25a199e65f88e77a03059dfd908a1d5294dc9',
    'platformName': 'iOS',
    'automationName': 'XCUITest',
    'deviceName': 'Fares iPhone',
    'platformVersion': '16.7.10',
    'noReset': True,
    'xcodeSigningId': 'iPhone Developer',
    'xcodeOrgId': 'YJYU75UJZ8',
    'newCommandTimeout': 60,
    'logLevel': 'debug',
    'showXcodeLog':True
}
FILE_NAMES = {
    'screenshot': 'consents_ui_screenshot.png',
    'clicks_chain': 'consents_ui_clicks_chain.txt',
    'elements': 'consents_ui_elements.txt',
    'paths': 'inner_VCs_paths.txt',
    'connections': 'screens_connections.txt',
    'output': 'output_dict.txt'
}

def clicks_chain_info(visited_elements: List[str]) -> str:
    """Generate formatted string of click chain history"""
    chain = "\n".join([f"\t<{idx}> - {desc}"
                       for idx, desc in enumerate(visited_elements)])
    logging.info(f'Clicks chain info:\n{chain}')
    return f"{len(visited_elements)} clicks needed:\n{chain}"

def consents_ui_processing(driver, visited_elements: List[str]) -> None:
    """Process and save consent UI details"""
    logging.info('Processing Consents UI Screen')

    Navigator.click_all_elements_in(driver)

    save_consents_ui_details(
        visited_elements
    )

def save_consents_ui_details(visited_elements: List[str]) -> None:
    """Save all consent UI details to files"""
    logging.info(f'Saving results')
    folder = Helper.get_current_app_results_folder_name()
    os.makedirs(folder, exist_ok=True)

    # Save text data
    save_text_file(os.path.join(folder, FILE_NAMES['clicks_chain']), clicks_chain_info(visited_elements))

    screens_connections_filename = os.path.join(folder, FILE_NAMES['connections'])
    with open(screens_connections_filename, "w") as screens_connections_file:
        for line in tracker.inner_consents_ui_connections:
            screens_connections_file.write(line + "\n")

    Image_processor.create_connections_between_images(
        Helper.get_current_app_results_folder_name(), FILE_NAMES['connections']
    )

    # Save JSON output
    with open(os.path.join(folder, FILE_NAMES['output']), 'w') as f:
        json.dump(tracker.output_dic, f, indent=4)

    logging.info(f"Results stored in {folder}")

def save_text_file(path: str, content: any) -> None:
    """Helper to save text content to file"""

    if isinstance(content, (list, tuple)) and len(content) > 0:
        with open(path, 'w') as f:
            f.write("\n".join(content))
    elif isinstance(content, str):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    elif content:
        with open(path, 'w') as f:
            f.write(str(content))

def format_element(element) -> str:
    """Format element attributes as string"""
    attrs = ('name', 'label', 'visible', 'type')
    values = [element.get_attribute(attr) or f"No{attr.capitalize()}"
              for attr in attrs]
    return "|".join([f"Element{attr.capitalize()}:{val}"
                     for attr, val in zip(attrs, values)])




def main() -> None:

    """Main execution flow"""
    parser = argparse.ArgumentParser(description="Find consent UI in apps")
    parser.add_argument('-b', required=True, help='App bundle ID')
    parser.add_argument('-p', required=True, help='Platform iOS or android')
    parser.add_argument('-t', required=False, help='Time limit for finding the Second CMP Layer - 30 minutes by default')
    args = parser.parse_args()

    if not args.b:
        logging.error("Missing bundle ID")
        sys.exit(1)

    if not args.p:
        logging.error("Missing platform")
        sys.exit(1)

    if args.p not in ["iOS", "android"]:
        logging.error("Unknown platform")
        sys.exit(1)
    
    if args.t:
        tracker.time_limit = int(args.t)

    start_time = time.time()
    driver = None

    try:
        # Initialize driver
        capabilities = {**CAPABILITIES, 'bundleid': args.b}
        driver = webdriver.Remote(
            command_executor='http://localhost:4723',
            options=XCUITestOptions().load_capabilities(capabilities)
        )
        driver.activate_app(args.b)

        time.sleep(5)  # Allow app initialization

        # Initialize tracking
        tracker.platform = args.p
        tracker.bundle_id = args.b
        tracker.app_name = Helper.get_app_name(driver)
        tracker.app_label = Helper.get_app_label(driver)
        logging.info(f"App identifier: {tracker.app_name}:{tracker.app_label} - Running the script for {args.p} platform - Time limit set to {tracker.time_limit} mins")

        Navigator.go_find_consents_ui_screen(driver)



    # except Exception as e:
    #     logging.error(f"Fatal error: {str(e)}")
    finally:
        if driver:
            driver.quit()
        logging.info(f"Execution time: {time.time() - start_time:.2f}s")


if __name__ == "__main__":

    main()