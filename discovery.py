import os
import requests
import csv
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("YOUTUBE_API_KEY")

queries = [
    "AI tools",
    "AI productivity",
    "machine learning",
    "Python programming",
    "coding",
    "developer tools",
    "software development",
    "tech reviews",
    "gadgets",
    "artificial intelligence"
]

def search_channels(query):
    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "part": "snippet",
        "q": query,
        "type": "channel",
        "maxResults": 50,
        "key": api_key
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print("Search failed:", response.status_code)
        return []

    return response.json().get("items", [])

all_channels = []

for query in queries:
    results = search_channels(query)
    all_channels.extend(results)

unique_channels = {}

for item in all_channels:
    channel_id = item["id"]["channelId"]
    unique_channels[channel_id] = item

all_channels = list(unique_channels.values())

print("Total unique channels:", len(all_channels))

channel_ids = [
    item["id"]["channelId"]
    for item in all_channels
]

channel_url = "https://www.googleapis.com/youtube/v3/channels"

channel_data = []

for i in range(0, len(channel_ids), 50):
    batch = channel_ids[i:i + 50]

    channel_params = {
        "part": "snippet,statistics",
        "id": ",".join(batch),
        "key": api_key
    }

    response = requests.get(channel_url, params=channel_params)

    if response.status_code != 200:
        print("Channel request failed:", response.status_code)
        continue

    data = response.json()
    channel_data.extend(data.get("items", []))

qualified = []
rejected = []

for channel in channel_data:
    name = channel["snippet"]["title"]
    description = channel["snippet"].get("description", "")
    channel_id = channel["id"]

    statistics = channel.get("statistics", {})

    subscribers = int(statistics.get("subscriberCount", 0))
    views = int(statistics.get("viewCount", 0))
    videos = int(statistics.get("videoCount", 0))

    if 5000 <= subscribers <= 100000:
        status = "Qualified"
        reason = "Meets subscriber criteria"

        qualified.append({
            "channel_id": channel_id,
            "name": name,
            "description": description,
            "subscribers": subscribers,
            "views": views,
            "videos": videos,
            "status": status,
            "reason": reason
        })
    else:
        status = "Rejected"

        if subscribers < 5000:
            reason = "Below 5K subscribers"
        else:
            reason = "Above 100K subscribers"

        rejected.append({
            "channel_id": channel_id,
            "name": name,
            "description": description,
            "subscribers": subscribers,
            "views": views,
            "videos": videos,
            "status": status,
            "reason": reason
        })

print()
print("Total channel data:", len(channel_data))
print("Qualified:", len(qualified))
print("Rejected:", len(rejected))
print()

for creator in qualified:
    print("Name:", creator["name"])
    print("Subscribers:", creator["subscribers"])
    print("Status:", creator["status"])
    print("Reason:", creator["reason"])
    print("Channel ID:", creator["channel_id"])
    print()
    import csv

with open("qualified_influencers.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=[
            "channel_id",
            "name",
            "description",
            "subscribers",
            "views",
            "videos",
            "status",
            "reason"
        ]
    )

    writer.writeheader()
    writer.writerows(qualified)

print("Saved qualified influencers:", len(qualified))