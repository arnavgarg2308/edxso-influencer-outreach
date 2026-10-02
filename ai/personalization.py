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

input_file = "email_enriched_influencers.csv"
output_file = "personalized_influencers.csv"

class Personalization(BaseModel):
    index: int
    email: str
    instagram_dm: str

class PersonalizationResponse(BaseModel):
    personalizations: List[Personalization]

with open(input_file, "r", encoding="utf-8") as file:
    creators = list(csv.DictReader(file))

qualified = [
    creator for creator in creators
    if creator["status"].strip().lower() == "pass"
]

results = []
batch_size = 10

for start in range(0, len(qualified), batch_size):
    batch = qualified[start:start + batch_size]

    print(f"Processing {start + 1}-{start + len(batch)} / {len(qualified)}")

    creator_data = []

    for index, creator in enumerate(batch):
        creator_data.append({
            "index": index,
            "name": creator["name"],
            "niche": creator["niche"],
            "content_themes": creator["content_themes"],
            "content_relevance": creator["content_relevance"],
            "brand_fit": creator["brand_fit"],
            "description": creator["description"],
            "recent_video_titles": creator["recent_video_titles"]
        })

    prompt = f"""
You are an influencer outreach specialist for a Technology and AI collaboration campaign.

Create personalized outreach for every creator supplied below.

For each creator generate:

1. Email
2. Instagram DM

Email requirements:
- 60 to 90 words.
- Professional but natural.
- Personalized using the creator's actual niche, content themes, channel description, or recent video titles.
- Explain why a Technology/AI collaboration could be relevant.
- Include a clear but non-pushy call to action.
- Avoid generic mass outreach.
- Do not claim that you watched a specific video unless the supplied data supports it.
- Do not invent achievements.
- Do not invent audience demographics.
- Do not invent partnerships.
- Do not invent personal information.
- Do not invent contact information.

Instagram DM requirements:
- 15 to 30 words.
- Friendly and concise.
- Personalized using actual supplied creator information.
- No fabricated claims.

Important:
- Return exactly one result for every supplied creator.
- Preserve the supplied index exactly.
- email must contain only the email body.
- instagram_dm must contain only the DM text.

Creators:

{json.dumps(creator_data, ensure_ascii=False)}
"""

    success = False

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": PersonalizationResponse
                }
            )

            if response.parsed:
                parsed = response.parsed
            else:
                parsed = PersonalizationResponse.model_validate_json(response.text)

            if len(parsed.personalizations) != len(batch):
                raise ValueError(
                    f"Expected {len(batch)} results but received {len(parsed.personalizations)}"
                )

            for personalization in parsed.personalizations:
                creator = batch[personalization.index]

                results.append({
                    **creator,
                    "personalized_email": personalization.email,
                    "personalized_dm": personalization.instagram_dm
                })

            success = True
            print(f"Batch completed: {len(batch)} creators")
            break

        except Exception as error:
            print(f"Batch failed on attempt {attempt + 1}: {error}")

            if attempt < 2:
                print("Waiting 45 seconds before retry...")
                time.sleep(45)

    if not success:
        print("Skipping failed batch")

    time.sleep(5)

if results:
    with open(output_file, "w", newline="", encoding="utf-8") as file:
        fieldnames = list(qualified[0].keys()) + [
            "personalized_email",
            "personalized_dm"
        ]

        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

print()
print("Personalization completed")
print("Creators personalized:", len(results))
print("Saved:", output_file)