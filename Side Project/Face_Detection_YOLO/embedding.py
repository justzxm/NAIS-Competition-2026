import cv2
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1

device = "cuda" if torch.cuda.is_available() else "cpu"
model = InceptionResnetV1(pretrained="vggface2").eval().to(device)

def get_embedding(wajah_bgr):
    img = cv2.cvtColor(wajah_bgr, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (160, 160))
    t = torch.from_numpy(img).permute(2, 0, 1).float()
    t = (t - 127.5) / 128.0
    with torch.no_grad():
        emb = model(t.unsqueeze(0).to(device))[0].cpu().numpy()
    return emb / np.linalg.norm(emb)