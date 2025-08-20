from __future__ import annotations
import os
import sys
import json
import time
import re
import requests
from typing import List, Dict, Any

# --- Configuration ---
API_BASE = "https://api.modrinth.com/v2"
CONFIG_FILE = "main.json"
MODRINTH_TOKEN = os.environ.get("MODRINTH_TOKEN")

# --- Helper Functions ---

def version_key(v: str) -> List[Any]:
    """Converts a version string into a list for proper sorting."""
    return [int(x) if x.isdigit() else x for x in re.split(r'[.-]', v)]

def get_auth_headers() -> Dict[str, str]:
    """Constructs the necessary headers for API requests."""
    if not MODRINTH_TOKEN:
        print("❌ ERROR: MODRINTH_TOKEN environment variable not set.")
        sys.exit(1)
    return {
        "Authorization": f"Bearer {MODRINTH_TOKEN}",
        "User-Agent": "AutomatedVersionUpdater/1.2",
        "Content-Type": "application/json",
    }

def load_config() -> Dict[str, Any]:
    """Loads and validates the project configuration from main.json."""
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: Configuration file '{CONFIG_FILE}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ ERROR: Could not parse '{CONFIG_FILE}'. Please check for JSON errors.")
        sys.exit(1)

# --- Modrinth API Functions ---

def get_project_versions(slug: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """Fetches all versions for a given project slug from Modrinth."""
    url = f"{API_BASE}/project/{slug}/version"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"   ⟶ ❌ Network error while fetching versions for '{slug}': {e}")
        return []

def patch_project_version(version_id: str, new_game_versions: List[str], headers: Dict[str, str]) -> bool:
    """Updates a specific version ID with a new list of game versions."""
    url = f"{API_BASE}/version/{version_id}"
    payload = {"game_versions": new_game_versions}
    try:
        response = requests.patch(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"      ⟶ ❌ Failed to update version {version_id}: {e}")
        return False

# --- Main Execution ---

def main():
    """Main script logic."""
    if len(sys.argv) < 2:
        print("❌ ERROR: Please provide the target Minecraft version as an argument.")
        print("   Example: python main.py 1.21.9")
        sys.exit(1)

    target_mc_version = sys.argv[1]
    print("🚀 Starting Modrinth Automated Version Updater...")
    
    headers = get_auth_headers()
    config = load_config()

    projects_to_update = config
    if not projects_to_update:
        print("ℹ️  No projects found in 'main.json' to update. Exiting.")
        sys.exit(0)

    print(f"🎯 Target Minecraft Version: {target_mc_version}\n")
    
    total_updated = 0
    for slug, target_project_versions in projects_to_update.items():
        print(f"🔹 Processing project: '{slug}'")
        
        all_mod_versions = get_project_versions(slug, headers)
        if not all_mod_versions:
            continue

        versions_to_patch = [
            v for v in all_mod_versions if v.get("version_number") in target_project_versions
        ]

        if not versions_to_patch:
            print(f"   ⟶ ℹ️  No matching versions found for '{slug}' from the list: {target_project_versions}")

        for version_data in versions_to_patch:
            version_name = version_data.get('name')
            version_number = version_data.get('version_number')
            version_id = version_data.get('id')
            current_game_versions = version_data.get('game_versions', [])

            if target_mc_version in current_game_versions:
                print(f"   • Skipping '{version_name}' ({version_number}): Already supports {target_mc_version}.")
                continue

            new_game_versions = sorted(
                list(set(current_game_versions + [target_mc_version])),
                key=version_key
            )
            
            print(f"   • Updating '{version_name}' ({version_number}): {current_game_versions} -> {new_game_versions}")
            
            success = patch_project_version(version_id, new_game_versions, headers)
            if success:
                total_updated += 1
            
            time.sleep(0.5)
        print("-" * 20)

    print(f"\n✅ Done. Successfully updated {total_updated} version(s).")

if __name__ == "__main__":
    main()
