"""NYU Courant faculty scraper.

Seeds the professors collection with their name, title, and email.
"""

# pylint: disable=R0801

import os
import re
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
mongo_dbname = os.getenv("MONGO_DBNAME", "potatoes")

if not mongo_uri:
    raise RuntimeError("MONGO_URI must be set in .env to connect to MongoDB.")

client = MongoClient(
    mongo_uri,
    serverSelectionTimeoutMS=3000,
    connectTimeoutMS=3000,
    socketTimeoutMS=5000,
)

for i in range(10):
    try:
        client.admin.command("ping")
        print("Connected to MongoDB")
        break
    except ServerSelectionTimeoutError:
        print(f"MongoDB not ready yet, retrying... ({i + 1}/10)")
        time.sleep(2)
else:
    raise RuntimeError("Could not connect to MongoDB after retries.")

db = client[mongo_dbname]

# If data already exists, stop execution
if db.professors.count_documents({}) > 0:
    print("Professors collection already has data. Skipping seeding.")
    exit(0)

LIST_URL = "https://cs.nyu.edu/dynamic/people/faculty/type/20/"


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_email(raw: str) -> str | None:
    raw = raw.lower()

    raw = raw.replace("(at)", "@").replace("[at]", "@")
    raw = raw.replace(" at ", "@")

    raw = raw.replace("(dot)", ".").replace("[dot]", ".")
    raw = raw.replace(" dot ", ".")

    raw = re.sub(r"\s+", "", raw)

    match = re.search(
        r"[a-z0-9._%+-]+@(?:[a-z0-9-]+\.)*nyu\.edu",
        raw,
        re.IGNORECASE,
    )

    return match.group(0) if match else None


page = requests.get(LIST_URL, timeout=(5, 15))
page.raise_for_status()

listing_soup = BeautifulSoup(page.text, "html.parser")
faculty_list = listing_soup.select("ul.people-listing > li.col-sm-6")

inserted_or_updated = 0

for li in faculty_list:
    name_tag = li.select_one("p.name.bold")
    title_tag = li.select_one("p.title")

    if not name_tag:
        continue

    name = _clean_line(name_tag.get_text())
    title = _clean_line(title_tag.get_text()) if title_tag else None

    email = None

    for info in li.select("p.info"):
        text = _clean_line(info.get_text(" "))

        if "email" not in text.lower():
            continue

        raw_email = re.sub(
            r"^.*?email:\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        raw_email = re.split(
            r"\s+Office:|\s+Ext:",
            raw_email,
            flags=re.IGNORECASE,
        )[0]

        email = _normalize_email(raw_email)
        break

    update = {"name": name}

    if title:
        update["title"] = title

    if email:
        update["email"] = email

    db.professors.update_one(
        {"name": name},
        {"$set": update},
        upsert=True,
    )

    inserted_or_updated += 1
    print(f"Added/updated {name}")

print(f"Done! {inserted_or_updated} professors added/updated.")