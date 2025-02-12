import matplotlib.pyplot as plt
import pandas as pd
import cv2
import os
import numpy as np
import requests
from matplotlib.animation import FuncAnimation
from dotenv import load_dotenv
from matplotlib.animation import FFMpegWriter

#Der API Key und die Match ID. Den API Key muss ich alle 24h erneuern auf: https://developer.riotgames.com/ Die Match ID fetche ich mit "main.py" und adde sie dann in mein .env.
#Anschließen ändere ich unter  os.getenv("MATCH_ID") die Nummer manuell. Bei einer großen Menge an Matches würde ich dies nicht tun, aber bei der kleinen Anzahl ist es okay.

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")
MATCH_ID = os.getenv("MATCH_ID3")

#Bei der Map handelt es sich tatsächlich um "Map12" (von Riot benannt). Ursprünglich wollte ich nur die Minimap verwenden, hab mich aber dann doch anders entschieden. 
map_image = cv2.imread("map12.png")
map_image = cv2.cvtColor(map_image, cv2.COLOR_BGR2RGB)
map_height, map_width, _ = map_image.shape  

df = pd.read_csv("player_positions.csv")
df = df.sort_values(by=["timestamp"])
timestamps = sorted(df["timestamp"].unique())
interp_steps = 20
champion_positions = {}

#Spawn Points für die jeweiligen Teams. Ich weiß leider nicht genau, wo jeder spawnt (da jeder unterschiedliche Koordinaten hat und alle in einem 'Ring' stehen). Ich habe mich also 
#annäherungsweise für 1000 und 14000 entschieden, da die Map 15000x15000 Koordinaten hat. 
blue_team_spawn = (1000, 1000)  
red_team_spawn = (14000, 14000) 

#Hier hab ich versucht die Tode zu tracken. Leider hat das nicht so gut geklappt, um zwischem manuellen Laufen zur Base und/oder dem Tod bzw. eines Recalls zu unterscheiden. 
#Dennoch war das hier später für die Death Heatmap wichtig. Ich habe mich dazu entschieden, das im Code zu lassen. 
deaths = {}  

def fetch_timeline(match_id, api_key):
    url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    headers = {"X-Riot-Token": api_key}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching timeline data: {response.status_code}, Response: {response.text}")
        return None

timeline_data = fetch_timeline(MATCH_ID, API_KEY)

#Für die verschiedenen Events hab ich die 'event types' von Riot durchgelesen, bzw. gefetched. Darunter befinden sich RECALLS, CHAMPION_KILLS und SUMMONER_SPELLS. Wie gesagt, leider 
#hat die Implementierung nicht so geklappt, wie ich mir es vorgestellt habe.
def get_event_flags(): 
    recalls = set()
    deaths = {}  
    kills = set()
    teleports = set()
    
    if not timeline_data:
        return recalls, deaths, kills, teleports
    
    for frame in timeline_data["info"]["frames"]:
        for event in frame["events"]:
            event_type = event["type"]
            timestamp = event.get("timestamp")
            
            if event_type == "RECALL":
                recalls.add((event["participantId"], timestamp))
                print(f"Recall event detected: Participant {event['participantId']} at {timestamp}")
            
            elif event_type == "CHAMPION_KILL": 
                killer_id = event.get("killerId")
                victim_id = event.get("victimId")
                assists = event.get("assistingParticipantIds", [])
                kill_timestamp = timestamp
                kills.add((killer_id, victim_id, kill_timestamp))
                deaths[victim_id] = kill_timestamp  
                print(f"Kill event detected: Killer {killer_id}, Victim {victim_id} at {kill_timestamp}, Assists: {assists}")
            
            elif event_type == "SUMMONER_SPELL" and event.get("spellId") == 4: 
                teleports.add((event["participantId"], timestamp))
                print(f"Teleport event detected: Participant {event['participantId']} at {timestamp}")
    return recalls, deaths, kills, teleports

recalls, deaths, kills, teleports = get_event_flags()

def detect_teleport(champ_id, timestamp):
    if (champ_id, timestamp) in recalls or (champ_id, timestamp) in deaths:
        return True  
    if (champ_id, timestamp) in teleports:
        return True  
    return False 

fig, ax = plt.subplots(figsize=(10, 10))
ax.imshow(map_image, extent=[0, map_width, 0, map_height])
icon_size = 40
champion_images = {}
for champion in df["champion_name"].unique():
    icon_path = os.path.join("icons", f"{champion}.png")
    icon = cv2.imread(icon_path, cv2.IMREAD_UNCHANGED)
    if icon is not None:
        icon_resized = cv2.resize(icon, (icon_size, icon_size))
        icon_resized_rgb = cv2.cvtColor(icon_resized, cv2.COLOR_BGR2RGB)
        champion_images[champion] = icon_resized_rgb

champion_plots = {}

def normalize_position(x, y):
    return x / 15000 * map_width, y / 15000 * map_height

def interpolate_position(start, end, t, teleport=False): #Für das Erstellen der Übergänge. Hier werden zwei Positionen genommen, um daraus eine 3. zu gewinnen. 
    if teleport:
        return end
    t = t * t * (3 - 2 * t)
    return start + (end - start) * t 

def get_closest_row(champion_name, time):
    rows = df[df["champion_name"] == champion_name]
    before = rows[rows["timestamp"] <= time].tail(1)
    after = rows[rows["timestamp"] > time].head(1)
    if not before.empty and not after.empty:
        return before.iloc[0], after.iloc[0]
    elif not before.empty:
        return before.iloc[0], before.iloc[0]
    elif not after.empty:
        return after.iloc[0], after.iloc[0]
    return None, None

def add_team_overlay(icon, team_color, overlay_strength=0.3): #Ein Overlay, damit man zwischen den verschiedenen Teams besser unterscheiden kann. 
    if icon is None:
        return icon
    
    overlay = np.zeros_like(icon, dtype=np.uint8)
    if team_color == 'blue':
        overlay[:] = [0, 0, 150]
    elif team_color == 'red':
        overlay[:] = [150, 0, 0]
    
    icon_with_overlay = cv2.addWeighted(icon, 1 - overlay_strength, overlay, overlay_strength, 0)
    return icon_with_overlay

def handle_death(victim_id, timestamp):
    deaths[victim_id] = timestamp
    print(f"Champion {victim_id} died at {timestamp}") #Dies wird im Terminal ausgegeben. Eigentlich könnte dies auch weggelassen werden, jedoch fand ich es interessant, zu sehen. 

def respawn_victim(victim_id, current_time): #Eigentlich sollten die Champions nach dem Tod wieder in der Base spawnen, bzw. teleporten. Wie schon oben mehrmals erwähnt, klappt das mit meienr Funktion nicht richtig.
    respawn_delay = 10000  
    death_time = deaths.get(victim_id)  
    if death_time and current_time - death_time >= respawn_delay:
        if victim_id <= 5: 
            return normalize_position(blue_team_spawn[0], blue_team_spawn[1])
        else: 
            return normalize_position(red_team_spawn[0], red_team_spawn[1])
    return None  

def update(frame): #Hier werden die einzelnen Frames geupdated/gechecked. 
    real_frame = frame // interp_steps  
    interp_fraction = (frame % interp_steps) / interp_steps  
    if real_frame >= len(timestamps) - 1:
        return []
    current_time = timestamps[real_frame]
    next_time = timestamps[real_frame + 1]
   
    for img in list(champion_plots.values()):
        img.remove()
    champion_plots.clear()
    for champion_name in df["champion_name"].unique():
        row_before, row_after = get_closest_row(champion_name, current_time)
        if row_before is None or row_after is None:
            continue
        start_x, start_y = row_before["x_position"], row_before["y_position"]
        end_x, end_y = row_after["x_position"], row_after["y_position"]
        distance = np.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)
        
        respawn_position = respawn_victim(row_before["participant_id"], current_time)
        if respawn_position:
            print(f"Champion {row_before['participant_id']} respawning at {respawn_position}...")
            start_x, start_y = respawn_position
        teleport = detect_teleport(row_before["participant_id"], current_time)
        start_x, start_y = normalize_position(start_x, start_y)
        end_x, end_y = normalize_position(end_x, end_y)
        x_position = interpolate_position(start_x, end_x, interp_fraction, teleport)
        y_position = interpolate_position(start_y, end_y, interp_fraction, teleport)

        team_color = 'blue' if int(row_before["participant_id"]) <= 5 else 'red'
        icon_with_overlay = add_team_overlay(champion_images[champion_name], team_color)
        img = ax.imshow(icon_with_overlay, extent=[
            x_position - icon_size // 2, x_position + icon_size // 2,
            y_position - icon_size // 2, y_position + icon_size // 2
        ], alpha=0.8)
        
        champion_plots[champion_name] = img
    return list(champion_plots.values())

total_frames = (len(timestamps) - 1) * 20
ani = FuncAnimation(fig, update, frames=total_frames, interval=50, blit=False)
plt.xlim(0, map_width)
plt.ylim(0, map_height)

# Erstellen des Videos und Speichern der Animation
writer = FFMpegWriter(fps=30, metadata=dict(artist='Me'), bitrate=1800)
output_file = "champion_positions_match3.mp4"  
ani.save(output_file, writer=writer, dpi=300)

#plt.show()