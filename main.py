import os
import requests
import json
import csv
from dotenv import load_dotenv

#Der API Key wird aus dem environment geladen. Die .env File werde ich aus Privatsschutzgründen nicht mit hochladen, da der API Key unter anderem privat ist. 
load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")

#Ich speichere alle BASE_URLS, aber ich benutze nur die für "europe". Anfangs war die Überlegung da, z.B. European Gameplay Movement mit dem aus den USA zu vergleichen. Dazu kam ich aber nicht.
BASE_URLS = {
    "routing": {
        "americas": "https://americas.api.riotgames.com",
        "europe": "https://europe.api.riotgames.com",
        "asia": "https://asia.api.riotgames.com",
        "sea": "https://sea.api.riotgames.com",
    }
}

def send_request(endpoint, region_type, region):
    headers = {"X-Riot-Token": API_KEY}
    base_url = BASE_URLS[region_type][region]
    response = requests.get(base_url + endpoint, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None
#Hier geh ich auf die einzelnen Endpoints ein.
def get_summoner_info(game_name, tag_line, region="europe"):
    endpoint = f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    return send_request(endpoint, region_type="routing", region=region)

def get_match_history(puuid, region="europe"):
    endpoint = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
    return send_request(endpoint, region_type="routing", region=region)

def get_match_details(match_id, region="europe"):
    endpoint = f"/lol/match/v5/matches/{match_id}"
    return send_request(endpoint, region_type="routing", region=region)

def get_match_timeline(match_id, region="europe"):
    endpoint = f"/lol/match/v5/matches/{match_id}/timeline"
    return send_request(endpoint, region_type="routing", region=region)

def save_player_positions_to_csv(match_id, match_timeline, match_details, filename="player_positions.csv"):
    if 'info' not in match_timeline or 'frames' not in match_timeline['info']:
        print("Error: 'info' or 'frames' key not found in match timeline data.")
        return
    
    #'Participant ID' mit 'Champion ID' verbinden
    participant_champions = {}
    for participant in match_details.get("info", {}).get("participants", []):
        participant_champions[participant["participantId"]] = {
            "champion_name": participant["championName"],
            "champion_id": participant["championId"]
        }

    with open(filename, mode='w', newline='') as csvfile:
        fieldnames = ['match_id', 'participant_id', 'champion_name', 'champion_id', 'timestamp', 'x_position', 'y_position']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        #Das Fetchen der Positions
        for frame in match_timeline['info']['frames']:
            timestamp = frame['timestamp']  

            for participant_id, participant in frame.get('participantFrames', {}).items():
                if 'position' in participant:
                    x_position = participant['position']['x']
                    y_position = participant['position']['y']

                    #Die Champion Info (Name und ID) werden hier gespeichert, damit ich später damit weiterarbeiten kann. Das ist wichtig, da nicht alle Champions mit ihrem richtigen Namen gespeichert werden. 
                    #Der Champion "Wukong" wird zum Beispiel im Code als "MonkeyKing" gespeichert!
                    champion_info = participant_champions.get(int(participant_id), {'champion_name': 'Unknown', 'champion_id': None})
                    champion_name = champion_info['champion_name']
                    champion_id = champion_info['champion_id']

                    #Erstellen der .CSV-Datei
                    writer.writerow({
                        'match_id': match_id, 
                        'participant_id': participant_id,
                        'champion_name': champion_name,
                        'champion_id': champion_id,
                        'timestamp': timestamp,
                        'x_position': x_position,
                        'y_position': y_position
                    })
#Der Abschnitt unten sind die Prompts. Leider ist es nicht möglich, sowas auf der Website auszugeben, da man dafür einen RSO (Riot Sign On) API Endpoint braucht. 
if __name__ == "__main__":

    game_name = input("Enter the summoner's game name (e.g., PlayerName): ").strip()
    tag_line = input("Enter the summoner's tag line (e.g., 1234): ").strip()
    region = "europe"
#Aus Gewohnheit hab ich die player info "summoner" genannt. Vor kurzer Zeit hat sich Riot entschieden, ein neues Identifikationssystem zu implementieren. Vorher hießen League of Legends User "Summoner".
    summoner_info = get_summoner_info(game_name, tag_line, region)

    if summoner_info:
        print("\nSummoner Info:")
        print(json.dumps(summoner_info, indent=4))

        puuid = summoner_info.get("puuid")
        if puuid:
            match_history = get_match_history(puuid, region)
            print("\nMatch History:")
            print(json.dumps(match_history, indent=4))

            if match_history:
                match_id = match_history[0] 
                match_details = get_match_details(match_id, region)
                print(f"Details for match {match_id}:")
                print(json.dumps(match_details, indent=4))

              
                match_timeline = get_match_timeline(match_id, region)
                if match_timeline:
                    print(f"Timeline for match {match_id}:")
                    save_player_positions_to_csv(match_id, match_timeline, match_details) 

        else:
            print("Failed to retrieve match history!")
    else:
        print("Failed to retrieve summoner/player info!")
