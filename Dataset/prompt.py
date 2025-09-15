prompt_1 = '''
    System Prompt:
    This app makes use of 5 third-party SDKs (or partners). The full list of these SDKs (or partners) are XX, XX, and XXX.

    User Prompt:
    Each time you analyze one provided image's UI, other UI screens (images) or clickchains (navigation) do not affect your judgment for this analysis.

    Below is a UI posted by the consent management platform (CMP) of the app. Check if the UI is in the CMP initial layers (i.e., does the UI provide an overall description?).If yes, check if the UI discloses the number of SDKs (or partners) used by the app. If yes, compare this disclosed number with the actual number of SDKs (or partners) being used. Report an error if there is a mismatch. 
    Hint:  The CMP initial layer refers to the first interface presented to users when they visit an app that requires consent for data processing. This layer typically provides a high-level overview of data collection practices and user choices before accessing more detailed settings.

'''
    

prompt_2 = '''
   Below is a UI posted by the consent management platform (CMP) of the app. Check if the UI displays the purposes of SDKs (or partners, or cookies), such as strictly necessary (or essential), functional, ads, analytics, marketing, performance, targeting, social media, and optimization, etc. If yes, Check if any of the purposes other than strictly necessary (or essential) are set as non-configurable. For example, the purpose accompanied by a checkbox whose state could not be changed, or accompanied by a text indicating “always active” is non-configurable.  But if the necessary/essential purpose of SDKs (or partners, or cookies) is non-configurable, it is compliance 
    Hint: non-configurable means that users cannot disable, modify, or opt out of a certain feature or setting, and they are forced to accept it

    Each time, you should independently analyze a single image (all images need to be analyzed). Each result is independent and does not affect others. Answer 'yes' if at least one result shows this, otherwise answer 'no'.
    Only report an issue if you can confirm or detect the issue with high confidence. The report should include Rule 2.1: (1) Binary result: If this violates the rule, answer "Yes"(At least one "yes", answer yes) or "No."(2) explanations(point which UI violates rules lead to answer "yes")
'''
    

prompt_3 = '''
    Below is a UI posted by the consent management platform (CMP) of the app. Analyze the text, buttons and other UI elements of the UI, and detect whether there are any semantically misleading UI elements. For example, “ok” sometimes can mean “accept” or “reject”, and hence “ok” can be considered misleading in some cases. 
   
    Each time, you should independently analyze a single image (all images need to be analyzed). Each result is independent and does not affect others. Answer 'yes' if at least one result shows this, otherwise answer 'no'.
    Only report an issue if you can confirm or detect the issue with high confidence. The report should include Rule 2.3: (1) Binary result: If this violates the rule, answer "Yes"(At least one "yes", answer yes) or "No."(2) explanations(point which UI violates rules lead to answer "yes")
'''


prompt_4 = '''
    User Prompt:    
    Analyze the information of the above UI screenshots and navigations, and report conflicting information. For example, the text displayed between UIs is not consistent with each other. 
    You only need to answer yes if there is a conflict between the description of the same content or other behaviors on different interfaces, otherwise answer no.

    If you found UI contains partners/vendors/SDK name, please count the total number of different name partners/vendors/SDK number in all UIs. And compared the number with its disclosed number of partners/vendors/SDK.
    Only report an issue if there is a clear and specific conflict. If the initial description lacked details but was later clarified with more details, it does not indicate a rule violation.

    Only report an issue if you can confirm or detect the issue with high confidence. The report should include Rule 2.2: (1) Binary result: If this violates the rule, answer "Yes" or "No."(2) explanations

'''

prompt_5 = '''
    User Prompt:
    Analyze the navigations between the CMP UI screenshots, and identify if there are any navigation frictions which make it difficult for users to express their consent or decline on the CMP UI. For example, navigation frictions manifest when the button users click indicates the following UIs could not be configured while they are indeed configurable. 
    For example, in a UI, there may be a function labeled as non-configurable. However, if you discover that you can actually configure something by clicking into deeper layers (e.g., second, third, etc.), this means the app violates its stated rule.
    Hint: non-configurable means that users cannot disable, modify, or opt out of a certain feature or setting, and they are forced to accept it

   You should only consider the UI related to the clicked button and its corresponding functionality (focus on just one, without considering other features on the same page). 
   If the button is associated with a non-interactive state (e.g., marked as "Always Active" or similar indicators), but after clicking, the user navigates to a screen where the state is changeable, answer **"Yes"**. In all other cases, answer **"No"**. 
    Each time, you should independently analyze a navigation that includes two UI images (all navigations need to be analyzed). Each result is independent and does not affect others. Answer 'yes' if at least one result shows this, otherwise answer 'no'. You do not need to consider images that do not appear in the navigation.

     You only give one overall answer(There is at least one violation of the rule answer yes, otherwise no): Only report an issue if you can confirm or detect the issue with high confidence. The report should include Rule 2.4: (1) Binary result: If this violates the rule, answer "Yes" or "No."(2) explanations
   
'''


prompt_6 = '''
    User Prompt:
    You should first translate all info into english and then analyze.
    Analyze the navigations between the CMP UI screenshots, and identify if there are any UIs that allow users to make changes (e.g., through checkbox) while there are no explicit “save” or “confirm my choice” options to commit the changes. 
    For example, a UI may have a button that navigates to an SDK list UI, allowing users to configure each SDK individually. However, if this UI only has an button such as “Accept” to exit the banner and no other buttons to record user operations in either this UI or the SDK list UI, it violates the rule.
    For example, if a UI has a button labeled "Confirm", "Save", "Submit", etc., which navigates to the next UI, and the next UI does not have a button that allows exiting the CMP banner, then this UI follows the rule. In this case, you should answer "No".
    
    Each time, you should independently analyze a navigation that includes two UI images (all navigations need to be analyzed). Each result is independent and does not affect others. Answer 'yes' if at least one result shows this, otherwise answer 'no'. You do not need to consider images that do not appear in the navigation.
    
    Steps:
        Examine the initial UI in the navigation path:  
        1. If a button labeled "Confirm," "Save," "Submit," etc., is found, immediately answer "No" and do not analyze further in this navigation. No further investigation and step is needed for this path. go to next navigation
        2. If no "Confirm," "Save," "Submit," etc. button is found, proceed to the next UI in the navigation path. Look for the same types of buttons.
        3. If you find a "Confirm," "Save," "Submit," etc. button at any point in the navigation path, answer "No" and stop analyzing this path.
        4. If no "Confirm," "Save," "Submit," etc. buttons are found in any of the UIs in the navigation path, answer "Yes".


    Only report an issue if you can confirm with high confidence that no "Confirm," "Save," or "Submit" button exists anywhere in the navigation path.

    You only give one overall answer(There is at least one violation of the rule answer yes, otherwise no): Be sure to analyze the entire navigation path, and detect if there are no such commit options on the whole path. Only report an issue if you can confirm or detect the issue with high confidence. The report should include Rule 2.5: (1) Binary result: If this violates the rule, answer "Yes" or "No."(2) explanations
'''

prompt_over = '''
    System Prompt:
    You are an app UI analysis expert. You will be provided with the below information regarding the use of consent management platforms (CMPs) in an app:
    CMP UI Screenshots: A list of CMP UI screenshots including the UI(image) name and related URL.
    CMP UI Navigations: A list of UI events indicating an UI action, and source and destination of the UI action. 

    For example, the below UI screenshots and navigations indicate that users can click xxx button on image1, which leads to the rendering of image2. 
    CMP UI Screenshots [(“image_1”, “https://”), (“image_1”, “https://”)]
    CMP UI Navigations  [(“image1”, “click xxx button”, “image2”)]
    ['"file1_name" click button: “Text” --> "file2_name"', etc]. This mean ["In the file1_name UI, when the user clicks the button labeled 'Text', they will be navigated to the file2_name UI.", etc.

    You should follow the order to answer below question.
'''

# Rule: Timing
prompt_7 = '''
You are an app UI analysis expert.
Analyze the provided images, which show the UI before reaching the Consent Management Platform (CMP). 
Determine whether the software can be used normally before the Consent Management Platform (CMP) appears.
If the software is functional and the user can perform actions before encountering the CMP, respond with "yes"; otherwise, respond with "no."

 You only give one overall answer:
 The answer should include Rule 4: (1) Binary result: If this violates the rule, answer "Yes" or "No."(2) explanations
'''
