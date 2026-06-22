import cv2
import mediapipe as mp
import numpy as np
import os
import time
import pandas as pd
from config import DATA_DIR, EXERCISES, FEEDBACK_MAP, KEY_MAP_LABELS, CAMERA_ID

# Initialize Mediapipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

def get_counts(current_mode):
    if not current_mode:
        return {}
    mode_dir = os.path.join(DATA_DIR, current_mode)
    if not os.path.exists(mode_dir):
        return {}
    
    counts = {}
    for filename in os.listdir(mode_dir):
        if filename.endswith(".csv"):
            # Filename format: {current_mode}_{current_label}_{timestamp}.csv
            parts = filename.split('_')
            if len(parts) >= 2:
                try:
                    label = int(parts[1])
                    counts[label] = counts.get(label, 0) + 1
                except:
                    continue
    return counts

def extract_landmarks(results):
    if not results.pose_landmarks:
        return None
    landmarks = []
    for lm in results.pose_landmarks.landmark:
        landmarks.extend([lm.x, lm.y, lm.z, lm.visibility])
    return landmarks

def main():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    cap = cv2.VideoCapture(CAMERA_ID)
    
    current_mode = None
    is_recording = False
    recorded_frames = []
    current_label = None
    label_counts = {}
    
    print("--- Data Collection Started ---")
    print("Press 'P' for Pushup mode, 'S' for Squat mode, 'B' for BicepCurl, 'L' for LateralRaise, 'R' for BentOverRow.")
    print("Press 'Q' to quit.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.flip(frame, 1)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = pose.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('p'):
            current_mode = 'Pushup'
            label_counts = get_counts(current_mode)
            print(f"Mode set to: {current_mode}")
        elif key == ord('s'):
            current_mode = 'Squat'
            label_counts = get_counts(current_mode)
            print(f"Mode set to: {current_mode}")
        elif key == ord('b'):
            current_mode = 'BicepCurl'
            label_counts = get_counts(current_mode)
            print(f"Mode set to: {current_mode}")
        elif key == ord('l'):
            current_mode = 'LateralRaise'
            label_counts = get_counts(current_mode)
            print(f"Mode set to: {current_mode}")
        elif key == ord('r'):
            current_mode = 'BentOverRow'
            label_counts = get_counts(current_mode)
            print(f"Mode set to: {current_mode}")
            
        if current_mode:
            key_char = chr(key).upper()
            if key_char in KEY_MAP_LABELS:
                is_recording = True
                current_label = KEY_MAP_LABELS[key_char]
                recorded_frames = []
                print(f"Started recording {current_mode} - Label: {FEEDBACK_MAP[current_mode][current_label]} ({current_label})")
            
            if key == ord(' '):
                if is_recording:
                    is_recording = False
                    print(f"Stopped recording. Saving {len(recorded_frames)} frames...")
                    
                    if len(recorded_frames) > 0:
                        mode_dir = os.path.join(DATA_DIR, current_mode)
                        if not os.path.exists(mode_dir):
                            os.makedirs(mode_dir)
                            
                        timestamp = int(time.time())
                        filename = f"{current_mode}_{current_label}_{timestamp}.csv"
                        filepath = os.path.join(mode_dir, filename)
                        
                        columns = ['label']
                        for i in range(33):
                            columns.extend([f'x{i}', f'y{i}', f'z{i}', f'v{i}'])
                            
                        df = pd.DataFrame(recorded_frames, columns=columns)
                        df.to_csv(filepath, index=False)
                        print(f"Saved to {filepath}")
                        # Update counts after saving
                        label_counts = get_counts(current_mode)
                    
                    recorded_frames = []
                    current_label = None

        if is_recording:
            landmarks = extract_landmarks(results)
            if landmarks:
                row = [current_label] + landmarks
                recorded_frames.append(row)
                
            cv2.putText(image, f"RECORDING: {FEEDBACK_MAP[current_mode][current_label]}", 
                        (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

        # Display info
        mode_text = f"Mode: {current_mode if current_mode else 'None (P:Push, S:Squat, B:Curl, L:Lateral, R:Row)'}"
        cv2.putText(image, mode_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        
        if current_mode:
            instructions = "Press C: Correct, 1/2/3: Errors. Space to STOP."
            cv2.putText(image, instructions, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
            
            # Display counts for each label
            y_offset = 120
            cv2.putText(image, "Counts:", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
            for l_idx, l_name in FEEDBACK_MAP[current_mode].items():
                y_offset += 25
                count = label_counts.get(l_idx, 0)
                color = (255, 255, 255)
                if count < 20: color = (0, 0, 255) # Red if low
                elif count < 40: color = (0, 255, 255) # Yellow if ok
                else: color = (0, 255, 0) # Green if high
                
                txt = f"{l_name}: {count}"
                cv2.putText(image, txt, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)

        cv2.imshow('Data Collection', image)

    cap.release()
    cv2.destroyAllWindows()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
