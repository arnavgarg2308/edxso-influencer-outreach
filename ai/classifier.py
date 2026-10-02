import os
import csv
import json
import time
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from typing import List

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

input_file = "enriched_influencers.csv"
output_file = "classified_influencers.csv"

class Classification(BaseModel):
    index: int
    niche: str
    content_themes: List[str]
    content_relevance: str
    brand_fit: str
    status: str
    reason: str

class ClassificationResponse(BaseModel):
    classifications: List[Classification]

with open(input_file, "r", encoding="utf-8") as file:
    creators = list(csv.DictReader(file))

results = []
batch_size = 10

for start in range(0, len(creators), batch_size):
    batch = creators[start:start + batch_size]

    print(f"Processing {start + 1}-{start + len(batch)} / {len(creators)}")

    creator_data = []

    for index, creator in enumerate(batch):
        creator_data.append({
            "index": index,
            "name": creator["name"],
            "description": creator["description"],
            "subscribers": creator["subscribers"],
            "average_views": creator["average_views"],
            "average_engagement_rate": creator["average_engagement_rate"],
            "recent_video_titles": creator["recent_video_titles"]
        })

    prompt = f"""
You are an influencer marketing analyst for an automated influencer outreach system.

The campaign is looking for micro-influencers relevant to Technology and AI.

Analyze every creator using only the supplied information.

For each creator determine:

1. Their actual primary niche.
2. 2 to 5 specific content themes.
3. Content relevance to Technology and AI.
4. Brand fit for a Technology/AI campaign.
5. Whether the creator should pass or fail the filtering stage.
6. A short evidence-based reason.

Rules:

- content_relevance must be exactly High, Medium, or Low.
- brand_fit must be exactly High, Medium, or Low.
- status must be exactly Pass or Fail.
- Pass if recent content is meaningfully related to AI, technology, software, coding, developer tools, automation, gadgets, machine learning, data science, or closely related technology topics.
- Fail if recent content is primarily unrelated to these areas.
- Do not judge only from the channel name.
- Pay particular attention to recent video titles and the channel description.
- Do not invent audience demographics.
- Do not invent contact information.
- Do not invent partnerships.
- Do not invent facts not present in the supplied data.
- Keep each reason concise.
- Return one classification for every creator.
- Preserve the supplied index exactly.

Creators:

{json.dumps(creator_data, ensure_ascii=False)}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": ClassificationResponse
            }
        )

        parsed = response.parsed

        if parsed is None:
            parsed = ClassificationResponse.model_validate_json(response.text)

        for classification in parsed.classifications:
            creator = batch[classification.index]

            results.append({
                **creator,
                "niche": classification.niche,
                "content_themes": ", ".join(classification.content_themes),
                "content_relevance": classification.content_relevance,
                "brand_fit": classification.brand_fit,
                "status": classification.status,
                "reason": classification.reason
            })

        print(f"Batch completed: {len(parsed.classifications)} creators")

    except Exception as error:
        print("Batch failed:", error)

    time.sleep(2)

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
        "recent_video_titles",
        "niche",
        "content_themes",
        "content_relevance",
        "brand_fit",
        "status",
        "reason"
    ]

    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

print()
print("LLM classification completed")
print("Creators classified:", len(results))
print("Saved:", output_file)