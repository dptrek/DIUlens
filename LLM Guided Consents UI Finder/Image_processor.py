import logging
# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
from PIL import Image, ImageDraw
from io import BytesIO
import Secrets
import requests
import dropbox
import os
import logging
from ContextTracker import tracker


def save_png_image(pngImage, folder_name, image_name):
    folder_name = folder_name
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    # Save the Base64 string to a file in the "screenshots_base64" folder
    file_path = os.path.join(folder_name, image_name)

    # Save the screenshot to a file
    with open(file_path, 'wb') as file:
        file.write(pngImage)

    logging.info(f"Screenshot saved to {file_path}")
    return file_path

def highlight_element(screenshot, element, folder_name, screenshot_filename):
    # Load the screenshot into a Pillow Image
    image = Image.open(BytesIO(screenshot))

    # Get element coordinates and size
    location = element.location
    size = element.size

    # Correct the coordinates
    left = int(location['x'])
    top = int(location['y'])
    right = left + int(size['width'])
    bottom = top + int(size['height'])

    # Scale coordinates for high-DPI devices
    pixel_ratio = 3.0
    left = int(left * pixel_ratio)
    top = int(top * pixel_ratio)
    right = int(right * pixel_ratio)
    bottom = int(bottom * pixel_ratio)

    # Draw a red rectangle around the element
    draw = ImageDraw.Draw(image)
    draw.rectangle([left, top, right, bottom], outline="red", width=5)

    # Convert the image to bytes
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()

    # Save the image
    save_png_image(png_bytes, folder_name, screenshot_filename)

def delete_png_image(folder_name, image_filename):
    file_path = os.path.join(folder_name, image_filename)

    try:
        if os.path.exists(file_path):
            os.remove(file_path)  # Delete the file
            logging.info(f"Deleted file: {file_path}")
        else:
            logging.warning(f"File not found: {file_path}")
    except Exception as e:
        logging.error(f"Error deleting file {file_path}: {e}")

def get_url_fileio_for(screenshot_path):
    logging.info(f"Uploading a screenshot to file.io")
    url = 'https://file.io/'

    image_url = ""
    # Open the file in binary mode
    with open(screenshot_path, "rb") as file:
        # Upload the file
        response = requests.post(url, files={"file": file})
        res = response.json()

        if res["success"] == True:
            image_url = res["link"]
            logging.info(f"Screenshot uploaded successfuly! URL: {image_url}")
        else:
            logging.info(f"Failed uploading the screenshot")

    return image_url

def get_url_dropbox_for(screenshot_filename):
    access_token = Secrets.DROPBOX_ACCESS_KEY

    try:
        # Initialize Dropbox client
        dbx = dropbox.Dropbox(access_token)

        # Open the file and upload
        with open(screenshot_filename, "rb") as file:
            response = dbx.files_upload(file.read(), f"/{screenshot_filename}",
                                        mode=dropbox.files.WriteMode("overwrite"))
            logging.info(f"File uploaded to Dropbox: {screenshot_filename}")

        # Check if a shared link already exists
        shared_links = dbx.sharing_list_shared_links(path=f"/{screenshot_filename}").links
        if shared_links:
            shared_link = shared_links[0].url
            logging.info(f"Reusing existing shared link for {screenshot_filename}")
        else:
            # Create a new shared link
            shared_link_metadata = dbx.sharing_create_shared_link_with_settings(f"/{screenshot_filename}")
            shared_link = shared_link_metadata.url
            logging.info(f"Created new shared link for {screenshot_filename}")

        # Convert shared link to direct download link
        direct_link = shared_link.replace("www.dropbox.com", "dl.dropboxusercontent.com").replace("?dl=0", "")

        logging.info(f"Direct link: {direct_link}")
        return direct_link
    except Exception as e:
        logging.error(f"Error uploading to Dropbox: {e}")
        return None

def delete_from_dropbox(screenshot_filename):
    access_token = Secrets.DROPBOX_ACCESS_KEY

    try:
        # Create Dropbox client
        dbx = dropbox.Dropbox(access_token)

        # Delete the file from Dropbox
        response = dbx.files_delete_v2(f"/{screenshot_filename}")

        if response.metadata:
            logging.info(f"File '{screenshot_filename}' deleted successfully from Dropbox.")
        else:
            logging.error(f"Failed to delete '{screenshot_filename}' from Dropbox.")

    except Exception as e:
        logging.error(f"Error deleting file from Dropbox: {e}")
        return None

def create_connections_between_images(folder_name, screens_connections_filename, output_file="screens_connections_output.png"):

    if len(tracker.inner_consents_ui_screenshots_pngs) == 0:
        logging.info(f"Screens connections file is empty")
        return

    else:
        logging.info(f"Drawing screens connections")

        # Parse the connections from the text file
        connections = []
        screens_connections_file_path = os.path.join(folder_name, screens_connections_filename)
        with open(screens_connections_file_path, "r") as file:
            for line in file:
                src, dest = line.strip().split(" > ")
                connections.append((src, dest))

        # Load all images into a dictionary
        images = {}
        for image_name in tracker.inner_consents_ui_screenshots_pngs:
            try:
                current_image_file_path = os.path.join(folder_name, image_name)
                with Image.open(current_image_file_path) as img:
                    img = img.convert("RGBA")  # Ensure compatibility with PNG
                    images[image_name] = img
            except Exception as e:
                logging.error(f"Error loading image {image_name}: {e}")

        # Adjust space between images
        max_width = max(img.width for img in images.values())
        max_height = max(img.height for img in images.values())
        padding = 300  # Increased padding for better visibility of arrows
        canvas_width = (max_width + padding) * len(images) - padding
        canvas_height = max_height

        # Create a blank canvas
        result = Image.new("RGBA", (canvas_width, canvas_height), "white")

        # Arrange images on the canvas
        positions = {}
        x_offset = 0
        for image_name, img in images.items():
            result.paste(img, (x_offset, 0))
            positions[image_name] = (x_offset + max_width // 2, max_height // 2)  # Center point
            x_offset += max_width + padding

        # Draw arrows based on connections
        draw = ImageDraw.Draw(result)
        arrow_color = "black"
        arrow_width = 8
        for src, dest in connections:
            if src in positions and dest in positions:
                start = positions[src]
                end = positions[dest]
                # Draw line
                draw.line([start, end], fill=arrow_color, width=arrow_width)
                # Draw arrowhead
                arrowhead_size = 25
                direction = (end[0] - start[0], end[1] - start[1])
                norm = (direction[0] ** 2 + direction[1] ** 2) ** 0.5
                unit_dir = (direction[0] / norm, direction[1] / norm)
                perp_dir = (-unit_dir[1], unit_dir[0])  # Perpendicular for arrowhead
                p1 = (end[0] - arrowhead_size * unit_dir[0] + arrowhead_size * perp_dir[0],
                      end[1] - arrowhead_size * unit_dir[1] + arrowhead_size * perp_dir[1])
                p2 = (end[0] - arrowhead_size * unit_dir[0] - arrowhead_size * perp_dir[0],
                      end[1] - arrowhead_size * unit_dir[1] - arrowhead_size * perp_dir[1])
                draw.polygon([end, p1, p2], fill=arrow_color)

        # Convert the image to bytes
        buffer = BytesIO()
        result.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        save_png_image(png_bytes, folder_name, output_file)
        logging.info(f"{output_file} created successfully!")

