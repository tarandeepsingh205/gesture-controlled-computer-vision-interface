import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import sys

# --- CONFIGURATION ---
PROJECT_NAME = "PROJECT MUDRA: FINAL STABLE"
CAMERA_ID = 0
# Capture Resolution (What camera sees)
CAP_W, CAP_H = 1280, 720 
# Window Resolution (What you see on screen - Big Window)
WINDOW_W, WINDOW_H = 1280, 720

SMOOTHING = 1.3         # Normal movement speed
DRAG_SMOOTHING = 3.0    # Slower, smoother speed for dragging
CLICK_DISTANCE = 30     # Pinch tight to CLICK
RELEASE_DISTANCE = 60   # Open wide to RELEASE
FRAME_REDUCTION = 100   

# --- OPTIMIZATIONS ---
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# Setup Camera
print(f"Connecting to Camera {CAMERA_ID}...")
cap = cv2.VideoCapture(CAMERA_ID)

if not cap.isOpened():
    print("ERROR: Could not open camera.")
    sys.exit()

cap.set(3, CAP_W)
cap.set(4, CAP_H)

# Setup Hand Tracking
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1, 
    model_complexity=0, 
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

screen_w, screen_h = pyautogui.size()
ploc_x, ploc_y = 0, 0
cloc_x, cloc_y = 0, 0
drag_active = False
last_action_time = 0
click_start_pos = None 

# Mode Debounce
current_mode = None
mode_frame_count = 0
MODE_SWITCH_THRESHOLD = 3 

print(f"--- {PROJECT_NAME} STARTED ---")
print("🖐️ 1 Finger: Move")
print("🤏 Pinch Tight: Start Drag")
print("👐 Open Wide: Drop File")
print("✌️ 2 Fingers: Scroll")
print("🤟 3 or 4 Fingers (Thumb IN): Copy")
print("✊ Fist: Paste")
print("🖐️ 5 Fingers (Open Hand): Switch Tabs")

def safe_hotkey(*args):
    try:
        pyautogui.mouseUp() 
        for key in args:
            pyautogui.keyDown(key)
        time.sleep(0.05) 
        for key in reversed(args):
            pyautogui.keyUp(key)
    except Exception as e:
        print(f"Key Error: {e}")

while True:
    try:
        success, img = cap.read()
        if not success: 
            print("Failed to read frame.")
            continue
        
        # Flip logic
        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)
        
        h, w, c = img.shape
        
        # --- DRAW ZONES ---
        cv2.line(img, (0, 80), (w, 80), (0, 0, 255), 2) 
        cv2.line(img, (0, 640), (w, 640), (0, 0, 255), 2) 
        
        cv2.putText(img, "SCROLL UP", (int(w/2)-80, 60), cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 0, 255), 2)
        cv2.putText(img, "SCROLL DOWN", (int(w/2)-100, 700), cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 0, 255), 2)
        cv2.putText(img, "PREV TAB", (20, int(h/2)), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 0), 2)
        cv2.putText(img, "NEXT TAB", (w-150, int(h/2)), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 0), 2)

        if results.multi_hand_landmarks:
            for hand_lms in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
                
                lm_list = []
                for id, lm in enumerate(hand_lms.landmark):
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    lm_list.append([id, cx, cy])

                if len(lm_list) >= 21:
                    x1, y1 = lm_list[8][1:]   # Index
                    x2, y2 = lm_list[12][1:]  # Middle
                    x_thumb, y_thumb = lm_list[4][1:] 
                    palm_x, palm_y = lm_list[0][1], lm_list[0][2]

                    scale_ref = np.hypot(lm_list[5][1] - lm_list[17][1], lm_list[5][2] - lm_list[17][2])
                    if scale_ref == 0: scale_ref = 1

                    fingers = []
                    fingers.append(1 if lm_list[8][2] < lm_list[6][2] else 0)
                    fingers.append(1 if lm_list[12][2] < lm_list[10][2] else 0)
                    fingers.append(1 if lm_list[16][2] < lm_list[14][2] else 0)
                    fingers.append(1 if lm_list[20][2] < lm_list[18][2] else 0)
                    
                    thumb_dist = np.hypot(lm_list[4][1] - lm_list[17][1], lm_list[4][2] - lm_list[17][2])
                    fingers.append(1 if thumb_dist > scale_ref * 1.3 else 0)

                    # --- MODE DETECTION ---
                    detected_mode = "NONE"
                    if fingers[0]==1 and fingers[1]==0 and fingers[2]==0: detected_mode = "MOUSE"
                    elif fingers[0]==1 and fingers[1]==1 and fingers[2]==0: detected_mode = "SCROLL"
                    elif fingers[0]==1 and fingers[1]==1 and fingers[2]==1 and fingers[4]==0: detected_mode = "COPY"
                    elif fingers == [0, 0, 0, 0, 0] or fingers == [0, 0, 0, 0, 1]: detected_mode = "PASTE"
                    elif fingers[0]==1 and fingers[1]==1 and fingers[2]==1 and fingers[3]==1 and fingers[4]==1: detected_mode = "TAB"

                    if detected_mode == current_mode:
                        mode_frame_count += 1
                    else:
                        mode_frame_count = 0
                        current_mode = detected_mode

                    cv2.putText(img, f"MODE: {current_mode}", (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

                    if mode_frame_count > MODE_SWITCH_THRESHOLD:
                        
                        # 1. MOUSE MODE
                        if current_mode == "MOUSE":
                            x3 = np.interp(x1, (FRAME_REDUCTION, w - FRAME_REDUCTION), (0, screen_w))
                            y3 = np.interp(y1, (FRAME_REDUCTION, h - FRAME_REDUCTION), (0, screen_h))

                            dist = np.hypot(x1 - x_thumb, y1 - y_thumb)
                            
                            # --- CLICK & DRAG LOGIC ---
                            if dist < CLICK_DISTANCE:
                                if not drag_active:
                                    # Freeze cursor on initial pinch to prevent jitter
                                    click_start_pos = (x3, y3)
                                    pyautogui.mouseDown()
                                    drag_active = True
                                
                                # Deadzone Logic:
                                # If user pinches and stays within 40px radius, KEEP cursor FROZEN at start pos.
                                # This prevents "up and down" jitter during the click.
                                if click_start_pos:
                                    move_dist = np.hypot(x3 - click_start_pos[0], y3 - click_start_pos[1])
                                    if move_dist < 40:
                                        x3, y3 = click_start_pos # Override position to locked one
                                    else:
                                        click_start_pos = None # User moved far enough, release lock to drag

                                cv2.circle(img, (x1, y1), 15, (0, 255, 0), cv2.FILLED)
                                cv2.putText(img, "DRAG", (x1, y1+30), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
                            
                            elif dist > RELEASE_DISTANCE: 
                                if drag_active:
                                    pyautogui.mouseUp()
                                    drag_active = False
                                    click_start_pos = None
                                cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
                            
                            # Keep 'Green' circle if dragging, even if distance fluctuates slightly
                            elif drag_active:
                                cv2.circle(img, (x1, y1), 15, (0, 255, 0), cv2.FILLED)


                            # --- MOVEMENT ---
                            # Use higher smoothing when dragging to make it feel heavier/controlled
                            current_smooth = DRAG_SMOOTHING if drag_active else SMOOTHING
                            
                            cloc_x = ploc_x + (x3 - ploc_x) / current_smooth
                            cloc_y = ploc_y + (y3 - ploc_y) / current_smooth
                            
                            try: pyautogui.moveTo(cloc_x, cloc_y)
                            except: pass
                            ploc_x, ploc_y = cloc_x, cloc_y

                        # 2. SCROLL
                        elif current_mode == "SCROLL":
                            if drag_active: pyautogui.mouseUp(); drag_active = False
                            if time.time() - last_action_time > 0.1:
                                if y1 < 80: 
                                    pyautogui.scroll(150); last_action_time = time.time()
                                    cv2.putText(img, "UP", (50, 150), cv2.FONT_HERSHEY_PLAIN, 3, (0,255,0), 3)
                                elif y1 > 640: 
                                    pyautogui.scroll(-150); last_action_time = time.time()
                                    cv2.putText(img, "DOWN", (50, 600), cv2.FONT_HERSHEY_PLAIN, 3, (0,255,0), 3)

                        # 3. COPY
                        elif current_mode == "COPY":
                            if time.time() - last_action_time > 1.5:
                                print("Action: Copy")
                                safe_hotkey('ctrl', 'c')
                                cv2.putText(img, "COPY", (200, 200), cv2.FONT_HERSHEY_PLAIN, 4, (0, 255, 255), 4)
                                last_action_time = time.time()

                        # 4. PASTE
                        elif current_mode == "PASTE":
                            if time.time() - last_action_time > 1.5:
                                print("Action: Paste")
                                safe_hotkey('ctrl', 'v')
                                cv2.putText(img, "PASTE", (200, 200), cv2.FONT_HERSHEY_PLAIN, 4, (0, 255, 0), 4)
                                last_action_time = time.time()

                        # 5. TABS
                        elif current_mode == "TAB":
                            cv2.circle(img, (palm_x, palm_y), 20, (0, 255, 255), cv2.FILLED)
                            if time.time() - last_action_time > 0.8:
                                if palm_x < w * 0.25: 
                                    safe_hotkey('ctrl', 'shift', 'tab')
                                    cv2.putText(img, "< PREV TAB", (50, 400), cv2.FONT_HERSHEY_PLAIN, 3, (255,0,0), 3)
                                    last_action_time = time.time()
                                elif palm_x > w * 0.75: 
                                    safe_hotkey('ctrl', 'tab')
                                    cv2.putText(img, "NEXT TAB >", (w-300, 400), cv2.FONT_HERSHEY_PLAIN, 3, (255,0,0), 3)
                                    last_action_time = time.time()

        # Force Window Size (Reliable)
        final_img = cv2.resize(img, (WINDOW_W, WINDOW_H))
        cv2.imshow(PROJECT_NAME, final_img)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    except Exception as e:
        print(f"Error: {e}")
        if drag_active: 
            pyautogui.mouseUp()
            drag_active = False
        continue

cap.release()
cv2.destroyAllWindows()
