import matplotlib.pyplot as plt
import pandas as pd
import cv2
import numpy as np
import seaborn as sns

#Die Map wird hier geladen. Weitere Kommentare zur Map in "plot_positions.py".
map_image = cv2.imread("map12.png")
map_image = cv2.cvtColor(map_image, cv2.COLOR_BGR2RGB)
map_height, map_width, _ = map_image.shape

#Ich greif auf die .csv Datei zu, bzw. lese sie
df = pd.read_csv("player_positions.csv")

#Sogennantes 'normalizen' der Map Position. Hiermit hatte ich einige Probleme, die ich mit Hilfe von trial & error und Stackoverflow lösen konnte. 
def normalize_position(x, y):
    norm_x = x / 15000 * map_width
    norm_y = (15000 - y) / 15000 * map_height  #Ich weiß nicht warum, aber die Map wurde mir dauernd auf der Y-Achse gespiegelt angezeigt. Deswegen hab ich sie hier gespiegelt, damit die Spiegelung wieder rückgängig gemacht wird.
    return norm_x, norm_y


df["x_position"], df["y_position"] = zip(*df.apply(lambda row: normalize_position(row["x_position"], row["y_position"]), axis=1))

#Die Heatmap-Matrix 
heatmap_matrix = np.zeros((map_height, map_width))

for _, row in df.iterrows():
    x, y = int(row["x_position"]), int(row["y_position"])
    heatmap_matrix[y, x] += 1  # Ensure integer indices

#Gaussian Blur, damit die Heatmap, bzw. die Übergänge weicher sind.
heatmap_matrix = cv2.GaussianBlur(heatmap_matrix, (201, 201), 55)


heatmap_matrix = heatmap_matrix / np.max(heatmap_matrix)

#'Plotten' der Heatmap
fig, ax = plt.subplots(figsize=(10, 10))
ax.imshow(np.flipud(map_image), extent=[0, map_width, 0, map_height])  # ✅ Flip image vertically to match LoL map

#Hiermit habe ich die Transparenz der Heatmap bestimmen können. 
sns.heatmap(heatmap_matrix, cmap="viridis", alpha=0.3, ax=ax)

ax.collections[-1].colorbar.remove()

#Die X- und Y-Achsen habe ich entfernt, da sie in der Abbildung nicht notwendig sind. 
ax.set_xticks([])
ax.set_yticks([])

plt.savefig("MATCH3_heatmap_viridis.png", transparent=True)

#plt.show()
