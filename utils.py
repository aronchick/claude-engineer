import base64
import io
import re

from PIL import Image


def encode_image_to_base64(image_path):
    try:
        with Image.open(image_path) as img:
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.DEFAULT_STRATEGY)
            if img.mode != "RGB":
                img = img.convert("RGB")
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="JPEG")
            return base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
    except Exception as e:
        return f"Error encoding image: {str(e)}"


def parse_goals(response):
    goals = re.findall(r"Goal \d+: (.+)", response)
    return goals


def execute_goals(goals, chat_function):
    for i, goal in enumerate(goals, 1):
        print(f"Executing Goal {i}: {goal}")
        response, exit_continuation = chat_function(f"Continue working on goal: {goal}")
        if "AUTOMODE_COMPLETE" in response or exit_continuation:
            print("Automode completed.")
            break
