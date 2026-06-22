import os
import pandas as pd
from collections import Counter

dataset_root = "dataset"
window_size = 30

if os.path.exists(dataset_root):
    for exercise in os.listdir(dataset_root):
        exercise_path = os.path.join(dataset_root, exercise)
        if not os.path.isdir(exercise_path):
            continue
            
        print(f"\n--- Distribution for {exercise} ---")
        counts = Counter()
        file_counts = Counter()
        total_windows = 0
        total_files = 0
        
        for f in os.listdir(exercise_path):
            if f.endswith(".csv"):
                filepath = os.path.join(exercise_path, f)
                df = pd.read_csv(filepath)
                if len(df) >= window_size:
                    label = df['label'].iloc[0]
                    num_windows = len(df) - window_size + 1
                    counts[label] += num_windows
                    file_counts[label] += 1
                    total_windows += num_windows
                    total_files += 1

        print(f"Total files: {total_files}, Total windows: {total_windows}")
        for label, count in sorted(file_counts.items()):
            win_count = counts[label]
            print(f"Label {label}: {count} files | {win_count} windows ({win_count/total_windows*100:.2f}%)")
