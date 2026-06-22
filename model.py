import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from config import POSE_CONNECTIONS, NUM_LANDMARKS

def get_edge_index():
    # Bidirectional edges
    edges = []
    for u, v in POSE_CONNECTIONS:
        edges.append([u, v])
        edges.append([v, u])
    
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    return edge_index

class ST_GCN_Block(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ST_GCN_Block, self).__init__()
        self.gcn = GCNConv(in_channels, out_channels)
        self.tcn = nn.Conv1d(out_channels, out_channels, kernel_size=3, padding=1)
        self.relu = nn.ReLU()

    def forward(self, x, edge_index):
        # x shape: (Batch * Seq_Len, Num_Nodes, In_Channels)
        
        # Spatial Graph Convolution
        x = self.gcn(x, edge_index)
        x = self.relu(x)
        
        # Reshape for Temporal Convolution
        # Need shape: (Batch * Num_Nodes, Channels, Seq_Len)
        # But for simplicity, we treat the sequence as the time dimension.
        # Wait, x is currently (B*T, N, C). 
        # Let's pass it back out as (B, T, N, C) and do TCN in the main model 
        # or do a simple 1D temporal conv across the temporal dimension.
        return x

class PINN_Kinematic_Layer(nn.Module):
    def __init__(self):
        super(PINN_Kinematic_Layer, self).__init__()
        # In a TRUE PINN, we incorporate physical laws into the loss function or layer.
        # Here, we calculate physical constraints like velocity (first derivative) 
        # and acceleration (second derivative) as explicit physics-informed features.
        
    def forward(self, x):
        # x shape: (Batch, Seq_Len, Num_Nodes, Features=3)
        
        # Calculate velocity (dx/dt)
        velocity = torch.zeros_like(x)
        velocity[:, 1:, :, :] = x[:, 1:, :, :] - x[:, :-1, :, :]
        
        # Calculate acceleration (d^2x/dt^2)
        acceleration = torch.zeros_like(x)
        acceleration[:, 2:, :, :] = velocity[:, 2:, :, :] - velocity[:, 1:-1, :, :]
        
        # Combine base coordinates with physical derivatives
        # Output shape: (Batch, Seq_Len, Num_Nodes, Features * 3)
        pinn_features = torch.cat([x, velocity, acceleration], dim=-1)
        return pinn_features

class PostureModel(nn.Module):
    def __init__(self, num_classes, in_features=3, hidden_dim=64):
        super(PostureModel, self).__init__()
        self.hidden_dim = hidden_dim
        
        self.pinn_layer = PINN_Kinematic_Layer()
        # After PINN layer, features are multiplied by 3 (pos, vel, acc)
        pinn_out_features = in_features * 3
        
        # ST-GCN for spatial-temporal graph feature extraction
        self.st_gcn = ST_GCN_Block(pinn_out_features, hidden_dim)
        self.edge_index = get_edge_index()
        
        # Transformer for global temporal attention
        # Combined size: 64 GCN features + 12 biomechanical features = 76
        self.temporal_in_dim = hidden_dim + 12 
        
        self.transformer_encoder = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model=self.temporal_in_dim, nhead=2, batch_first=True),
            num_layers=1
        )
        
        # LSTM for sequential dependency
        self.lstm = nn.LSTM(input_size=self.temporal_in_dim, hidden_size=128, 
                            num_layers=1, batch_first=True)
                            
        # Fully connected for classification
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x):
        # x shape: (Batch, Seq_Len, Features)
        # Features = 99 coordinates + 12 angles = 111
        B, T, F = x.size()
        
        # 1. Separate coordinates and angles
        coords = x[:, :, :99].view(B, T, 33, 3) # (B, T, 33, 3)
        angles = x[:, :, 99:] # (B, T, 12)
        
        # 2. Physics-Informed Kinematic Layer (on coordinates)
        x_pinn = self.pinn_layer(coords) # (B, T, 33, 9)
        
        # 3. ST-GCN Spatial Processing
        x_gcn_in = x_pinn.view(B * T, 33, -1)
        edge_index = self.edge_index.to(x.device)
        x_gcn_out = self.st_gcn(x_gcn_in, edge_index) # (B*T, 33, self.hidden_dim)
        
        # Spatial Pooling
        x_spatial_pooled = torch.mean(x_gcn_out, dim=1) # (B*T, self.hidden_dim)
        x_spatial_seq = x_spatial_pooled.view(B, T, self.hidden_dim) # (B, T, 64)
        
        # 4. Concatenate Biomechanical Angles
        # 64 GCN features + 12 angle features = 76 features
        x_combined = torch.cat([x_spatial_seq, angles], dim=-1) # (B, T, 76)
        
        # 5. Transformer Temporal Modeling
        x_trans = self.transformer_encoder(x_combined) # (B, T, 76)
        
        # 6. LSTM Temporal Modeling
        lstm_out, (hn, cn) = self.lstm(x_trans) # (B, T, 128)
        
        # Take the output of the last time step
        final_temporal_feature = lstm_out[:, -1, :] # (B, 128)
        
        # 7. Classification
        out = self.fc(final_temporal_feature) # (B, num_classes)
        return out

def get_pinn_loss(model_predictions, batch_inputs):
    """
    A custom Physics-Informed Neural Network (PINN) loss function.
    """
    # batch_inputs shape: (B, T, 109)
    # 1. Extract and reshape coordinates (first 99 features)
    B, T, F = batch_inputs.size()
    coords = batch_inputs[:, :, :99].view(B, T, 33, 3) # (B, T, 33, 3)
    
    loss_physics = 0.0
    key_bones = [(11, 13), (13, 15), (12, 14), (14, 16)] # Shoulders to elbows, elbows to wrists
    
    for u, v in key_bones:
        p1 = coords[:, :, u, :] # (B, T, 3)
        p2 = coords[:, :, v, :] # (B, T, 3)
        
        # Distance squared
        bone_length_sq = torch.sum((p1 - p2) ** 2, dim=-1) # (B, T)
        
        # Variance over time for each batch sequence
        variance = torch.var(bone_length_sq, dim=1) # (B,)
        
        loss_physics += torch.mean(variance)
        
    return loss_physics

if __name__ == "__main__":
    # Test model
    model = PostureModel(num_classes=5)
    dummy_input = torch.randn(2, 30, 33, 3) # Batch=2, Seq=30, Nodes=33, Features=3
    output = model(dummy_input)
    print(f"Output shape: {output.shape}")
    
    pinn_loss = get_pinn_loss(output, dummy_input)
    print(f"PINN Loss: {pinn_loss.item()}")
