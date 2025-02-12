import cv2
import dlib
import pyttsx3
import numpy as np
from ultralytics import YOLO
import time
import logging
logging.getLogger("ultralytics").setLevel(logging.WARNING)  # Hides unnecessary info

# Function to compute eye aspect ratio (optional for blinking detection)
def eye_aspect_ratio(eye):
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    return (A + B) / (2.0 * C)

# Function to get the eye region from facial landmarks
def get_eye_region(landmarks, eye_indices):
    return np.array([(landmarks.part(i).x, landmarks.part(i).y) for i in eye_indices], np.int32)

# Function to determine gaze direction
def get_gaze_direction(eye):
    # Compute bounding box
    x_min, y_min = np.min(eye, axis=0)
    x_max, y_max = np.max(eye, axis=0)

    eye_roi = gray[y_min:y_max, x_min:x_max]  # Extract eye region
    _, threshold_eye = cv2.threshold(eye_roi, 55, 255, cv2.THRESH_BINARY_INV)  # Threshold to isolate iris

    # Find contours in threshold image
    contours, _ = cv2.findContours(threshold_eye, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        return "Unknown"

    # Get the largest contour (iris)
    contour = max(contours, key=cv2.contourArea)
    M = cv2.moments(contour)
    
    if M["m00"] == 0:
        return "Unknown"
    
    cx = int(M["m10"] / M["m00"])  # Center of the contour
    eye_width = x_max - x_min
  
    # # Determine direction based on iris position for 3 parts
    # if cx < eye_width // 3:
    #     return "Left"
    # elif cx > 2 * eye_width // 3:
    #     return "Right"
    # else:
    #     return "Center"
    
    # Divide the eye into 5 parts
    left_most = eye_width // 5  # 1/5 of the eye width (first segment)
    left_mid = 2 * eye_width // 5  # 2/5 of the eye width (second segment)
    right_mid = 3 * eye_width // 5  # 3/5 of the eye width (fourth segment)
    right_most = 4 * eye_width // 5  # 4/5 of the eye width (fifth segment)

    # Determine gaze direction based on iris position for 5 parts
    if cx < left_mid:  # Leftmost two sections
        return "Left"
    elif cx > right_mid:  # Rightmost two sections
        return "Right"
    else:  # Center section
        return "Center"
    

# Load dlib's face detector and facial landmark predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

# Load YOLO model (lightweight version)
model = YOLO("yolov8n.pt", verbose=False)  # Suppresses model logging # YOLOv8 Nano (smallest model)

# Start webcam
cap = cv2.VideoCapture(0)

cap.set(3, 640)  # Width
cap.set(4, 480)  # Height

# Store previous direction to avoid repeated prints
prev_direction = None
engine=pyttsx3.init()
continous_right=0
continous_left=0
continous_eye_left=0
continous_eye_right=0

frame_skip = 3  # Process every 3rd frame to reduce CPU usage
frame_count = 0

# Timers to prevent rapid repeated warnings
last_warning_time = 0
warning_interval = 4  # Minimum gap between two warnings (in seconds)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_count += 1
    if frame_count % frame_skip != 0:  # Skip frames to reduce processing load
        continue
    
    frame=cv2.flip(frame,1)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)
    
    current_time = time.time()  # Get the current time

    #Face detection warnings
    if(len(faces)==0) and (current_time - last_warning_time) > warning_interval:
        engine.say("Warning, No face detected.")
        engine.runAndWait()
        last_warning_time = current_time
        continue
    if len(faces)>1 and (current_time - last_warning_time) > warning_interval:
        engine.say("Warning Multiple faces detected.")
        engine.runAndWait()
        last_warning_time = current_time
        continue
        
    # Perform object detection with lower confidence threshold
    results = model(frame, conf=0.5, device="cpu")  # Use CPU with lower confidence
    # Check if a phone is detected
    detected_objects = [model.names[int(box.cls)] for box in results[0].boxes]
    if "cell phone" in detected_objects and (current_time - last_warning_time) > warning_interval:
        print("Phone Detected")
        engine.say("Warning! Phone detected")
        engine.runAndWait()
        last_warning_time = current_time
        continue
    # Show only if necessary
    # cv2.imshow("Phone Detection", results[0].plot())
    
    for face in faces:
        landmarks = predictor(gray, face)

        # Extract key landmark points
        nose = (landmarks.part(30).x, landmarks.part(30).y)  # Nose tip
        face_center_x = (face.left() + face.right()) // 2
        face_center_y = (face.top() + face.bottom()) // 2
        # print('(',face_center_x,face_center_y,')',end=" ")
        
        # Get left and right eye regions
        left_eye = get_eye_region(landmarks, [36, 37, 38, 39, 40, 41])
        right_eye = get_eye_region(landmarks, [42, 43, 44, 45, 46, 47])

        direction = None  # Default to None
        # print('(',nose[0],nose[1],')')     
        
        # Draw eye landmarks
        # cv2.polylines(frame, [left_eye], True, (0, 255, 0), 1)
        # cv2.polylines(frame, [right_eye], True, (0, 255, 0), 1
        
        # Determine left or right movement
        if nose[0] < face_center_x - 10:
            direction = "Turned Left"
            continous_left+=1
            continous_right=0      
        elif nose[0] > face_center_x + 10:
            direction = "Turned Right"
            continous_right+=1      
            continous_left=0      
        else:
            prev_direction=None
            continous_left=0      
            continous_right=0      
        # # Determine up or down movementq
        # if nose[1] < face_center_y - 20:
        #     direction = "Turned Up"
        # elif nose[1] > face_center_y + 20:
        #     direction = "Turned Down"

        # Print only if the direction has changed
        if direction and direction != prev_direction:
            # print(direction)
            prev_direction = direction  # Update previous direction
        if continous_left>4 and (current_time - last_warning_time) > warning_interval:
            continous_eye_right=0
            continous_eye_left=0
            print('turned left')
            engine.say("Warning turned left")
            engine.runAndWait()
            last_warning_time = current_time
            continue

        if continous_right>4 and (current_time - last_warning_time) > warning_interval:
            continous_eye_right=0
            continous_eye_left=0
            print('turned right')
            engine.say("Warning turned right")
            engine.runAndWait()
            last_warning_time = current_time
            continue
 
        # Draw face landmarks (optional for visualization)
        # for i in range(68):
        #     x, y = landmarks.part(i).x, landmarks.part(i).y
        #     cv2.circle(frame, (x, y), 1, (0, 255, 255), -1)
        

        # Determine gaze direction
        left_gaze = get_gaze_direction(left_eye)
        right_gaze = get_gaze_direction(right_eye)

        # Print gaze direction if both eyes agree
        if left_gaze == right_gaze=='Center':
            continous_eye_left=0
            continous_eye_right=0
            # print(f"Eye Direction: {left_gaze}")
            continue
        elif left_gaze == right_gaze=='Left':
            # print(f"Eye Direction: {left_gaze}")
            continous_eye_right=0
            continous_eye_left+=1
        elif left_gaze == right_gaze=='Right':
            # print(f"Eye Direction: {left_gaze}")
            continous_eye_right+=1
            continous_eye_left=0
        
        if continous_eye_left>4 and (current_time - last_warning_time) > warning_interval:
            print("Looking left")
            engine.say("Warning looking left")
            engine.runAndWait()
            last_warning_time = current_time
            continue
        if continous_eye_right>4 and (current_time - last_warning_time) > warning_interval:
            print("Looking right")
            engine.say("Warning looking right")
            engine.runAndWait()
            last_warning_time = current_time
            continue


    cv2.imshow("Face Direction Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()