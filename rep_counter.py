import numpy as np
from config import FEEDBACK_MAP

def calculate_angle(a, b, c):
    """Calculates the 2D angle between three points (b is the vertex)"""
    a = np.array([a.x, a.y])
    b = np.array([b.x, b.y])
    c = np.array([c.x, c.y])
    
    ba = a - b
    bc = c - b
    
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    
    return np.degrees(angle)

class RepCounter:
    def __init__(self):
        self.stage = None
        self.correct_reps = 0
        self.incorrect_reps = 0
        self.current_rep_errors = set()
        self.error_frequencies = {}
        self.current_mode = None

    def reset(self, new_mode):
        self.current_mode = new_mode
        self.stage = None
        self.correct_reps = 0
        self.incorrect_reps = 0
        self.current_rep_errors = set()
        self.error_frequencies = {}

    def get_stats(self):
        return {
            "correct_reps": self.correct_reps,
            "incorrect_reps": self.incorrect_reps,
            "error_frequencies": self.error_frequencies
        }

    def _complete_rep(self):
        if len(self.current_rep_errors) > 0:
            self.incorrect_reps += 1
            for err in self.current_rep_errors:
                self.error_frequencies[err] = self.error_frequencies.get(err, 0) + 1
        else:
            self.correct_reps += 1
        self.current_rep_errors = set() # Reset for next rep

    def update(self, landmarks, mode, label_idx):
        if mode != self.current_mode:
            self.reset(mode)

        if not landmarks or not mode:
            return

        # If an error is detected at any point, flag the current rep
        if label_idx > 0:
            error_text = FEEDBACK_MAP.get(mode, {}).get(label_idx, "Unknown Error")
            self.current_rep_errors.add(error_text)

        try:
            lm = landmarks.landmark

            # Determine which side is more visible
            left_visibility = (lm[11].visibility + lm[13].visibility + lm[15].visibility + lm[23].visibility + lm[25].visibility + lm[27].visibility) / 6.0
            right_visibility = (lm[12].visibility + lm[14].visibility + lm[16].visibility + lm[24].visibility + lm[26].visibility + lm[28].visibility) / 6.0
            
            # Helper to get the best joint pair based on visibility
            def get_best_joint(left_idx, right_idx):
                return lm[left_idx] if left_visibility > right_visibility else lm[right_idx]

            # Primary joints for angle calculations
            shoulder = get_best_joint(11, 12)
            elbow = get_best_joint(13, 14)
            wrist = get_best_joint(15, 16)
            hip = get_best_joint(23, 24)
            knee = get_best_joint(25, 26)
            ankle = get_best_joint(27, 28)

            if mode == 'Pushup':
                elbow_angle = calculate_angle(shoulder, elbow, wrist)
                if elbow_angle < 90:
                    self.stage = "down"
                if elbow_angle > 160 and self.stage == 'down':
                    self.stage = "up"
                    self._complete_rep()

            elif mode == 'Squat':
                knee_angle = calculate_angle(hip, knee, ankle)
                if knee_angle < 100:
                    self.stage = "down"
                if knee_angle > 160 and self.stage == 'down':
                    self.stage = "up"
                    self._complete_rep()

            elif mode == 'BicepCurl':
                elbow_angle = calculate_angle(shoulder, elbow, wrist)
                if elbow_angle > 150:
                    self.stage = "down"
                if elbow_angle < 60 and self.stage == 'down':
                    self.stage = "up"
                    self._complete_rep()

            elif mode == 'LateralRaise':
                # Track angle between hip, shoulder, and elbow for arm raise
                shoulder_angle = calculate_angle(hip, shoulder, elbow)
                if shoulder_angle < 30:
                    self.stage = "down"
                if shoulder_angle > 80 and self.stage == 'down':
                    self.stage = "up"
                    self._complete_rep()

            elif mode == 'BentOverRow':
                elbow_angle = calculate_angle(shoulder, elbow, wrist)
                if elbow_angle > 150:
                    self.stage = "down"
                if elbow_angle < 90 and self.stage == 'down':
                    self.stage = "up"
                    self._complete_rep()

        except Exception as e:
            print("RepCounter Error:", e)

    def update_squat_heuristic(self, landmarks):
        if self.current_mode != 'Squat':
            self.reset('Squat')

        if not hasattr(self, 'min_knee_angle'):
            self.min_knee_angle = 180
            self.persistent_feedback = "Ready to start."
            self.persistent_label_idx = 0

        feedback = self.persistent_feedback
        label_idx = self.persistent_label_idx

        try:
            lm = landmarks.landmark

            left_visibility = lm[11].visibility + lm[23].visibility + lm[25].visibility + lm[27].visibility
            right_visibility = lm[12].visibility + lm[24].visibility + lm[26].visibility + lm[28].visibility
            
            def get_best(l, r): return lm[l] if left_visibility > right_visibility else lm[r]

            shoulder = get_best(11, 12)
            hip = get_best(23, 24)
            knee = get_best(25, 26)
            ankle = get_best(27, 28)

            knee_angle = calculate_angle(hip, knee, ankle)
            
            # Back angle: angle between Hip-Shoulder and Vertical
            hip_np = np.array([hip.x, hip.y])
            shoulder_np = np.array([shoulder.x, shoulder.y])
            vertical_np = np.array([hip.x, hip.y - 0.5])
            
            v1 = shoulder_np - hip_np
            v2 = vertical_np - hip_np
            cos_theta = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
            back_angle = np.degrees(np.arccos(np.clip(cos_theta, -1.0, 1.0)))

            if back_angle > 45:
                feedback = "Back bending too forward"
                label_idx = 1
                self.current_rep_errors.add(feedback)

            if knee_angle < 140: # Changed from 100 to 140 to catch shallow squats
                self.stage = "down"
            
            if self.stage == 'down':
                self.min_knee_angle = min(self.min_knee_angle, knee_angle)
            
            if knee_angle > 160 and self.stage == 'down':
                self.stage = "up"
                if self.min_knee_angle > 90:
                    self.current_rep_errors.add("Squat too shallow")
                    self.persistent_feedback = "Squat too shallow"
                    self.persistent_label_idx = 2
                else:
                    self.persistent_feedback = "Correct"
                    self.persistent_label_idx = 0
                
                # Feedback updates immediately upon standing
                if feedback != "Back bending too forward":
                    feedback = self.persistent_feedback
                    label_idx = self.persistent_label_idx
                    
                self._complete_rep()
                self.min_knee_angle = 180
                
        except Exception as e:
            print("Squat Heuristic Error:", e)

        return feedback, label_idx
