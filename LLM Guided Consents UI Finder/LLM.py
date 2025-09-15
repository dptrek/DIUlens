import Secrets
from openai import OpenAI
import Helper
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
from ContextTracker import tracker
from ContextTracker import paths_context

def openAI_query(sys_prompt, elements_list_as_string, visited_elements_as_string):

    logging.info(f"Enquiring LLM")
    OpenAI_key = Secrets.OpenAI_KEY
    # Initialize OpenAI client
    client = OpenAI(
        api_key=OpenAI_key,  # Replace with your actual API key
        base_url="https://api.openai.com/v1"  # Update as necessary
    )

    try:
        completion = None

        if visited_elements_as_string != "":
            # Make a completion request
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Here is the list of elements to analyze:\n{elements_list_as_string}"},
                    {"role": "user", "content": f"Filter out these already clicked elements:\n{visited_elements_as_string}"},

                ],
                # model="gpt-4o-mini-2024-07-18",
                model="gpt-4o-2024-08-06",
                # model="gpt-4o-mini",
                timeout=30
            )

        else:
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Here is the list of elements to analyze:\n{elements_list_as_string}"},
                ],
                # model="gpt-4o-mini-2024-07-18",
                model="gpt-4o-2024-08-06",
                # model="gpt-4o-mini",
                timeout=30
            )
        # Extract and return the content of the response
        res = completion.choices[0].message.content
        logging.info(f'Sorted elements by OpenAI:\n{res}')
        return res

    except Exception as e:
        logging.error(f"query_gpt(): An error occured {e}.")
        return None


def openAI_query_page_source_pick_element(current_screen_page_source):

    sys_prompt = f"""
You are a mobile app assistant tasked with identifying the most likely UI element that leads to the user consents screen, as required by TCF (Transparency and Consent Framework) regulations. This screen typically allows users to manage privacy preferences, cookies, or consents.\nYour input is a list of XPaths from the current app screen, extracted via Appium. You must choose only one element from this list—the one most likely to lead to the consents-related screen.
Here is a list of XPaths to pick from:\n{current_screen_page_source}

USE THE FOLLOWING APPROACH:
1. Dismiss popups or alerts by selecting buttons that contain terms like: "No", "Don’t", "Not", "Close", or any button that implies cancellation or dismissal.
2. Handle login/signup screens by selecting options like: "Continue as guest", "Maybe later", "Skip", or similar.
3. Only select elements of the following types: {Helper.get_clickable_elements_types()}.
4. Avoid suggesting any XPath that has already been clicked in the current state (provided in the sequence below)
5. Use the following list of confirmed paths to the CMP UI in other apps as reference patterns to guide your selection:
    - Cookie & Ad Preferences
    - Account -> Privacy Settings 
    - Menu -> About -> Cookies Policy -> Manage your consents
    - Menu -> Settings -> Cookie Settings 
    - Menu -> Settings & Privacy -> Do not sell or share my personal information
    - Menu -> Your Privacy Choices
    - Profile -> Account -> Data Protection -> Cookie Settings 
    - Profile -> Settings -> Data Protection 
    - Profile -> Manage My Consents 
    - Profile -> Cookie Settings 
    - More -> Settings -> Privacy Settings 
    """

    full_prompt = sys_prompt + "\n"

    #Preparing the CURRENT STATE INFO to the prompt
    if len(paths_context.current_path) > 0:
        current_state_info = f"""
CURRENT STATE INFO:
You're currently on the screen:
{paths_context.current_path[-1].element_clicked_xpath}
Sequence of clicks so far:
{Helper.get_all_previous_clicked_elements()}
"""
        full_prompt += current_state_info
        full_prompt += "\n"

    
    #Preparing the RESPONSE FORMAT to the prompt
    response_format = """
RESPONSE FORMAT:
Your response should be as follows:
replace_this_with_an_xpath_from_the_list
Do not add any explanatory text, or punctuation marks, formatting, or backticks."""

    full_prompt += response_format


    logging.info(f"Enquiring LLM")
    OpenAI_key = Secrets.OpenAI_KEY
    # Initialize OpenAI client
    client = OpenAI(
        api_key=OpenAI_key,  # Replace with your actual API key
        base_url="https://api.openai.com/v1"  # Update as necessary
    )

    try:
        # Make a completion request
        completion = client.chat.completions.create(
            messages=[

                {"role": "system", "content": full_prompt},

            ],
            # model="gpt-4o-mini-2024-07-18",
            model="gpt-4o-2024-08-06",
            # model="gpt-4o-mini",
            timeout=30,
            temperature=0.3

        )
        # Extract and return the content of the response
        res = completion.choices[0].message.content
        trimmed_xpath = trim_to_xpath(res)
        logging.info(f'Chosen element by OpenAI:\n{res} after trimming {trimmed_xpath}')
        return trimmed_xpath

    except Exception as e:
        logging.error(f"query_gpt(): An error occurred {e}.")
        return None


def trim_to_xpath(text: str) -> str:
    start_idx = text.find("//")
    if start_idx == -1:
        return text

    # Find the first closing bracket after the XPath starts
    end_idx = text.find("]", start_idx)
    if end_idx == -1:
        return text[start_idx:]  # Return from '//' to the end if no closing bracket

    return text[start_idx:end_idx + 1]  # Include the closing bracket



def openAI_query_page_source_decider(sys_prompt, current_screen_page_source, response_format):

    full_prompt = ""
    full_prompt += sys_prompt + "\n"
    full_prompt += f"Here is the page_source of the current screen:\n{current_screen_page_source}" + "\n"



    logging.info(f"Enquiring LLM")
    last_elements_clicked = ""

    response_format_prompt = f"{response_format}"
    full_prompt += response_format_prompt + "\n"

    if len(paths_context.current_path) > 0:
        last_elements_clicked = f"I'm on the {paths_context.current_path[-1].element_clicked_xpath} screen and I want to navigate to the Consents Screen, which element should I click now? Here is the list of elements clicked so far:\n{Helper.get_all_previous_clicked_elements()}"
        full_prompt += last_elements_clicked + "\n"


    OpenAI_key = Secrets.OpenAI_KEY
    # Initialize OpenAI client
    client = OpenAI(
        api_key=OpenAI_key,  # Replace with your actual API key
        base_url="https://api.openai.com/v1"  # Update as necessary
    )


    try:
        # Make a completion request
        completion = client.chat.completions.create(
            messages=[

                {"role": "system", "content": full_prompt},



            ],
            # model="gpt-4o-mini-2024-07-18",
            model="gpt-4o-2024-08-06",
            # model="gpt-4o-mini",
            timeout=30,
            temperature=0.3

        )
        # Extract and return the content of the response
        res = completion.choices[0].message.content
        return res

    except Exception as e:
        logging.error(f"query_gpt(): An error occurred {e}.")
        return None



# def openAI_query_vision(prompt, image_url):
#     logging.info(f"Enquiring LLM for current screenshot")
#     OpenAI_key = Secrets.OpenAI_KEY
#     # Initialize OpenAI client
#     client = OpenAI(
#         api_key=OpenAI_key,  # Replace with your actual API key
#         base_url="https://api.openai.com/v1"  # Update as necessary
#     )
#
#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {
#                 "role": "user",
#                 "content": [
#                     {"type": "text", "text": prompt},
#                     {
#                         "type": "image_url",
#                         "image_url": {
#                             "url": image_url,
#                         },
#                     },
#                 ],
#             }
#         ],
#         max_tokens=300,
#     )
#
#     res = response.choices[0].message.content
#     return res


def openAI_query_vision(prompt):
    logging.info(f"Enquiring LLM for current screenshot")
    OpenAI_key = Secrets.OpenAI_KEY
    # Initialize OpenAI client
    client = OpenAI(
        api_key=OpenAI_key,  # Replace with your actual API key
        base_url="https://api.openai.com/v1"  # Update as necessary
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        max_tokens=300,
    )

    res = response.choices[0].message.content
    return res


def LLM_first_second_layer_decider(page_source):

    sys_prompt = '''
    You are a mobile app assistant tasked with identifying the exact screen for managing user consents (consents banner), as required by TCF (Transparency and Consent Framework) regulations. This screen is typically associated with managing privacy preferences, cookies, or consents.
    '''

    response_format = f'''
    # RESPONSE #
    
    Your response should be only one of the following three, you must mention FIRST, SECOND or NO: 
    - "FIRST": if the page source represent the first consent screen description provided below.
    - "SECOND": if the page source represent the second consent screen description provided below.
    - "NO": if the page source does not represent either first consent nore second consent screens.
    
    Description of the first screen/layer: {get_first_layer_desc_IAB()}.
    Description of the second screen/layer: {get_second_layer_desc_IAB()}.


    Do not add any explanatory text, or punctuation marks, formatting, or backticks.
    '''
    gpt_res = openAI_query_page_source_decider(sys_prompt, page_source, response_format)


    if 'FIRST' in gpt_res:
        logging.info(f'LLM decision: This is the First CMP Layer')
        return "FIRST"

    elif 'SECOND' in gpt_res:
        logging.info(f'LLM decision: This is the Second CMP Layer')
        return "SECOND"
    else:
        logging.info(f'LLM decision: This is Neither First nor Second CMP Layer')
        return "NO"
    



def get_first_layer_desc():

    return """
    First Layer of the CMP SDK

    The First Layer is the initial screen presented to the user. It is designed to provide a high-level overview of the data collection and processing practices, allowing users to make quick decisions about their consent preferences. Here’s how it typically looks and functions:
    
    # Purpose and Layout #
    
    The First Layer is concise and user-friendly, aiming to capture the user's attention without overwhelming them with too much information.
    It usually includes:
    A short description of the data collection practices.
    Action buttons for users to make quick choices (e.g., "Accept All," "Reject All," or "More Options").
    A privacy policy link for users who want to read more details.
    
    # Key Components #
    
    Header/Title:
    A clear and concise title, such as "Your Privacy Choices" or "We Value Your Privacy."
    
    Description:
    A brief explanation of why the user is seeing this screen, e.g., "We use cookies and similar technologies to improve your experience on our site. You can manage your preferences below."
    
    Action Buttons:
    Accept All: Allows the user to consent to all data collection and processing activities.
    Reject All: Allows the user to deny consent for all non-essential data collection and processing.
    More Options/Customize: Takes the user to the Second Layer for granular control over their preferences.
    
    Privacy Policy Link:
    A link to the full privacy policy for users who want more detailed information.
    
    # Design and Customization #
    
    The First Layer is designed to be visually appealing and consistent with the app or website's branding.
    """

def get_first_layer_desc_IAB():

    return """
    To qualify as the initial (first) layer of the Framework UI, all the following conditions must be met:

    First, scan the screen for any visible, actionable buttons labeled with any of the following:
    "Accept", "Okay", "Approve", “Agree”, or clear variants, and a separate button or link such as "Advanced Settings", "Customise Choices", or similar, that allows users to customize their preferences.

    1. The screen must inform the user that information is stored on and/or accessed from their device, including technologies such as cookies or device identifiers.
    2. It must state that personal data is being processed and describe the nature of the data (e.g., unique identifiers, browsing activity).
    3. It must indicate that third-party Vendors are storing and/or accessing data and processing the user’s personal data, mention the number of Vendors (which may include non-Framework Vendors), and include a link to the full list of named Vendors.
    4. It must list all distinct and separate Purposes for which data is processed, using at least the standardized Purpose and/or Stack names defined in the Framework.
    5. It must include information about any Special Features used by Vendors during data processing.
    6. It should provide information about the consequences of consenting or not consenting, including the ability to withdraw consent at any time.
    7. It must clarify the scope of the consent (e.g., service-specific or group-specific), and if group-specific, include a link to more details about the group.
    8. It must include instructions or a link to resurface the Framework UI in order to withdraw or modify consent later.
    9. It should indicate if any Vendors are relying on legitimate interest instead of consent, inform the user of their right to object, and link to the relevant section of the UI that provides more information on this type of processing.
    
    # Key Components #

    Action Buttons:
    The screen must include at least one visible and actionable button labeled:

    “Accept”, “Okay”, “Approve”, or a similar term — that captures user consent.
    It must also include a separate visible and actionable element labeled:
    “Advanced Settings”, “Customise Choices”, or similar — that allows users to access detailed consent options.

    """

def get_second_layer_desc():

    return """
    Second Layer of the CMP SDK

    The Second Layer is the detailed screen where users can manage their consent preferences granularly. It typically includes:
    
    Toggle switches for enabling/disabling specific data processing purposes (e.g., analytics, advertising, personalization).
    Vendor lists showing which third parties are involved in data processing.
    It must have Accept/Reject/Save/Confirm/Done/Update or similar buttons to apply the user's choices.
    """

def get_second_layer_desc_IAB():
    return """
    To qualify as a second layer, all the following conditions must be met:

    First, scan the screen for any visible, actionable buttons labeled with any of the following:
    "Accept", "Reject", "Save", "Confirm", "Done", "Update" — or clear variants.

    1. The screen provides detailed vendor-level information, including:
        - List of named Vendors with links to their privacy policies
        - Their associated Purposes, Special Purposes, Features, Special Features
        - Legal Bases, data retention periods, and categories of data collected
        - The user can review all standard Purposes, Special Purposes, Features, and Special Features, with names, descriptions, and possibly illustrations
    2. The screen allows granular and specific user choices:
        - Could be per Vendor 
        - Could be per Purpose i.e. Analytics, Advertising, Performance
    3. It contains clear information about:
        - Processing based on legitimate interest and the right to object
        - Consequences of consenting or not consenting
        - Vendor storage durations and refresh behavior

    # Key Components #

    Action Buttons:
    The screen must include at least one visible and actionable button labeled:
        - “Accept”, “Reject”, “Save”, “Confirm”, “Done”, “Update” — or a similar term — that directly applies or finalizes user consent choices.
    """


