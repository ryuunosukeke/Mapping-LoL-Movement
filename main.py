import os
import requests
import json
import csv
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")

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

def save_player_positions_to_csv(match_timeline, match_details, filename="player_positions.csv"):
    if 'info' not in match_timeline or 'frames' not in match_timeline['info']:
        print("Error: 'info' or 'frames' key not found in match timeline data.")
        return
    
   
    participant_champions = {}
    for participant in match_details.get("info", {}).get("participants", []):
        participant_champions[participant["participantId"]] = participant["championName"]

    with open(filename, mode='w', newline='') as csvfile:
        fieldnames = ['participant_id', 'champion', 'timestamp', 'x_position', 'y_position']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

     
        for frame in match_timeline['info']['frames']:
            timestamp = frame['timestamp']  

     
            for participant_id, participant in frame.get('participantFrames', {}).items():
                if 'position' in participant:
               
                    x_position = participant['position']['x']
                    y_position = participant['position']['y']

                    champion_name = participant_champions.get(int(participant_id), 'Unknown Champion')

             
                    writer.writerow({
                        'participant_id': participant_id,
                        'champion': champion_name,
                        'timestamp': timestamp,
                        'x_position': x_position,
                        'y_position': y_position
                    })
    
    print(f"Player positions have been saved to {filename}.")

if __name__ == "__main__":

    game_name = input("Enter the summoner's game name (e.g., PlayerName): ").strip()
    tag_line = input("Enter the summoner's tag line (e.g., 1234): ").strip()
    region = "europe"

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
                    save_player_positions_to_csv(match_timeline, match_details) 
        else:
            print("Failed to retrieve match history!")
    else:
        print("Failed to retrieve summoner info!")
