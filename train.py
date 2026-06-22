import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import os
import argparse
from config import DEVICE, LEARNING_RATE, BATCH_SIZE, EPOCHS, FEEDBACK_MAP
from dataset import PostureDataset
from model import PostureModel, get_pinn_loss

def train_model(exercise_mode):
    print(f"--- Training Model for {exercise_mode} ---")
    
    # Load Dataset
    dataset = PostureDataset(exercise_mode, augment=True) # Enable synthetic noise augmentation
    
    if len(dataset) == 0:
        print(f"No data found for {exercise_mode}. Please run data_collection.py first.")
        return
        
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    # Initialize Model
    num_classes = len(FEEDBACK_MAP[exercise_mode])
    model = PostureModel(num_classes=num_classes).to(DEVICE)
    
    # Loss and Optimizer
    weights = torch.ones(num_classes).to(DEVICE)
    weights[0] = 2.0
    if exercise_mode == 'Squat' and num_classes > 2:
        weights[2] = 5.0 # Heavily penalize missing "Squat too shallow"
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    # Cosine Annealing scheduler to fine-tune weights at the end
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    
    # PINN Loss weight
    lambda_pinn = 0.0001
    
    model.train()
    best_acc = 0.0
    save_dir = "weights"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    save_path = os.path.join(save_dir, f"{exercise_mode}_model.pth")
    
    for epoch in range(EPOCHS):
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        
        for batch_idx, (inputs, labels) in enumerate(dataloader):
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss_cls = criterion(outputs, labels)
            loss_pinn = get_pinn_loss(outputs, inputs)
            loss = loss_cls + lambda_pinn * loss_pinn
            
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
            _, predicted = torch.max(outputs.data, 1)
            total_samples += labels.size(0)
            total_correct += (predicted == labels).sum().item()
            
        scheduler.step() # Update learning rate
        
        epoch_loss = total_loss / len(dataloader)
        epoch_acc = 100 * total_correct / total_samples
        curr_lr = optimizer.param_groups[0]['lr']
        print(f"Epoch [{epoch+1}/{EPOCHS}], Loss: {epoch_loss:.4f}, Accuracy: {epoch_acc:.2f}%, LR: {curr_lr:.6f}")
        
        # Save Best Model logic
        if epoch_acc >= best_acc:
            best_acc = epoch_acc
            torch.save(model.state_dict(), save_path)
            print(f"--> New Best Accuracy! Model saved to {save_path}")

    print(f"Training complete. Best Accuracy: {best_acc:.2f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train Posture Model')
    parser.add_argument('--mode', type=str, choices=['Pushup', 'Squat', 'BicepCurl', 'LateralRaise', 'BentOverRow'], required=True, 
                        help='Exercise mode to train (Pushup, Squat, BicepCurl, LateralRaise, or BentOverRow)')
    args = parser.parse_args()
    
    train_model(args.mode)
