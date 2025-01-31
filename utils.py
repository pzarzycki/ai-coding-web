import os
import markdown2
import base64
from io import BytesIO
from PIL import Image

def markdown_to_html(markdown_text):
    """
    Convert Markdown text to HTML.
    
    :param markdown_text: A string containing Markdown formatted text.
    :return: A string containing the converted HTML.
    """
    html = markdown2.markdown(markdown_text, extras=["code-friendly", "fenced-code-blocks", "latex", ])
    return html

def b64_encode_image(image: Image, format='jpeg') -> str:
    """
    Converts a PIL image to a Base64-encoded string.
    :param image: A PIL Image object.
    :return: Base64-encoded image string.
    """

    assert format in ['jpeg', 'png'], "Image format must be 'jpeg' or 'png'."

    buffer = BytesIO()
    image.save(buffer, format=format.upper())  # serialize the image to a in-memory file-like object
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/{format};base64,{base64_image}"


def scan_directory(directory):
    def list_files(dir_path, prefix=""):
        tree_str = ""
        items = sorted(os.listdir(dir_path))
        for i, item in enumerate(items):
            if item.startswith('.') or item == '__pycache__':
                continue
            path = os.path.join(dir_path, item)
            connector = "└─ " if i == len(items) - 1 else "├─ "
            tree_str += f"{prefix}{connector}{item}/\n" if os.path.isdir(path) else f"{prefix}{connector}{item}\n"
            if os.path.isdir(path):
                extension = "    " if i == len(items) - 1 else "│   "
                tree_str += list_files(path, prefix + extension)
        return tree_str

    return ".\n" + list_files(directory)