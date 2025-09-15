import time
import logging
import ContextTracker
from ContextTracker import tracker
from ContextTracker import paths_context
from selenium.webdriver.common.by import By
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException
import Image_processor
import html
import re
import xml.etree.ElementTree as ET
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from selenium.webdriver.common.by import By
from typing import List
from io import StringIO
import base64
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def class_to_html_tag_ios(class_name):

    if tracker.platform  == "iOS":
        # iOS UI class to HTML tag mapping
        mapping = {
            'XCUIElementTypeButton': 'button',
            'XCUIElementTypeStaticText': 'span',
            'XCUIElementTypeTextField': 'input',
            'XCUIElementTypeImage': 'img',
            'XCUIElementTypeCell': 'li',
            'XCUIElementTypeSwitch': 'input type="checkbox"',
            'XCUIElementTypeRadioButton': 'input type="radio"',
            'XCUIElementTypeTable': 'table',
            'XCUIElementTypeCollectionView': 'div',
            'XCUIElementTypeOther': 'div'
        }
        return mapping.get(class_name, 'div')

    elif tracker.platform == "android":
        mapping = {
            'android.widget.Button': 'button',
            'android.widget.TextView': 'span',
            'android.widget.EditText': 'input',
            'android.widget.ImageView': 'img',
            'android.view.ViewGroup': 'div',
            'android.widget.CheckBox': 'input type="checkbox"',
            'android.widget.RadioButton': 'input type="radio"',
            'android.widget.ListView': 'ul',
            'android.widget.LinearLayout': 'div',
            'android.widget.RelativeLayout': 'div'
        }
        return mapping.get(class_name, 'div')


def accept_reject_confirm_elements_filter(element):

    keys = ['accept', 'reject', 'allow', 'confirm', 'save', 'toggle', 'update', 'dismiss', 'done', 'close']

    name = get_name_attribute(element)
    label = get_label_attribute(element)
    el_desc = element_desc_as_string(element)

    #check if the name or the label of the element has any of the keywords
    if ((name and any(word in name.lower() for word in keys)) or
            (label and any(word in label.lower() for word in keys))):

        logging.info(f'Element that may cause CMP UI termination: {el_desc}')
        tracker.accept_reject_confirm_elements_descs.append(el_desc)
        return True

    else:
        tracker.non_accept_reject_confirm_elements_descs.append(el_desc)
        return False




def retrieve_all_elements(driver):

    logging.info(f"Retrieving elements of the current screen")
    # Find all elements on the current screen
    elements = driver.find_elements(AppiumBy.XPATH, "//*[self::*]")  # Find all elements on the screen using XPath

    elements_with_id_or_label = []

    # Iterate over the found elements and print their attributes
    for index, element in enumerate(elements):
        element_id = get_name_attribute(element)
        element_label = get_label_attribute(element)

        # Skip elements where 'id' and 'label' are both None
        if element_id is None and element_label is None:
            continue

        elements_with_id_or_label.append(element)

    return elements_with_id_or_label


def is_this_in_path_consents_ui(driver):
    #this function check if the passed screen page_source is already exist in the path from launch the app to the consents ui or not
    logging.info(f'Check current screen fingerprint against previous screens...')
    for screen in paths_context.cmp_ui_path:

        # if verify_all_xpaths_exist(driver, set(screen.static_texts)):
        #     return True
        try:
            el = driver.find_element(By.XPATH, screen.element_clicked_xpath)
            if el.get_attribute("visible") == "true":
                return True
        
        except:
            continue

    return False




def get_current_app_results_folder_name() -> str:
    """Get results folder path for current app
    Returns a path with proper handling of .app names to maintain regular folder icon on macOS"""
    results_folder = "llm_guided_consent_finder_Results"
    folder_name = f"{results_folder}/{tracker.app_name}-{tracker.bundle_id}"

    # Ensure we don't create a special .app bundle by adding a trailing slash
    if folder_name.endswith('.app'):
        folder_name += "/"  # This will be automatically normalized by the OS
    return folder_name


def retrieve_clickable_elements(driver):
    """Optimized version with same I/O but better performance"""
    logging.info('Extracting the clickable elements in the current screen')

    # Single XPath query for all relevant elements
    clickable_xpath = get_clickable_xpaths()

    # Batch retrieve elements and attributes
    elements = driver.find_elements(AppiumBy.XPATH, clickable_xpath)
    if not elements:
        return []

    # Pre-process elements in a single pass
    seen_labels = set()
    unique_elements = []

    for element in elements:
        # Batch get all attributes at once
        el_type = get_type_attribute(element)
        el_label = get_label_attribute(element)
        el_name = get_name_attribute(element)

        # Skip elements without labels or names
        if not el_label and not el_name:
            continue

        # Ensure no duplicates
        label_key = el_label.lower() if el_label else el_name.lower()
        if label_key in seen_labels:
            continue

        # Add label to seen labels
        seen_labels.add(label_key)

        # Append the element if it's visible and enabled, commenting the if displayed condition because the element may be down below in the page
        if element.is_displayed() and element.is_enabled():
            unique_elements.append(element)
        # if element.is_enabled():
        #     unique_elements.append(element)


    return unique_elements



def retrieve_next_clickable_elements(driver, all_clickable_elements_xpaths):
    """Optimized version with same I/O but better performance"""
    logging.info('Retrieving the next clickable elements')

    next_elements_xpath = []
    for xpath in all_clickable_elements_xpaths:
        if xpath not in tracker.consents_ui_elements_clicked_xpaths:
            next_elements_xpath.append(xpath)

    # Batch retrieve elements and attributes
    if not next_elements_xpath:
        logging.info(f'Could not find elements match the xpath(s)')
        return []  # No new elements to process

    # Combine all XPaths using " | " (OR condition) for batch retrieval
    combined_xpath = " | ".join(next_elements_xpath)

    elements = driver.find_elements(AppiumBy.XPATH, combined_xpath)
    return elements if elements else []


def retrieve_exact_list_clickable_elements(driver, elements_descs):
    """Optimized version with same I/O but better performance"""
    logging.info('Retrieving the exact list of clickable elements')

    next_elements_xpath = []
    for e in elements_descs:
        xpath = generate_xpath(e)
        next_elements_xpath.append(xpath)

    # Batch retrieve elements and attributes
    if not next_elements_xpath:
        logging.info(f'Could not find elements match the xpath(s)')
        return []  # No new elements to process

    # Combine all XPaths using " | " (OR condition) for batch retrieval
    combined_xpath = " | ".join(next_elements_xpath)

    elements = driver.find_elements(AppiumBy.XPATH, combined_xpath)
    return elements if elements else []


def retrieve_exact_clickable_element(driver, element_xpath):
    """Optimized version with same I/O but better performance"""
    logging.info('Retrieving the exact clickable element')

    clickable_element = None

    if element_xpath:
        clickable_element_found = driver.find_element(AppiumBy.XPATH, element_xpath)

        if clickable_element_found:
            logging.info(f'Matched clickable element found')
            clickable_element = clickable_element_found

    return clickable_element


def get_all_previous_clicked_elements():

    elements = ""
    for index, e in enumerate(paths_context.current_path):
        elements += f"[{index}]:{e.element_clicked_xpath}\n"

    print(f'Elements clicked so far:\n{elements}')
    return elements



def parse_and_sort_elements(gpt_response):
    parsed_elements = []
    lines = gpt_response.strip().split("\n")  # Split response into lines

    for line in lines:
        if ":" in line:
            # Split the line at the first ":" to separate index and content
            index, element = line.split(":", 1)
            parsed_elements.append((int(index.strip()), element.strip()))

    # Sort elements by priority index and return only the element content
    sorted_elements = [element for _, element in sorted(parsed_elements, key=lambda x: x[0])]

    return sorted_elements


def element_desc_as_string(element):
    attributes = {
        "name": get_name_attribute(element),
        "label": get_label_attribute(element),
        "type": get_type_attribute(element),
        # "visible": get_visible_attribute(element),
    }

    return " ".join(f"{key}:{value}" for key, value in attributes.items() if value is not None)





# def extract_enabled_elements_xpaths(driver) -> list[str]:
#     """
#     Extracts XPaths for enabled elements of specific types in format: //ElementType[@name='value']

#     Args:
#         page_source: XML string from Appium

#     Returns:
#         List of XPaths like ["//XCUIElementTypeButton[@name='Done']", ...]
#     """
#     target_types = {
#         'XCUIElementTypeButton',
#         'XCUIElementTypeStaticText',
#         'XCUIElementTypeCell',
#         # 'XCUIElementTypeLink',
#         # 'XCUIElementTypeSwitch',
#         'XCUIElementTypeOther' #i.e. Cheap Oair app has all of its elements as XCUIElementTypeOther (they may used Flutter)
#     }

#     page_source = driver.page_source

#     try:
#         root = ET.fromstring(page_source)
#         xpaths = []

#         for elem in root.iter():
#             # Skip if not target type or not enabled
#             if (elem.tag not in target_types or
#                     elem.attrib.get('enabled', '').lower() != 'true'):
#                 #or elem.attrib.get('visible', '').lower() != 'true'):
#                 continue

#             # Get name if exists (prefer 'name', fallback to 'label')
#             name = elem.attrib.get('name')
#             label = elem.attrib.get('label')
#             if name and label:
#                 xpaths.append(f"//{elem.tag}[@name='{name}' and @label='{label}']")
#             elif name:
#                 xpaths.append(f"//{elem.tag}[@name='{name}']")


#         return xpaths

#     except ET.ParseError:
#         return []

def extract_enabled_elements_xpaths(driver) -> list[str]:
    """
    Extracts XPaths for enabled elements of specific types using Appium XPath queries.

    Returns:
        List of XPath strings like ["//XCUIElementTypeButton[@name='Done']", ...]
    """
    target_types = [
        'XCUIElementTypeButton',
        'XCUIElementTypeStaticText',
        'XCUIElementTypeImage', #Confirmed the use of it (Roland-Garros:com.fft.rolandgarros app use images for navigation bar items)
        # 'XCUIElementTypeCell', #Cell without XCUIElementTypeStaticText will be useless, so no need to catch it (reducing the items I'm looking for)
        'XCUIElementTypeOther'
    ]

    xpaths = []

    for el_type in target_types:
        # Find all matching elements of this type with @enabled='true'
        elements = driver.find_elements(
            AppiumBy.XPATH,
            f"//{el_type}[@enabled='true']"
        )

        for el in elements:

            try:
                name = el.get_attribute("name")
                label = el.get_attribute("label")

                if name and label:
                    xpath = f"//{el_type}[@name='{name}' and @label='{label}']"
                elif name:
                    xpath = f"//{el_type}[@name='{name}']"
                else:
                    continue

                xpaths.append(xpath)

            except:
                continue


    return xpaths



def find_tabbar_elements(driver):

    consents_screen_elements_xpaths = '''
                                    //*[
                                        (
                                            self::XCUIElementTypeButton[
                                                @enabled='true' and @visible='true' and @name != "" and @label != ""
                                                and (ancestor::XCUIElementTypeTabBar//XCUIElementTypeButton)
                                            ] 
                                            or 
                                            self::XCUIElementTypeLink[
                                                @enabled='true' and @visible='true' and @name != "" and @label != ""
                                                and (ancestor::XCUIElementTypeTabBar//XCUIElementTypeLink)
                                            ] 
                                            or 
                                            self::XCUIElementTypeStaticText[
                                                @enabled='true' and @visible='true' and @name != "" and @label != ""
                                                and (ancestor::XCUIElementTypeTabBar//XCUIElementTypeStaticText)
                                            ] 
                                        )
                                    ]
                                    '''

    consents_screen_elements = driver.find_elements(By.XPATH, consents_screen_elements_xpaths)
    print(f'Found {len(consents_screen_elements)}')
    for el in consents_screen_elements:
        print(element_desc_as_string(el))


def extract_enabled_elements_xpaths_for_consent_screen(driver) -> list[str]:

    #TODO: defer the interaction with the blacklist elements: "accept", "reject", "deny", "close", "done", "update", "toggle", ...
    clickable_elements_xpaths = []
    consents_screen_elements_xpaths = '''(
                                        //XCUIElementTypeButton[
                                        @enabled='true' and 
                                        @visible='true' and 
                                        @name != "" and 
                                        @label != "" and 
                                        not(ancestor::XCUIElementTypeTabBar)
                                        ]
                                        |                                        
                                        //XCUIElementTypeStaticText[
                                        @enabled='true' and 
                                        @visible='true' and 
                                        @name != "" and 
                                        @label != "" and 
                                        not(ancestor::XCUIElementTypeTabBar) and not(ancestor::XCUIElementTypeButton) 
                                        ]
                                        )
                                        '''

    consents_screen_elements = driver.find_elements(By.XPATH, consents_screen_elements_xpaths)

    for el in consents_screen_elements:

        el_name = el.get_attribute("name")
        el_label = el.get_attribute("label")
        el_type = el.get_attribute("type")


        xpath = f'//{el_type}[@name="{el_name}" and contains(@label, "{el_label}")]'
        if xpath not in clickable_elements_xpaths:
            clickable_elements_xpaths.append(f"//{el_type}[@name='{el_name}' and contains(@label, '{el_label}')]")
        else:
            continue

    
    return clickable_elements_xpaths


def get_inner_static_text_of_cell(cell_element):

    try:
        static_text = cell_element.find_element(By.XPATH, './/XCUIElementTypeStaticText[@enabled="true" and @visible="true" and @name != "" and @label != ""]')
        text_name = static_text.get_attribute("name")
        text_label = static_text.get_attribute("label")
        text_type = static_text.get_attribute("type")
        xpath = f'//{text_type}[@name="{text_name}" and contains(@label, "{text_label}")]'

        return xpath

    except:
        print(f'Could not find a static text for this useless cell')
        return None





def extract_xpath(element_string):
    """
    Generate an XPath from an element string in the format:
    element: <type="XCUIElementTypeOther" name="clickMe" label="Click Me">
    """
    # Use regex to find attribute key-value pairs, regardless of preceding noise
    attributes_dict = dict(re.findall(r'(\w+)="([^"]*)"', element_string))

    # Decode HTML entities and strip leading/trailing spaces
    # attributes_dict = {k: html.unescape(v.strip()) for k, v in attributes_dict.items()}
    attributes_dict = {k: html.unescape(v.strip()).rstrip('.') for k, v in attributes_dict.items()}

    # Extract the element type from the attributes dictionary or use a default
    element_type = attributes_dict.pop("type", "XCUIElementTypeAny")

    # Construct XPath dynamically
    xpath_conditions = []

    for k, v in attributes_dict.items():
        if k in {"name"}:
            # Exact match for other attributes
            xpath_conditions.append(f"@{k}='{v}'")

    xpath_query = f"//{element_type}[{' and '.join(xpath_conditions)}]"


    logging.info(f'Locating element with xpath {xpath_query}')
    return xpath_query



def navigation_status(driver):
    #each screen's fingerprint is its own page_source which has a list of elements


    for consents_static_texts in tracker.consents_ui_fingerprint:

        if verify_all_xpaths_exist(driver, set(consents_static_texts)):

            # for el in tracker.consents_ui_fingerprint:

            #find a way to check for "still_same" status
            return "same"

    if is_this_in_path_consents_ui(driver):
        return "navigated_back"

    # elif set(tracker.consents_screen_statics_xpaths).issubset(current_screen_statics_xpaths_set):
    #     return "still_same"

    else:
        return "navigated_deeper"


def generate_xpath(element_string):
    # Split the input string into key-value pairs
    attributes = dict(item.split(":", 1) for item in element_string.split(" ") if ":" in item)

    # Start building the XPath query
    xpath_query = "//*"

    if tracker.platform == "iOS":
        conditions = []
        if "name" in attributes:
            conditions.append(f"contains(@name, '{attributes['name']}')")
        if "label" in attributes:
            conditions.append(f"contains(@label, '{attributes['label']}')")
        if "type" in attributes:
            conditions.append(f"contains(@type, '{attributes['type']}')")
        # if "visible" in attributes:
        #     conditions.append(f"contains(@visible, '{attributes['visible']}')")

        # Combine conditions into a valid XPath
        if conditions:
            xpath_query += "[" + " and ".join(conditions) + "]"

        return xpath_query

    elif tracker.platform == "android":
        conditions = []
        if "resource-id" in attributes:
            conditions.append(f"contains(@resource-id, '{attributes['resource-id']}')")
        if "text" in attributes:
            conditions.append(f"contains(@text, '{attributes['text']}')")
        if "class" in attributes:
            conditions.append(f"contains(@class, '{attributes['class']}')")
        if "visible" in attributes:
            conditions.append(f"contains(@visible, '{attributes['visible']}')")

        # Combine conditions into a valid XPath
        if conditions:
            xpath_query += "[" + " and ".join(conditions) + "]"

        return xpath_query


def check_all_xpaths_exist(driver, buttons_descs):
    """
    Check if all XPaths in the list exist on the current screen.

    :param driver: The Appium WebDriver instance.
    :param xpath_list: A list of XPaths to check.
    :return: True if all XPaths exist, False otherwise.
    """
    for desc in buttons_descs:
        xpath = generate_xpath(desc)
        elements = driver.find_elements(AppiumBy.XPATH, xpath)
        if not elements:  # If no elements are found for the current XPath
            return False
    return True  # All XPaths exist

def navigation_status_using_xpaths(driver):

    if check_all_xpaths_exist(driver, tracker.non_accept_reject_confirm_elements_descs):
        logging.info(f"No navigation detected")
        return  "still_same"

    else:
        for screen in paths_context.cmp_ui_path:
            xpath = generate_xpath(screen.element_clicked_xpath)
            element = driver.find_element(AppiumBy.XPATH, xpath)
            if element:
                print(f'xpath generated {xpath}')
                logging.info(f"Navigated back")
                return "navigated_back"


    return "navigated_deeper"


def fingerprinting_screen(driver):

    results = get_all_static_text_xpaths(driver)
    # results = extract_enabled_elements_xpaths(driver)
    return results


def fingerprinting_cmp_screen(driver):
    #This is special kind of fingerprint that will exclude accept, reject and similar elements (to cover the dynamic content of Didomi CMP screens as they change Accept All to Done in case of turning on/off all options)
    results = get_all_static_text_xpaths(driver, True)
    # results = extract_enabled_elements_xpaths(driver)
    return results



def verify_all_xpaths_exist(driver, xpaths_list_to_be_checked):
    """
    Enhanced version with logging of missing elements.
    """

    all_exist = True
    for xpath in xpaths_list_to_be_checked:
        try:
            """
            use find_elements not find_element, as find_elements will allow us to check the overall page source not only ones on the current screen.
            That helps when we swiped up or down
            """
            elements_matched = driver.find_elements(By.XPATH, xpath) 
            
            #The element is not exist at all
            if len(elements_matched) == 0:
                    print(f'{len(elements_matched)} This xpath not exist: {xpath}')
                    return False
            
            #element exists but it is covered by modal screen (Didomi architecture keeps elements still in the page_source becuase they are overlapping each other)
            elif elements_matched[0].get_attribute('visible') == 'false':
                    print('An element is not visible anymore')
                    return False
            
            print(f'{elements_matched[0].get_attribute('visible')}')
            # driver.find_element(By.XPATH, xpath) 
            

        except NoSuchElementException:
            print(f"Element not found: {xpath}")
            return False


    return all_exist


#used to detect changes on the Consents screen (such as changing the values of SwitchButtons)
def elements_with_values(driver):

    results = []
    xpath = """
            //*[
                (self::XCUIElementTypeButton or self::XCUIElementTypeSwitch) 
                and string-length(@name) > 0 
                and string-length(@value) > 0
            ]
            """

    elements = driver.find_elements(By.XPATH, xpath)
    for el in elements:

        type = el.get_attribute("type")
        name = el.get_attribute("name")
        value = el.get_attribute("value")

        results.append(f"//{type}[@name={name} and @value={value}]")
    
    return results



def get_all_static_text_xpaths(driver, exclude_accept_reject_elements=False) -> List[str]:
    """
    Returns XPaths of all XCUIElementTypeStaticText elements that have either name or label attributes.

    Args:
        driver: Appium WebDriver instance

    Returns:
        List of valid XPath strings (only for elements with name/label)
    """
    results = []

    #@visible="true" to cover Modal screens (in case we don't set the visible -> we will get elements that are behind the Modal screen)
    XPath = """(//XCUIElementTypeStaticText[string-length(@name) > 0 and string-length(@label) > 0 and @visible="true"])[position() <= 15]"""
    static_texts = driver.find_elements(By.XPATH, XPath)

    if len(static_texts) == 0:   
        XPath = """(//XCUIElementTypeOther[string-length(@name) > 0 and string-length(@label) > 0 and @visible="true"])[position() <= 15"""
        static_texts = driver.find_elements(By.XPATH, XPath)

    for element in static_texts:
        # Check if element has either name or label attribute
        name = element.get_attribute('name')
        label = element.get_attribute('label')
        type = element.get_attribute('type')

        #exclude_accept_reject_elements = True only when we are fingerprinting the CMP Layers
        if exclude_accept_reject_elements:
            keys = ['accept', 'reject', 'allow', 'confirm', 'save', 'toggle', 'update', 'dismiss', 'done', 'close']
            #check if the name or the label of the element has any of the keywords
            if ((name and any(word in name.lower() for word in keys)) or
                    (label and any(word in label.lower() for word in keys))):
                continue
        

        if name is None and label is None:
            continue  # Skip elements without either attribute

        if len(label) > 40:
            label = label[:40]  # Slice to first 40 characters

        results.append(f"""//{type}[@name="{name}" and contains(@label,"{label}")]""")
        # xpath = get_element_xpath(element)
        # # Only include if xpath contains attributes (not ending with [])
        # if not xpath.endswith('[]'):
        #     results.append(xpath)

    print(f'Found {len(results)} static text elements with name/label')
    return results



def get_next_unclicked_xpath(list_of_xpaths_to_choose_from):

    for xpath in list_of_xpaths_to_choose_from:
        if xpath not in tracker.consents_ui_elements_clicked_xpaths:
            return xpath
    
    #In case all the xpaths in the passes list are already clicked -> return None
    return None

def get_element_xpath(element) -> str:
    """
    Generates XPath only if element has name or label attributes.
    Returns empty-string-style XPath (ending with []) if no attributes found.
    """
    attributes = []

    if name := element.get_attribute('name'):
        attributes.append(f'@name="{name}"')
    if label := element.get_attribute('label'):
        attributes.append(f'contains(@label, "{label}")')
    if enabled := element.get_attribute('enabled'):
        attributes.append(f'@enabled="{enabled}"')




    if attributes:
        return f'//XCUIElementTypeStaticText[{" and ".join(attributes)}]'
    return '//XCUIElementTypeStaticText[]'  # Marker for no attributes


def get_app_name(driver):
    # Find the XCUIElementTypeApplication element (it's usually the root element)
    application_element = driver.find_element(AppiumBy.XPATH, "//*[contains(@type, 'XCUIElementTypeApplication')]")
    # Get the 'name'
    app_name = get_name_attribute(application_element) or "noAppName"

    return f"{app_name}"

def get_app_label(driver):
    # Find the XCUIElementTypeApplication element (it's usually the root element)
    application_element = driver.find_element(AppiumBy.XPATH, "//*[contains(@type, 'XCUIElementTypeApplication')]")
    # Get the 'label' attributes
    app_label = get_label_attribute(application_element) or "noAppLabel"

    return f"{app_label}"

def get_app_name_and_label(driver):
    # Find the XCUIElementTypeApplication element (it's usually the root element)
    application_element = driver.find_element(AppiumBy.XPATH, "//*[contains(@type, 'XCUIElementTypeApplication')]")
    # Get the 'name' and 'label' attributes
    app_name = get_name_attribute(application_element) or "noAppName"
    app_label = get_label_attribute(application_element) or "noAppLabel"

    return f"{app_name}:{app_label}"




def swipe_until_element_clickable(driver, element):
    """Scroll down until the element with the given XPath is clickable."""
    logging.info(f'Swiping down looking for {element_desc_as_string(element)}')
    try:
        driver.execute_script("mobile:scroll", {"direction": "down", "element": element})
        time.sleep(1)
        element_desc = element_desc_as_string(element)
        element_xpath = generate_xpath(element_desc)
        element = driver.find_element(AppiumBy.XPATH, element_xpath)

        if element.is_displayed() and element.is_enabled():
            print("Element is_displayed and is_enabled.")
            return True
    except:
        logging.info(f"Error: Element is_displayed? {element.is_displayed()} is_enabled? {element.is_enabled()}.")
        return False


def swipe_up_full(driver):
    logging.info(f'Swiping up...')
    driver.execute_script("mobile: swipe", {
        "direction": "down",
        "percent": 0.01,
        "speed": 1000 #iOS only (speed: 1000 → Slower than default (lower values = faster, higher = slower on iOS))
    })

def swipe_down_full(driver):
    logging.info(f'Swiping down...')
    driver.execute_script("mobile: swipe", {
        "direction": "up",
        "percent": 0.01,
        "velocity": 500, #a little, 500 larger, 700 extremely larger (full screen)
        "speed": 1000 #iOS only (speed: 1000 → Slower than default (lower values = faster, higher = slower on iOS))
    })


def swipe_up_little(driver):
    #moving the screen from down to up
    logging.info("Swiping up slightly...")
    driver.execute_script("mobile: swipe", {
    "direction": "down",
    "percent": 0.01,
    "velocity": 100, #a little, 500 larger, 700 extremely larger (full screen)
    "speed": 1000 #iOS only (speed: 1000 → Slower than default (lower values = faster, higher = slower on iOS))
    })


def swipe_down_little(driver):
    #moving the screen from up to down
    logging.info("Swiping down slightly...")
    driver.execute_script("mobile: swipe", {
        "direction": "up",
        "percent": 0.01,
        "velocity": 100, #a little, 500 larger, 700 extremely larger (full screen)
        "speed": 1000 #iOS only (speed: 1000 → Slower than default (lower values = faster, higher = slower on iOS))
    })


def swipe_up_little_using_drag(driver):
    #this works find but it will behave as a click in case the starting points x,y meet with a clickable element
    logging.info("Swiping up slightly using dragFromToForDuration...")
    size = driver.get_window_size()
    start_x = size['width'] // 2
    start_y = size['height'] // 3
    end_y = start_y + 40  # move downward

    driver.execute_script("mobile: dragFromToForDuration", {
        "duration": 0.3,
        "fromX": start_x,
        "fromY": start_y,
        "toX": start_x,
        "toY": end_y
    })

def swipe_down_little_using_drag(driver):
    #this works find but it will behave as a click in case the starting points x,y meet with a clickable element
    logging.info("Swiping down slightly using dragFromToForDuration...")
    size = driver.get_window_size()
    start_x = size['width'] // 2  
    start_y = size['height'] * 2 // 3
    end_y = start_y - 40  # move upward

    driver.execute_script("mobile: dragFromToForDuration", {
        "duration": 0.3,
        "fromX": start_x,
        "fromY": start_y,
        "toX": start_x,
        "toY": end_y
    })


def go_to_the_top(driver):

    try:

        top_element = get_first_visible_element(driver)
        center_x, center_y = get_center_of(top_element)

        reached_top = False
           # make sure the element in within the screen boundaries
        while not reached_top:  # -200 for the height of the tabbar
            swipe_up_full(driver)
            new_center_x, new_center_y = get_center_of(top_element)

            if new_center_y == center_y:
                logging.info(f'Reached the top')
                return True

            else:
                center_y = new_center_y
        
    except NoSuchElementException:
        return False
    

def get_first_visible_element(driver):
    """Returns the first visible element matching the XPath (top-to-bottom, left-to-right)."""

    xpath = '''
            //XCUIElementTypeStaticText[
            string-length(@name) > 0 and 
            string-length(@label) > 0 and 
            @enabled="true" and 
            @visible="true"
            ]
            '''
    try:
        top_element = driver.find_element(By.XPATH, xpath)
        return top_element
    
    except NoSuchElementException:
        return None



def try_different_different_backs_strategies(driver):

    #To handle inner screens that has the back button in the navigation bar
    back_status = go_back_using_navigation(driver)
    if not back_status:
         #To handle screens that use swipe right to go back
        back_status = go_back_using_swipe_right(driver)
        if not back_status:
            return False

    return True


#in iOS apps, the navigation bar has the back button as the first button
def go_back_using_navigation(driver):
    try:
        # Attempt to find and click the back button
        # back_button = driver.find_element(By.XPATH, '//XCUIElementTypeNavigationBar/XCUIElementTypeButton[1]')
        """ this xpath looking for the following three buttons:
        1- back: for navigation bar
        2- done: for Safari within the app
        3- close: for Modal screens such as what Didomi CMP has
        """

        back_button = driver.find_element(
            By.XPATH,
            '''
            //XCUIElementTypeButton[
                translate(@name, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz") = "back" or
                translate(@label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz") = "back" or
                translate(@name, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz") = "done" or
                translate(@label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz") = "done" or
                translate(@name, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz") = "close" or
                translate(@label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz") = "close"
            ]
            '''
        )
        if back_button.is_displayed and back_button.is_enabled():

            clicking_back_attempts_limit = 3

            while clicking_back_attempts_limit >= 0:
                back_button_name = back_button.get_attribute("name")
                back_button_label = back_button.get_attribute("label")
                back_button_type = back_button.get_attribute("type")

                logging.info(f'We found {back_button_name} of type {back_button_type}')
                tap_on_directly(driver, back_button)

                # if back_button_type != "XCUIElementTypeButton":
                #     tap_on_directly(driver, back_button)
                # else:
                #     back_button.click()

                time.sleep(1)

                clicking_back_attempts_limit -= 1

                navigation_status_res = navigation_status(driver)

                if navigation_status_res == "same" or navigation_status_res == "still_same":
                    logging.info(f'Clicking Back button worked')
                    return True

                else:
                    logging.info(f'Clicking/tapping {back_button_name} did not work, {clicking_back_attempts_limit} attempts remaining')

                    continue
            
            logging.info(f'Exhaused all attempts, clicking/tapping back not working.')
            return False
        else:

            logging.warning("Back button exists but is not interactable")
            return False

    except NoSuchElementException:
        logging.error("Back button not found in the navigation bar")
        return False

    except ElementNotInteractableException:
        logging.error("Back button found but not clickable (may be obscured)")
        return False

    except Exception as e:
        logging.error(f"Unexpected error while clicking back button: {str(e)}")
        return False


#Works but not for tableViews
def go_back_using_swipe_right(driver):
    # used to go back in iOS devices
    driver.execute_script("mobile: dragFromToForDuration", {
        "duration": 0.2,
        "fromX": 1,  # Start near the left edge
        "fromY": driver.get_window_size()["height"] / 2,  # Middle of the screen
        "toX": driver.get_window_size()["width"] * 0.9,  # Swipe to the right
        "toY": driver.get_window_size()["height"] / 2
    })

    time.sleep(1)
    #check if we are now back to the consents screen
    navigation_status_res = navigation_status(driver)
    if navigation_status_res == "same" or navigation_status_res == "still_same":
        logging.info(f'Swiping to the right worked')
        return True
    else:
        logging.info(f'Swiping to the right did not work')
        return False



def found_new_elements_after_scroll_down(new_elements):

    new_elements_count = 0
    for e in new_elements:

        if element_desc_as_string(e) in tracker.accept_reject_confirm_elements_descs or accept_reject_confirm_elements_filter(e):
            continue

        if not e.is_displayed() or not e.is_enabled():
            continue

        if not get_name_attribute(e) or not get_label_attribute(e):
            continue

        #return True in case we found at least one element that we haven't seen before
        if element_desc_as_string(e) not in tracker.consents_ui_elements_clicked_descs:
            new_elements_count += 1


    if new_elements_count > 0:
        logging.info(f'{new_elements_count} new elements found after swiping down')
        return True

    else:
        return False


def get_name_attribute(element):

    if tracker.platform == "iOS":
        return element.get_attribute('name')

    elif tracker.platform == "android":
        return element.get_attribute('resource-id')

def get_type_attribute(element):
    if tracker.platform == "iOS":
        return element.get_attribute('type')

    elif tracker.platform == "android":
        return element.get_attribute('class')

def get_label_attribute(element):
    if tracker.platform == "iOS":
        return element.get_attribute('label')

    elif tracker.platform == "android":
        return element.get_attribute('text')

def get_visible_attribute(element):
    if tracker.platform == "iOS":
        return element.get_attribute('visible')

    elif tracker.platform == "android":
        return element.get_attribute('visible')


def do_we_leave_the_app(driver):
    #Check if we left the app -> yes? return to our app
    if get_app_name_and_label(driver) != f"{tracker.app_name}:{tracker.app_label}":
        logging.info('Left the app, trying to return.')
        return True
    
    else:
        return False


def get_back_to_the_app(driver):
        driver.activate_app(tracker.bundle_id)
        time.sleep(5)  #to allow the current app load completely


def terminate_and_relaunch(driver):
    driver.terminate_app(tracker.bundle_id)
    driver.activate_app(tracker.bundle_id)
    time.sleep(5)


def get_clickable_elements_types():

    if tracker.platform == "iOS":
        return ['XCUIElementTypeButton', 
                'XCUIElementTypeStaticText', 
                'XCUIElementTypeCell', 
                # 'XCUIElementTypeLink',
                'XCUIElementTypeOther'
                ]

    elif tracker.platform == "android":
        return ['android.widget.Button', 'android.widget.TextView', 'android.widget.ListView', 'android.widget.EditText', 'android.widget.EditText']


def get_clickable_xpaths():

    full_xpaths = "//*["
    valid_types = get_clickable_elements_types()

    for index, valid_type in enumerate(valid_types):
        if index == len(valid_types) - 1:
            full_xpaths += f"(@type='{valid_type}' and @enabled='true')]"

        else:
            full_xpaths += f"(@type='{valid_type}' and @enabled='true') or"

    return  full_xpaths



def alert_appeared(driver):
    try:
        # Search for an XCUIElementTypeAlert that is enabled and visible
        alert = driver.find_element(AppiumBy.XPATH, "//XCUIElementTypeAlert[@enabled='true' and @visible='true']")
        logging.info('An alert appeared on the screen.')

        # Take a screenshot and save it for the Alert
        screenshot_as_png = driver.get_screenshot_as_png()
        screenshot_filename = f"alert_{tracker.inner_screenshot_counter}.png"
        Image_processor.save_png_image(screenshot_as_png, get_current_app_results_folder_name(), screenshot_filename)

        # Define the keywords to look for in button labels
        # Used to make sure to dismiss the alerts that may appear at the first launch of the app such as
        # asking for Notification, Location and Tracking
        negative_keywords = ["don't", "not", "no"]

        # Search for buttons with labels containing negative keywords
        for keyword in negative_keywords:
            try:
                # Find the button by its label containing the keyword (case-insensitive)
                button = alert.find_element(AppiumBy.XPATH, f".//XCUIElementTypeButton[contains(translate(@label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]")
                button.click()
                logging.info(f"Button with label containing '{keyword}' clicked to dismiss the alert.")
                return True  # Alert was dismissed
            except NoSuchElementException:
                continue  # Try the next keyword

        # If no negative keyword button is found, click any button in the alert
        # Used to dismiss general alerts such as those showed by developer to confirm update or so
        try:
            # Find any button in the alert
            any_button = alert.find_element(AppiumBy.XPATH, ".//XCUIElementTypeButton")
            button_label = any_button.get_attribute("label")
            any_button.click()
            logging.info(f"No negative keyword button found. Clicked button with label: '{button_label}'.")
            return True  # Alert was dismissed
        except NoSuchElementException:
            logging.warning("No buttons found in the alert.")
            return False  # Alert was not dismissed

    except NoSuchElementException:
        logging.info("No alert appeared on the screen.")
        return None  # No alert appeared


def alert_event_listener(driver):
    """Simpler wrapper using your original function"""
    try:
        # Just call your existing function
        result = alert_appeared(driver)
        if result is None:  # No alert found
            return
        # Log based on result if needed
    except Exception as e:
        logging.error(f"Alert check failed: {str(e)}")


def get_center_of(element):
    element_loaction = element.location
    x = element_loaction['x']
    y = element_loaction['y']
    width = element.size['width']
    height = element.size['height']

    center_x = x + (width / 2)
    center_y = y + (height / 3)

    return  center_x, center_y

def get_x_y(element):

    element_loaction = element.location
    x = element_loaction['x']
    y = element_loaction['y']

    return x, y

def tap_on_directly(driver, element) -> None:

    logging.info('Tapping on an element')
    center_x, center_y = get_center_of(element)
    driver.tap([(center_x, center_y)], 100)  # 100ms tap duration



def tap_on(driver, element) -> None:
    """Tap at specified screen coordinates"""

    logging.info('Tapping on an element')
    center_x, center_y = get_center_of(element)

    if element.get_attribute("type") != "XCUIElementTypeButton":
        driver.tap([(center_x, center_y)], 100)  # 100ms tap duration
    
    else:
        element.click()


def center_element_on_screen(driver, element, max_scrolls=15):
    logging.info('Centering the element on the screen')
    if is_element_in_tabbar(element):
        logging.info(f'Actually this element is part of a tabbar, cannot be in a higher position')

    def escape_xpath_value(s):
        return f"'{s}'" if '"' in s else f'"{s}"'

    try:
        el_type = element.get_attribute("type")
        el_name = element.get_attribute("name") or ""
        el_label = element.get_attribute("label") or ""
    except Exception as e:
        logging.warning(f"Could not retrieve element attributes: {e}")
        return

    # Build XPath
    xpath = ""
    if el_name and el_label:
        xpath = f'//{el_type}[@name={escape_xpath_value(el_name)} and contains(@label,{escape_xpath_value(el_label)})]'
    elif el_name:
        xpath = f'//{el_type}[@name={escape_xpath_value(el_name)}]'

    # Screen thresholds
    center_x, center_y = get_center_of(element)
    screen_height = driver.get_window_size()["height"]
    upper_y = screen_height / 10 #to avoid the navigation bar
    lower_y = (screen_height / 10) * 8 #to avoid the tabbar

    scroll_count = 0
    while (center_y < upper_y or center_y > lower_y) and scroll_count < max_scrolls:
        if center_y < upper_y: #the element's center is in a higher position than our upper y limit
            swipe_up_little(driver)
        else:
            swipe_down_little(driver)

        try:
            element = driver.find_element(By.XPATH, xpath)
            new_center_x, new_center_y = get_center_of(element)
        except Exception as e:
            logging.warning(f"Element disappeared or cannot be found again: {e}")
            break

        if new_center_y == center_y:
            logging.info(f'Element stopped moving — its y-axis now: {round(new_center_y, 2)}')
            break

        center_y = new_center_y
        scroll_count += 1

    if scroll_count >= max_scrolls:
        logging.warning("Reached max scroll attempts without centering fully")




def is_element_in_tabbar(element):
    try:
        tabbar_ancestor = element.find_element(AppiumBy.XPATH, "ancestor::XCUIElementTypeTabBar")
        return tabbar_ancestor is not None
    except:
        return False


def print_path_details(path):

    path_info = ""
    for indx, sc in enumerate(path):
        path_info += f"{indx + 1}: {sc.element_clicked_xpath}"





def convert_png_to_base64(png_image):

    # Read the file content and encode it
    return base64.b64encode(png_image).decode('utf-8')