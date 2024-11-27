import time
import threading
import pyautogui
import pytesseract
from PIL import ImageGrab
import numpy as np
import cv2

# Global variables to track user activity and synchronization
user_is_active = False
last_movement_time = time.time()
idle_threshold = 10  # Time in seconds after which user is considered inactive
lock = threading.Lock()
running = True
debug_print = False  # Add debug print flag

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def get_configuration():
    """
    Gets reference text position and button positions relative to it.
    Returns tuple of (reference_text, text_pos, relative_positions)
    """
    reference_text = "transbordo"
    # # Get reference text
    # reference_text = input("Enter the text to look for on screen: ")
    # input("Make sure the text is visible on screen and press Enter...")
    
    text_pos = find_text_on_screen(reference_text)

    if not text_pos:
        raise Exception("Reference text not found on screen!")
    print(f"Reference text found at: {text_pos}")
    
    # Get button positions and calculate relative positions
    relative_positions = [(-362, -247), (-362, -230)]

    if len(relative_positions) < 2:
        for i in range(2):
            input(f"Move the mouse to button {i+1} and press Enter...")
            button_pos = pyautogui.position()
            # Calculate relative offset from text position
            relative_pos = (button_pos[0] - text_pos[0], button_pos[1] - text_pos[1])
            relative_positions.append(relative_pos)
            print(f"Button {i+1} relative position: {relative_pos}")
    
    return reference_text, text_pos, relative_positions


def find_text_on_screen(search_text):
    """
    Finds the position of specific text on screen using OCR.
    Returns the center coordinates of the found text or None if not found.
    """
    screenshot = ImageGrab.grab()
    # Convert to numpy array for processing
    screenshot_np = np.array(screenshot)
    
    # Convert to grayscale
    gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)
    
    # Apply adaptive thresholding to handle different lighting conditions
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,  # Block size
        2    # C constant
    )
    
    # Optional: Apply slight blur to reduce noise
    denoised = cv2.GaussianBlur(binary, (3,3), 0)
    
    # Debug: Save processed image
    if debug_print:
        cv2.imwrite('processed_screenshot.png', denoised)
    
    # Get OCR data with bounding boxes
    data = pytesseract.image_to_data(denoised, output_type=pytesseract.Output.DICT)
    
    for i, text in enumerate(data['text']):
        if search_text.lower() in text.lower():
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            # Return center position of the text
            return (x + w//2, y + h//2)
    return None

def check_mouse_position():
    """
    Continuously checks mouse position using pyautogui instead of pynput
    """
    global user_is_active, last_movement_time, running
    last_position = pyautogui.position()
    
    while running:
        current_position = pyautogui.position()
        if current_position != last_position:
            with lock:
                user_is_active = True
                last_movement_time = time.time()
            if debug_print:
                print(f"Mouse movement detected at {current_position}")
        last_position = current_position
        time.sleep(0.1)  # Small delay to prevent high CPU usage

def automated_clicks(config_data):
    """
    Performs automated clicks based on reference text position.
    """
    global user_is_active, last_movement_time, running
    reference_text, _, relative_positions = config_data
    
    while running:
        with lock:
            active = user_is_active
            last_move = last_movement_time
        
        current_time = time.time()
        if current_time - last_move > idle_threshold:
            with lock:
                user_is_active = False
                print(f"User inactive for {current_time - last_move:.1f} seconds")
        
        if not user_is_active:
            
            # Find current text position
            text_pos = find_text_on_screen(reference_text)
            if text_pos:
                # Store original mouse position
                original_position = pyautogui.position()
                
                # Calculate and perform clicks based on relative positions
                for rel_pos in relative_positions:
                    click_x = text_pos[0] + rel_pos[0]
                    click_y = text_pos[1] + rel_pos[1]
                    print(f"Performing automated clicks at {click_x}, {click_y}")
                    try:
                        pyautogui.click(click_x, click_y)
                    except pyautogui.FailSafeException:
                        print("Failsafe triggered - mouse in corner")
                    except Exception as e:
                        print(f"Click failed: {e}")
                    time.sleep(0.5)
                
                # Return mouse to original position
                try:
                    pyautogui.moveTo(original_position.x, original_position.y)
                except Exception as e:
                    print(f"Failed to return mouse to original position: {e}")
                
                time.sleep(10)
            else:
                print("Reference text not found, waiting...")
                time.sleep(5)
        else:
            if debug_print:
                print("User is active, waiting...")
            time.sleep(1)

def main():
    # Get the positions of the buttons to click
    config_data = get_configuration()
    time.sleep(2)
    
    # Start the position checker instead of pynput listener
    threading.Thread(target=check_mouse_position, daemon=True).start()
    
    # Start the automated clicks in a separate thread
    threading.Thread(target=automated_clicks, args=(config_data,), daemon=True).start()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        global running
        running = False
        print("\nExiting...")

if __name__ == '__main__':
    main()
