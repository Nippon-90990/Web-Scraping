import re
import json
import os
import requests # type: ignore
from requests.exceptions import RequestException, Timeout # type: ignore

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class SteamExtractorError(Exception):
    """Custom exception for Steam extractor errors"""
    pass


def extract_app_id(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise SteamExtractorError("URL is empty or not a string")

    match = re.search(r"/app/(\d+)", url)
    if not match:
        raise SteamExtractorError("Invalid Steam product URL")

    return match.group(1)


def fetch_steam_data(app_id: str) -> dict:
    api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"

    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
    except Timeout:
        raise SteamExtractorError("Steam API request timed out")
    except RequestException as e:
        raise SteamExtractorError(f"Network error: {e}")

    try:
        data = response.json()
    except ValueError:
        raise SteamExtractorError("Invalid JSON received from Steam")

    if app_id not in data:
        raise SteamExtractorError("Steam API response missing app ID")

    if not data[app_id].get("success"):
        raise SteamExtractorError("Steam API returned success=false")

    return data[app_id]["data"]


def build_payload(app_id: str, url: str, game: dict) -> dict:
    try:
        screenshots = [
            s["path_full"]
            for s in game.get("screenshots", [])
            if "path_full" in s
        ]
    except TypeError:
        screenshots = []

    return {
        "app_id": app_id,
        "name": game.get("name", "Unknown"),
        "source": url,
        "images": {
            "header": game.get("header_image"),
            "screenshots": screenshots
        }
    }


def save_json(app_id: str, payload: dict) -> None:
    file_path = os.path.join(OUTPUT_DIR, f"app_{app_id}.json")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except OSError as e:
        raise SteamExtractorError(f"Failed to write JSON file: {e}")

    print(f"✅ Saved → {file_path}")


def process_url(url: str) -> None:
    print(f"\n🔍 Processing: {url}")

    try:
        app_id = extract_app_id(url)
        game_data = fetch_steam_data(app_id)
        payload = build_payload(app_id, url, game_data)
        save_json(app_id, payload)

        image_count = (
            1 if payload["images"]["header"] else 0
        ) + len(payload["images"]["screenshots"])

        print(f"🖼️ Extracted {image_count} image URLs")

    except SteamExtractorError as e:
        print(f"❌ Error: {e}")

    except Exception as e:
        # Catch-all safety net (should never crash)
        print(f"🔥 Unexpected error: {e}")


def load_urls(file_path: str) -> list:
    if not os.path.exists(file_path):
        raise SteamExtractorError(f"Input file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


if __name__ == "__main__":
    try:
        urls = load_urls("steam_links.txt")
    except SteamExtractorError as e:
        print(f"❌ Startup error: {e}")
        exit(1)

    for url in urls:
        process_url(url)

    print("\n🎉 Finished processing all URLs.")
