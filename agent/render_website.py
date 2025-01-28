from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from PIL import Image
import time

def render_website_to_image(url, output_path):
    # Set up the web driver (ensure chromedriver is in your PATH)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)

    try:
        # Open the URL
        driver.get(url)
        
        # Wait for the page to load completely
        time.sleep(5)
        
        # Get the dimensions of the page
        total_width = driver.execute_script("return document.body.scrollWidth")
        total_height = driver.execute_script("return document.body.scrollHeight")
        
        # Set the window size to the dimensions of the page
        driver.set_window_size(total_width, total_height)
        
        # Take a screenshot and save it as a PNG file
        screenshot_path = output_path.replace('.jpg', '.png')
        driver.save_screenshot(screenshot_path)
        
        # Convert the PNG file to a JPG file
        image = Image.open(screenshot_path)
        rgb_image = image.convert('RGB')
        rgb_image.save(output_path, 'JPEG')
        
    finally:
        driver.quit()

if __name__ == "__main__":
    url = "https://www.example.com"
    output_path = "website_render.jpg"
    render_website_to_image(url, output_path)
