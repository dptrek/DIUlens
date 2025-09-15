from appium import webdriver
from PIL import Image

#TODO: Implement the history paths
class ContextTracker:
    def __init__(self, platform:str, driver:webdriver, time_limit:int, app_name:str, app_label:str, bundle_id:str, 
                 last_element_clicked_desc:str, consents_ui_elements_clicked_xpaths:list[str], 
                 consents_ui_elements_clicked_descs:list[str], accept_reject_confirm_elements_descs:list[str], non_accept_reject_confirm_elements_descs:list[str], 
                 consents_screen_statics_xpaths:list[str], screenshot_counter:int, inner_screenshot_counter:int, current_swipe_counter:int,
                 inner_consents_ui_connections:list[str], inner_consents_ui_screenshots_pngs:list[str], consents_ui_found:bool, 
                 second_consents_reached_through_first_screen:int, consents_ui_fingerprint, consents_ui_second_layer_screenshot:Image, 
                 consent_ui_previous_screens_clicked, output_dic):
        
        self.platform = platform
        self.driver = driver
        self.time_limit = time_limit
        self.app_name = app_name
        self.app_label = app_label
        self.bundle_id = bundle_id
        self.last_element_clicked_desc = last_element_clicked_desc
        self.consents_ui_elements_clicked_xpaths = consents_ui_elements_clicked_xpaths
        self.consents_ui_elements_clicked_descs = consents_ui_elements_clicked_descs
        self.accept_reject_confirm_elements_descs = accept_reject_confirm_elements_descs
        self.non_accept_reject_confirm_elements_descs = non_accept_reject_confirm_elements_descs
        self.consents_screen_statics_xpaths = consents_screen_statics_xpaths
        self.screenshot_counter = screenshot_counter
        self.inner_screenshot_counter = inner_screenshot_counter
        self.current_swipe_counter = current_swipe_counter
        self.inner_consents_ui_connections = inner_consents_ui_connections
        self.inner_consents_ui_screenshots_pngs = inner_consents_ui_screenshots_pngs
        self.consents_ui_found = consents_ui_found
        self.second_consents_reached_through_first_screen = second_consents_reached_through_first_screen
        self.consents_ui_fingerprint = consents_ui_fingerprint
        self.consents_ui_second_layer_screenshot = consents_ui_second_layer_screenshot
        self.consent_ui_previous_screens_clicked = consent_ui_previous_screens_clicked
        self.output_dic = output_dic


class DictElement:
    def __init__(self):
        self.name = "noNameAssignedYet" #name is the identifier for iOS elements
        self.label = "noLabelAssignedYet"
        self.navigation = "noNavigationAssignedYet"

class DictScreen:
    def __init__(self):
        self.label = "noLabelAssignedYet0"
        self.elements = []


class ScreenClicked:
    def __init__(self, fingerprint, element_clicked_xpath, static_texts):
        self.fingerprint = fingerprint
        self.element_clicked_xpath = element_clicked_xpath
        self.static_texts = static_texts


class PathsContext:
    def __init__(self, current_path, paths_history, cmp_ui_path):
        self.current_path = current_path
        self.paths_history = paths_history
        self.cmp_ui_path = cmp_ui_path

tracker = ContextTracker("",None, 30, "", "",  "",
                         "",
                         [], [],
                         [],[], [],
                         0,0,0,
                         [],[], False,0,
                         [], None, [], {})


paths_context = PathsContext([], [], [])