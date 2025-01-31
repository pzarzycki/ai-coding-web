from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from PIL import Image
import time
from io import BytesIO



def render_website_to_image(url, format='JPEG'):
    """
    Renders a website to an image.
    This function uses a headless Chrome browser to open the given URL, 
    captures a screenshot of the entire page, and returns it as a PIL.Image object.
    Args:
        url (str): The URL of the website to render.
    Returns:
        PIL.Image.Image: An image object containing the screenshot of the website.
    """
    # Set up the web driver (ensure chromedriver is in your PATH)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)

    try:
        # Open the URL
        driver.get(url)
        
        # Wait for the page to load completely
        driver.implicitly_wait(1)
        driver.execute_script("return document.readyState") == "complete"
        
        # Get the dimensions of the page
        total_width = driver.execute_script("return document.body.scrollWidth")
        total_height = driver.execute_script("return document.body.scrollHeight")
        
        # Set the window size to the dimensions of the page
        driver.set_window_size(total_width, total_height)
        
        # Take a screenshot and save it to a memory stream
        screenshot = driver.get_screenshot_as_png()
        image = Image.open(BytesIO(screenshot))
        
        # Save the PNG image to a memory stream
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format=format)
        img_byte_arr.seek(0)
        
        return Image.open(img_byte_arr).convert("RGB")
    finally:
        driver.quit()

