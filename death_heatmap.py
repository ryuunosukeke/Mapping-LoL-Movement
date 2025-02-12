import os
import json
import requests
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import cv2
from dotenv import load_dotenv

#Da ich diese Heatmap nach "heatmap.py" erstellt habe, war der Ablauf für mich hier einfacher. Vieles war einfach copy paste, weswegen ich den Code auch nicht so detailliert kommentieren werde. 
#Die meisten Kommentare befinden sich in "heatmap.py".
load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")
MATCH_ID = os.getenv("MATCH_ID3")  

#Anders als bei der anderen Heatmap, lese ich "Player_positions.csv" nicht ein, da sie mir keine Informationen über Kills und Deaths gibt.

map_image = cv2.imread("map12.png")
map_image = cv2.cvtColor(map_image, cv2.COLOR_BGR2RGB)
map_height, map_width, _ = map_image.shape  

def fetch_match_timeline(match_id, api_key):
  
    url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    headers = {"X-Riot-Token": api_key}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching timeline data: {response.status_code}, Response: {response.text}")
        return None

def extract_death_positions(timeline_data):
    death_positions = []

    if not timeline_data:
        print("No timeline data available.")
        return death_positions

    for frame in timeline_data["info"]["frames"]:
        for event in frame["events"]:
            if event["type"] == "CHAMPION_KILL":
                victim_id = event["victimId"]
                position = event.get("position", None)
                if position:
                    death_positions.append((position["x"], position["y"]))

    return death_positions

def normalize_position(x, y):
    return (x / 15000) * map_width, (y / 15000) * map_height

def generate_heatmap_matrix(death_positions, map_width, map_height):
    heatmap_matrix = np.zeros((map_height, map_width)) 

  
    for x, y in death_positions:
        x_pos, y_pos = normalize_position(x, y)  
        x_pos, y_pos = int(x_pos), int(y_pos)
        if 0 <= x_pos < map_width and 0 <= y_pos < map_height:
            heatmap_matrix[y_pos, x_pos] += 1  

    heatmap_matrix = cv2.GaussianBlur(heatmap_matrix, (201, 201), 55)

    heatmap_matrix = heatmap_matrix / np.max(heatmap_matrix)

    return heatmap_matrix

def plot_heatmap(heatmap_matrix, map_image):
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(map_image, extent=[0, map_width, 0, map_height])

    ax.imshow(heatmap_matrix, cmap="viridis", alpha=0.3, extent=[0, map_width, 0, map_height])

    ax.set_xticks([])
    ax.set_yticks([])

    plt.savefig("MATCH3_DEATHheatmap_viridis.png", transparent=True)
    plt.show()

if __name__ == "__main__":
    #Ich fetche die Timeline für den nächsten Schritt.
    timeline_data = fetch_match_timeline(MATCH_ID, API_KEY)

    #Ich extrahiere die Positionen der Tode von der timeline. 
    death_positions = extract_death_positions(timeline_data)


    heatmap_matrix = generate_heatmap_matrix(death_positions, map_width, map_height)

    plot_heatmap(heatmap_matrix, map_image)

