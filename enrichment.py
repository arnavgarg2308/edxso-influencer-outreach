import os
import csv
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("YOUTUBE_API_KEY")

input_file = "qualified_influencers.csv"
output_file = "enriched_influencers.csv"

with open(input_file, "r", encoding="utf-8") as file:
    creators = list(csv.DictReader(file))

results = []

for index, creator in enumerate(creators, start=1):
    channel_id = creator["channel_id"]

    print(f"Processing {index}/{len(creators)}: {creator['name']}")

    channel_url = "https://www.googleapis.com/youtube/v3/channels"

    channel_params = {
        "part": "contentDetails",
        "id": channel_id,
        "key": api_key
    }

    response = requests.get(channel_url, params=channel_params)

    if response.status_code != 200:
        print("Channel request failed:", response.status_code)
        continue

    channel_items = response.json().get("items", [])

    if not channel_items:
        continue

    channel = channel_items[0]

    uploads_playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]

    playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"

    playlist_params = {
        "part": "snippet",
        "playlistId": uploads_playlist_id,
        "maxResults": 10,
        "key": api_key
    }

    response = requests.get(playlist_url, params=playlist_params)

    if response.status_code != 200:
        print("Playlist request failed:", response.status_code)
        continue

    videos = response.json().get("items", [])

    video_ids = []
    video_titles = []

    for video in videos:
        video_ids.append(video["snippet"]["resourceId"]["videoId"])
        video_titles.append(video["snippet"]["title"])

    if not video_ids:
        continue

    video_url = "https://www.googleapis.com/youtube/v3/videos"

    video_params = {
        "part": "statistics",
        "id": ",".join(video_ids),
        "key": api_key
    }

    response = requests.get(video_url, params=video_params)

    if response.status_code != 200:
        print("Video request failed:", response.status_code)
        continue

    video_data = response.json().get("items", [])

    engagement_rates = []
    total_views = 0

    for video in video_data:
        statistics = video.get("statistics", {})

        views = int(statistics.get("viewCount", 0))
        likes = int(statistics.get("likeCount", 0))
        comments = int(statistics.get("commentCount", 0))

        total_views += views

        if views > 0:
            engagement_rate = ((likes + comments) / views) * 100
            engagement_rates.append(engagement_rate)

    if engagement_rates:
        average_engagement = sum(engagement_rates) / len(engagement_rates)
    else:
        average_engagement = 0

    if video_data:
        average_views = total_views / len(video_data)
    else:
        average_views = 0

    results.append({
        "channel_id": channel_id,
        "name": creator["name"],
        "description": creator["description"],
        "subscribers": creator["subscribers"],
        "channel_views": creator["views"],
        "channel_videos": creator["videos"],
        "recent_video_count": len(video_data),
        "average_views": round(average_views),
        "average_engagement_rate": round(average_engagement, 2),
        "recent_video_titles": " | ".join(video_titles)
    })

with open(output_file, "w", newline="", encoding="utf-8") as file:
    fieldnames = [
        "channel_id",
        "name",
        "description",
        "subscribers",
        "channel_views",
        "channel_videos",
        "recent_video_count",
        "average_views",
        "average_engagement_rate",
        "recent_video_titles"
    ]

    writer = csv.DictWriter(file, fieldnames=fieldnames)

    writer.writeheader()
    writer.writerows(results)

print()
print("Enrichment completed")
print("Creators processed:", len(results))
print("Saved:", output_file)