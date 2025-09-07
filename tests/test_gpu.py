import torch
import time

print("CUDA disponible:", torch.cuda.is_available())
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")
print("cuDNN disponible:", torch.backends.cudnn.is_available())
print("Versión cuDNN:", torch.backends.cudnn.version())

# Multiplicación de matrices grandes para medir aceleración
size = 5000
a = torch.rand(size, size, device="cuda")
b = torch.rand(size, size, device="cuda")

torch.cuda.synchronize()
start = time.time()
c = torch.mm(a, b)  # multiplicación de matrices en GPU
torch.cuda.synchronize()
end = time.time()

print(f"⏱ Tiempo en GPU: {end - start:.4f} segundos")
