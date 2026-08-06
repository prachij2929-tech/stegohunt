#
#
#
mport os
import cv2
import matplotlib.pyplot as plt
from collections import Counter

X = []
y = []

dataset_path = r"C:\caps\Dataset"

if not os.path.exists(dataset_path):
    print("❌ Dataset path NOT found")
    exit()

class_names = ["Cover", "Stego"]

for label, folder in enumerate(class_names):
    folder_path = os.path.join(dataset_path, folder)

    if not os.path.exists(folder_path):
        print(f"❌ Folder missing: {folder_path}")
        continue

    print("📂 Reading:", folder_path)

    for file in os.listdir(folder_path):
        if file.lower().endswith(".pgm"):
            img_path = os.path.join(folder_path, file)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)

            if img is not None:
                X.append(img)
                y.append(label)

print("\n✅ DONE")
print("Total images loaded:", len(X))
print("Total labels created:", len(y))

# -------------------------------
# LABEL COUNT
# -------------------------------
label_counts = Counter(y)
for label_idx, count in label_counts.items():
    print(f"{class_names[label_idx]}: {count} images")

# -------------------------------
# VISUAL CHECK: SHOW SOME IMAGES
# -------------------------------
print("\nShowing 5 sample images with labels...")
fig, axs = plt.subplots(1, 5, figsize=(15,3))

for i in range(5):
    if i >= len(X):  # safety check
        break
    axs[i].imshow(X[i], cmap='gray')
    axs[i].set_title(class_names[y[i]])
    axs[i].axis('off')

plt.show()