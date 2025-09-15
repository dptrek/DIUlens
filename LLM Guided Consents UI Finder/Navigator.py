import Helper
import LLM
import Image_processor
import time
import sys
import llm_guided_consent_finder as LLMGCF
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from ContextTracker import tracker
from ContextTracker import paths_context
from ContextTracker import ScreenClicked
from ContextTracker import DictScreen
from ContextTracker import DictElement



def click_all_elements_in(driver):
    """
    Clicks all elements in the provided list, handling stale elements by refreshing the list if necessary.
    """
    second_layer_screenshot_counter = 0
    all_clickable_elements_xpaths = Helper.extract_enabled_elements_xpaths_for_consent_screen(driver)
    swipe_attempted = False

    while Helper.get_next_unclicked_xpath(all_clickable_elements_xpaths) or swipe_attempted == False:

        logging.info(f'In loop, elements to be clicked count: {len(set(all_clickable_elements_xpaths))}')
        logging.info(f'In loop, elements clicked so far count: {len(set(tracker.consents_ui_elements_clicked_xpaths))}')

        #In case of exhausting all elements
        # if no more elements, try to swipe down to find more elements
        # if set(tracker.consents_ui_elements_clicked_xpaths) == set(all_clickable_elements_xpaths):
        if not Helper.get_next_unclicked_xpath(all_clickable_elements_xpaths) and not swipe_attempted:
                logging.info(f'Swiping down looking for more elements')
                Helper.swipe_down_full(driver)
                tracker.current_swipe_counter += 1

                # save a new screenshot after scrolling
                screenshot_png = driver.get_screenshot_as_png()
                tracker.consents_ui_second_layer_screenshot = screenshot_png
                #no need to update it since we are always go to the top before checking the fingerprint
                tracker.consents_ui_fingerprint.append(Helper.fingerprinting_cmp_screen(driver))

                extended_second_layer_filename = f"second_layer_screenshot_{second_layer_screenshot_counter}.png"
                Image_processor.save_png_image(screenshot_png, Helper.get_current_app_results_folder_name(),
                                               f"{extended_second_layer_filename}")
                second_layer_screenshot_counter += 1
                updated_xpaths = set(Helper.extract_enabled_elements_xpaths_for_consent_screen(driver))
                new_xpaths = updated_xpaths - set(all_clickable_elements_xpaths)

                if len(new_xpaths) > 0:
                    #Update the consents screen fingerprint
                    # tracker.consents_ui_fingerprint = Helper.fingerprinting_screen(driver)
                    #Add the newly found elements
                    all_clickable_elements_xpaths = all_clickable_elements_xpaths + list(new_xpaths)
                    logging.info(f'{len(new_xpaths)} New elements found after swiping down')
                    """ I set swipe_attempted = False to force it to swipe again 
                    after exhausting all current elements 
                    """
                    swipe_attempted = False
                    continue

                else:
                    logging.info(f'No new elements found after swiping down')
                    swipe_attempted = True
                    continue

        #In case of remaining elements to interact with
        next_xpath = Helper.get_next_unclicked_xpath(all_clickable_elements_xpaths)
        logging.info(f'Next XPath: {next_xpath}')

        possible_buttons = driver.find_elements(By.XPATH, next_xpath)
        if len(possible_buttons) > 0:
            button = possible_buttons[0]
            button_label = button.get_attribute("label")
            button_text = button.get_attribute("name")
            button_type = button.get_attribute("type")
            button_desc = Helper.element_desc_as_string(button)
        
        else:
            continue


        if next_xpath in tracker.consents_ui_elements_clicked_xpaths:
            logging.info(f'Skipping, element already visited')
            continue


        tracker.consents_ui_elements_clicked_xpaths.append(next_xpath)
        screenshot_filename = f"inner_{tracker.inner_screenshot_counter}_highlighted.png"
        Helper.center_element_on_screen(driver, button)
        current_screenshot = driver.get_screenshot_as_png()
        Image_processor.highlight_element(
            current_screenshot, button, Helper.get_current_app_results_folder_name(), screenshot_filename
        )

        Helper.tap_on(driver, button)

        time.sleep(2)

        #Check if we left the app -> yes? return to our app
        left_the_app = False
        if Helper.do_we_leave_the_app(driver):
            _process_outer_screen_reached(driver, button_desc, button_label, screenshot_filename, "left_the_app")
            tracker.inner_screenshot_counter += 1
            time.sleep(5) #to allow the other app to open

            Helper.get_back_to_the_app(driver)
            if Helper.verify_all_xpaths_exist(driver, tracker.consents_screen_statics_xpaths):
                print(f'We are back to our app')

        #checking if clicking the button cause the appearance of an Alert, this function will deal with it
        Helper.alert_appeared(driver)

        #Check if clicking button caused moving to another screen
        navigation_status = Helper.navigation_status(driver)

        #Navigated to a new screen
        if navigation_status == "navigated_back":
            logging.info(f"Navigated back after clicking {button_label}.")
            _process_outer_screen_reached(driver, button_desc, button_label, screenshot_filename, navigation_status)
            tracker.inner_screenshot_counter += 1

            logging.info("Trying to return to the Consents UI.")

            if go_to_consents_ui(driver):
                logging.info(f'We are back to the Consents UI using the previous path')
            else:
                logging.info(f'We are relaunching the app as we failed to get back to the Consents UI')
                Helper.terminate_and_relaunch(driver)

        #we went deeper inside the consents screen, try to go back by swipe and if it didn't work try to find back/done button and click
        elif navigation_status == "navigated_deeper":
            logging.info(f"Navigated deeper after clicking {button_text}.")
            _process_outer_screen_reached(driver, button_desc, button_label, screenshot_filename, navigation_status)
            tracker.inner_screenshot_counter += 1

            if Helper.try_different_different_backs_strategies(driver):
                logging.info(f'We are back to the Consents UI')
            else:
                logging.info("Could not return to Consents UI, relaunching app.")
                driver.terminate_app(tracker.bundle_id)
                driver.activate_app(tracker.bundle_id)
                time.sleep(5)
                if go_to_consents_ui(driver):
                    logging.info(f'We are back to the Consents UI after relaunching the app')
                else:
                    logging.info(f'We are unable to find our old way back to the Consents UI, exiting the script')
                    exit(1)

        # Still in the same screen but a new elements appeared after clicking the button
        elif navigation_status == "still_same":
            logging.info(f"New element appeared after clicking {button_text}.")
            _process_outer_screen_reached(driver, button_desc, button_label, screenshot_filename, navigation_status)
            tracker.inner_screenshot_counter += 1

        # Didn't navigate to a new screen nor new elements appeared on the current screen after clicking the button
        elif navigation_status == "same":
            logging.warning(f"No navigation occurred after clicking {button_text}.")
            if not left_the_app:
                Image_processor.delete_png_image(Helper.get_current_app_results_folder_name(), screenshot_filename)

        else:
            logging.info(f"Unrecognized navigation status")


    logging.info("Clicked all elements.")



def go_back(driver):
    logging.info("Trying to find a way to go back")

    navigating_back_status = Helper.try_different_different_backs_strategies(driver)

    if navigating_back_status:
        return True

    else:
        logging.info("We are not back to the consents screen.")
        return False


def go_to_consents_ui(driver):
    #This function used when we already found the consents ui screen previously
    logging.info(f'Finding my way back to the Consents UI')


    clicks_count = 0

    consents_screen_matched = False
    while not consents_screen_matched:
        Helper.go_to_the_top(driver) #to make sure we have same fingerprint as the previous (assumption: each screen first showed at its top)
        current_screen_fingerprint = Helper.fingerprinting_screen(driver)
        logging.info(f'Looking for the consents UI screen')
        print(f'{len(paths_context.cmp_ui_path)} step(s) maximum needed to reach the CMP UI.')

        #return false in case we have number of clicks >= stored screens
        if clicks_count >= len(paths_context.cmp_ui_path):
            logging.info(f'Clicked buttons > number of stored screens in the path.')
            return False

        # Check if the current screen is one of screens that are in the path from launching the app to the Consents UI screen
        screens = paths_context.cmp_ui_path
        # matched_screen = next((screen for screen in screens if set(screen.fingerprint) == set(current_screen_fingerprint)), None)
        matched_screen = None
        for sc in screens:
            els = driver.find_elements(By.XPATH, sc.element_clicked_xpath)
            if len(els) > 0:
                matched_screen = sc



        if not matched_screen:
            logging.info(f'Could not find matched screen')
            return False

        else:
            logging.info(f'Matched screen found, I will find the exact clicked element clicked before')
            retrieved_element = Helper.retrieve_exact_clickable_element(driver, matched_screen.element_clicked_xpath)

            if retrieved_element:
                Helper.center_element_on_screen(driver, retrieved_element)
                Helper.tap_on(driver, retrieved_element)
                logging.info(f'Element matched and clicked')
                #sleep for one second to enable the driver to load the new content
                time.sleep(1)

        #Check now after clicking on the button
        if Helper.navigation_status(driver) == "same":
            consents_screen_matched = True

        #Update current screen fingerprint
        current_screen_fingerprint = Helper.fingerprinting_screen(driver)

    return consents_screen_matched


# def go_to_consents_ui(driver):
#     #This function used when we already found the consents ui screen previously
#     logging.info(f'Finding my way back to the Consents UI')
#     current_screen_fingerprint = Helper.fingerprinting_screen(driver)

#     clicks_count = 0

#     consents_screen_matched = False
#     while not consents_screen_matched:
#         logging.info(f'Looking for the consents UI screen')
#         print(f'{len(tracker.consent_ui_previous_screens_clicked)} steps needed to reach it')

#         #return false in case we have number of clicks >= stored screens
#         if clicks_count >= len(tracker.consent_ui_previous_screens_clicked):
#             logging.info(f'Clicked buttons > number of stored screens in the path.')
#             return False

#         # Check if the current screen is one of screens that are in the path from launching the app to the Consents UI screen
#         screens = tracker.consent_ui_previous_screens_clicked
#         matched_screen = next((screen for screen in screens if set(screen.fingerprint) == set(current_screen_fingerprint)), None)

#         if not matched_screen:
#             logging.info(f'Could not find matched screen')
#             return False

#         else:
#             logging.info(f'Matched screen found, I will find the exact clicked element clicked before')
#             retrieved_element = Helper.retrieve_exact_clickable_element(driver, matched_screen.element_clicked_xpath)

#             if retrieved_element:
#                 if retrieved_element.get_attribute("type") != "XCUIElementTypeButton":
#                     Helper.tap_on(driver, retrieved_element)
#                 else:
#                     logging.info(f'Clicking a button on a previous screen')
#                     retrieved_element.click()

#                 logging.info(f'Element matched and clicked')
#                 #sleep for one second to enable the driver to load the new content
#                 time.sleep(1)

#         #Check now after clicking on the button
#         if Helper.navigation_status(driver) == "same":
#             consents_screen_matched = True

#         #Update current screen fingerprint
#         current_screen_fingerprint = Helper.fingerprinting_screen(driver)

#     return consents_screen_matched


def go_find_consents_ui_screen(driver):
    """Discovers consents UI screen using systematic exploration with LLM guidance"""
    visited_elements = []
    current_screen_page_source_xpaths = None
    start_time = time.time()
    time_limit = (tracker.time_limit * 60) #tracker.time_limit default = 30 
    elapsed_time = 0

    while not tracker.consents_ui_found and elapsed_time < time_limit:
        current_time = time.time()
        elapsed_time = current_time - start_time
        logging.info(f'Minutes elapsed: {round( (elapsed_time / 60), 2)}, minutes limit: {round( (time_limit / 60), 2)}')

        logging.info('Checking current screen with the LLM...')
        # Capture and process screenshot
        screenshot_png = driver.get_screenshot_as_png()
        ss_filename = f"path_to_consents_ui_screenshot_{tracker.screenshot_counter}.png"

        first_or_second_screen_decider = LLM.LLM_first_second_layer_decider(driver.page_source)
        

        # Check for consents UI match
        if "FIRST" in first_or_second_screen_decider:
            first_layer_filename = "first_layer_screenshot.png"
            Image_processor.save_png_image(screenshot_png, Helper.get_current_app_results_folder_name(), f"{first_layer_filename}")

        elif "SECOND" in first_or_second_screen_decider:
            second_layer_filename = "second_layer_screenshot.png"
            Image_processor.save_png_image(screenshot_png, Helper.get_current_app_results_folder_name(), f"{second_layer_filename}")
            tracker.consents_ui_second_layer_screenshot = screenshot_png
            _handle_consents_ui_found(driver, visited_elements)
            break

        else:
            current_screen_page_source_xpaths = Helper.extract_enabled_elements_xpaths(driver)
            element = LLM.openAI_query_page_source_pick_element(current_screen_page_source_xpaths)
            if element:
                chosen_el = driver.find_element(By.XPATH, element)
                _process_top_element(driver, chosen_el, element, screenshot_png, ss_filename, visited_elements)
            else:
                logging.info(f'Got None from LLM, skipping this iteration...')
                continue

        #increment
        tracker.screenshot_counter += 1

    logging.info(f'Terminating the script as the time exceeded {time_limit/60} mins.')
    sys.exit(1)




# Helper methods for internal processing

def _handle_consents_ui_found(driver, visited_elements):
    """Processes consents UI discovery"""
    tracker.consents_ui_found = True
    tracker.consents_ui_fingerprint.append(Helper.fingerprinting_cmp_screen(driver))
    tracker.consents_screen_statics_xpaths = Helper.get_all_static_text_xpaths(driver)
    paths_context.cmp_ui_path = paths_context.current_path
    print(f'cmp_ui_path set to {Helper.print_path_details(paths_context.cmp_ui_path)}')
    print(f'consents_screen_statics_xpaths set to the following:\n{tracker.consents_screen_statics_xpaths}')
    LLMGCF.consents_ui_processing(driver, visited_elements)


def _process_top_element(driver, element, chosen_xpath, screenshot_png, filename, visited_elements):
    """Processes and clicks the highest priority element"""

    # I'm not checking the element.is_displayed() because of the case where an element is down below in the tableview
    if not element.is_enabled():
        logging.info(f"Skipping non-interactable element: {element.get_attribute('name')}")
        return

    # Update tracking information
    current_screen_fingerprint = Helper.fingerprinting_screen(driver)
    current_screen_element_clicked_xpath = chosen_xpath
    current_screen_static_texts = Helper.get_all_static_text_xpaths(driver)
    current_screen = ScreenClicked(current_screen_fingerprint, current_screen_element_clicked_xpath, current_screen_static_texts)
    paths_context.current_path.append(current_screen)

    print(f'New screen static texts added with #{len(current_screen.static_texts)} of static texts')
    print(f'total count of previous screens {len(paths_context.current_path)}')
    for screen in paths_context.current_path:
        print(f'{screen.element_clicked_xpath}')


    element_desc = Helper.element_desc_as_string(element)
    logging.info(f"Clicking on element: {element_desc}")
    visited_elements.append(element_desc)

    # Process visual documentation
    Image_processor.highlight_element(
        screenshot_png, element,
        Helper.get_current_app_results_folder_name(),
        filename
    )

    # Perform interaction
    # in case the element is a button -> use click()
    # otherwise -> tap
    Helper.center_element_on_screen(driver, element)
    if element.get_attribute("type") == "XCUIElementTypeButton":
        logging.info('Interacting with the element using click()')
        element.click()

    else:
        Helper.tap_on(driver, element)


    time.sleep(3)
    #make sure we always stay in the app
    if Helper.do_we_leave_the_app(driver):
        Helper.get_back_to_the_app(driver)



def _process_outer_screen_reached(driver, button_desc, button_label, screenshot_filename, navigation_status):
    screenshot_as_png = driver.get_screenshot_as_png()
    inner_screenshot_filename = f"inner_{tracker.inner_screenshot_counter}.png"


    if navigation_status == "navigated_back":
        navigation_label = "exit"

    elif navigation_status == "same":
        navigation_label = "no_navigation"

    elif navigation_status == "still_same":
        navigation_label = "new_element_appear"

    else:
        navigation_label = inner_screenshot_filename

    current_element_dict = DictElement()
    current_element_dict.name = button_desc
    current_element_dict.label = button_label
    current_element_dict.navigation = navigation_label
    current_screen_dict = DictScreen()
    current_screen_dict.label = screenshot_filename
    current_screen_dict.elements = current_element_dict.__dict__

    tracker.output_dic[screenshot_filename] = current_screen_dict.__dict__
    tracker.inner_consents_ui_connections.append( f"{screenshot_filename} > {inner_screenshot_filename}")
    tracker.inner_consents_ui_screenshots_pngs.extend([screenshot_filename, inner_screenshot_filename])

    Image_processor.save_png_image(screenshot_as_png, Helper.get_current_app_results_folder_name(),
                                   inner_screenshot_filename)

def _cleanup_resources(dropbox_path):
    """Handles resource cleanup"""
    try:
        Image_processor.delete_from_dropbox(dropbox_path)
    except Exception as e:
        logging.warning(f"Failed to clean up resources: {str(e)}")