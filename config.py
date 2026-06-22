import torch

# General Configuration
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DATA_DIR = "dataset"
WINDOW_SIZE = 30  # Number of frames in a sequence
FPS = 15
CAMERA_ID = 0  # 0 for internal, 1 or 2 for external USB webcams

# Mediapipe configuration
# We will use 33 landmarks from mediapipe pose
NUM_LANDMARKS = 33
NUM_FEATURES = 3 # x, y, z

# Exercise Modes
EXERCISES = {
    'P': 'Pushup',
    'S': 'Squat',
    'B': 'BicepCurl',
    'L': 'LateralRaise',
    'R': 'BentOverRow'
}

# Labels and feedback map
# 0 is always correct. Others are specific errors.
FEEDBACK_MAP = {
    'Pushup': {
        0: "Correct",
        1: "Back not straight",
        2: "Hips too low",
        3: "Hips too high",
        4: "Not deep enough"
    },
    'Squat': {
        0: "Correct",
        1: "Back bending too forward",
        2: "Squat too shallow"
    },
    'BicepCurl': {
        0: "Correct",
        1: "Using momentum (swinging)",
        2: "Partial range of motion",
        3: "Elbows flared/moved"
    },
    'LateralRaise': {
        0: "Correct",
        1: "Raising too high",
        2: "Raising too low"
    },
    'BentOverRow': {
        0: "Correct",
        1: "Back rounded",
        2: "Standing too upright",
        3: "Partial range (elbows low)"
    }
}

# Key mapping for data collection
KEY_MAP_LABELS = {
    'C': 0, # Correct
    '1': 1, # Error 1
    '2': 2, # Error 2
    '3': 3, # Error 3
    '4': 4  # Error 4
}

# Model Hyperparameters
HIDDEN_DIM = 64
NUM_LAYERS = 2
LEARNING_RATE = 0.001
BATCH_SIZE = 32
EPOCHS = 50

# Graph configuration for ST-GCN
# Mediapipe pose connections
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (27, 29), (27, 31), (29, 31),
    (24, 26), (26, 28), (28, 30), (28, 32), (30, 32)
]


# Mapping of specific errors to the connections (bones) that should be highlighted in red
ERROR_CONNECTIONS = {
    'Pushup': {
        1: [(11, 23), (12, 24), (23, 24)], # Back not straight (spine/hips)
        2: [(11, 23), (12, 24), (23, 25), (24, 26)], # Hips too low
        3: [(11, 23), (12, 24), (23, 25), (24, 26)], # Hips too high
        4: [(11, 13), (12, 14), (13, 15), (14, 16)], # Not deep enough (arms)
    },
    'Squat': {
        1: [(11, 23), (12, 24)], # Back bending too forward (spine)
        2: [(23, 25), (24, 26), (25, 27), (26, 28)], # Squat too shallow (legs)
    },
    'BicepCurl': {
        1: [(11, 23), (12, 24)], # Swinging (back/spine movement)
        2: [(11, 13), (12, 14), (13, 15), (14, 16)], # Partial range (arms)
        3: [(11, 13), (12, 14)], # Elbows moved (shoulders)
    },
    'LateralRaise': {
        1: [(11, 13), (12, 14), (13, 15), (14, 16)], # Raising too high (arms)
        2: [(11, 13), (12, 14), (13, 15), (14, 16)], # Raising too low (arms)
    },
    'BentOverRow': {
        1: [(11, 23), (12, 24)], # Back rounded (spine)
        2: [(11, 23), (12, 24), (23, 25), (24, 26)], # Standing too upright (spine/hips)
        3: [(11, 13), (12, 14), (13, 15), (14, 16)], # Partial range (arms)
    }
}
