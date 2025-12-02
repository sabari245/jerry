#!/usr/bin/env python3
import os
import sys
import json
import time
import argparse
import subprocess
import requests
from pathlib import Path
from urllib.parse import unquote

# Configuration
CACHE_FILE_NAME = ".cache"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

def send_notification(title, message):
    try:
        subprocess.run(["notify-send", title, message], check=False)
    except FileNotFoundError:
        pass

def get_allanime_links(provider_id, episode_num):
    """
    Fetches video links for allanime.
    This logic mimics the get_json and extract_from_json functions in jerry.sh for allanime.
    """
    # allanime base url and refr might need to be passed or hardcoded.
    # Assuming standard ones for now, but ideally should match jerry.sh
    allanime_base = "allanime.day" 
    allanime_refr = "https://allanime.to" 
    
    # Construct the query
    # In jerry.sh: variables={"showId":"$episode_id","translationType":"$translation_type","episodeString":"$episode_number"}
    # We default to 'sub' for now, or could add an arg.
    translation_type = "sub"
    
    variables = {
        "showId": provider_id,
        "translationType": translation_type,
        "episodeString": str(episode_num)
    }
    
    query = """query ($showId: String!, $translationType: VaildTranslationTypeEnumType!, $episodeString: String!) {
        episode(
            showId: $showId
            translationType: $translationType
            episodeString: $episodeString
        ) {
            episodeString sourceUrls
        }
    }"""

    url = f"https://api.{allanime_base}/api"
    headers = {
        "Referer": allanime_refr,
        "User-Agent": USER_AGENT
    }
    
    try:
        print(f"DEBUG: Requesting {url} with vars={variables}")
        response = requests.get(url, params={
            "variables": json.dumps(variables),
            "query": query
        }, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # print(f"DEBUG: Response: {json.dumps(data)}") 
        
        if "data" not in data or "episode" not in data["data"] or not data["data"]["episode"]:
            print(f"DEBUG: No episode data found in response. Data keys: {data.keys()}")
            if "data" in data:
                print(f"DEBUG: data content: {data['data']}")
            return None

        source_urls = data["data"]["episode"]["sourceUrls"]
        print(f"DEBUG: Found {len(source_urls)} sourceUrls")
        
        # Logic to extract links from sourceUrls
        # jerry.sh does a complex sed/grep dance. 
        # Essentially it looks for "sourceUrl" and "sourceName".
        # And then calls 'generate_links' which hits specific endpoints based on sourceName.
        
        # For simplicity in this initial version, we will try to find the 'default' or 'S-mp4' or 'Luf-mp4' links
        # which usually correspond to direct m3u8 or mp4.
        
        # We need to decipher the sourceUrl.
        # In jerry.sh: provider_init decodes the weird hex-like string.
        
        decoded_links = []
        for source in source_urls:
            source_url = source.get("sourceUrl")
            source_name = source.get("sourceName")
            
            if not source_url:
                continue
                
            # Decryption logic from jerry.sh provider_init
            # It seems to be a custom hex mapping.
            # 01->9, 08->0, 05->=, 0a->2, ...
            # This is quite brittle to port directly without the exact mapping table.
            # However, looking at jerry.sh line 191, it is a simple substitution.
            
            decrypted_id = decrypt_allanime_id(source_url)
            
            # Now we generate links based on provider name (jerry.sh line 194)
            final_link = None
            if source_name == "Luf-mp4": # gogoanime
                 final_link = f"https://{allanime_base}{decrypted_id.replace('clock', 'clock.json')}"
            elif source_name == "Default": # wixmp
                 final_link = f"https://{allanime_base}{decrypted_id.replace('clock', 'clock.json')}"
            elif source_name == "S-mp4": # sharepoint
                 final_link = f"https://{allanime_base}{decrypted_id.replace('clock', 'clock.json')}"
            
            if final_link:
                # Fetch the actual link
                # jerry.sh get_links function
                try:
                    link_resp = requests.get(final_link, headers=headers)
                    if link_resp.status_code == 200:
                        json_resp = link_resp.json()
                        # Extract links from json response
                        for link_obj in json_resp.get("links", []):
                             decoded_links.append((link_obj.get("link"), link_obj.get("resolutionStr")))
                except:
                    pass

        # Sort by resolution (best first)
        # Simple heuristic: look for 1080, then 720, etc.
        decoded_links.sort(key=lambda x: 0 if '1080' in str(x[1]) else 1 if '720' in str(x[1]) else 2)
        
        if decoded_links:
            return decoded_links[0][0] # Return best link
            
    except Exception as e:
        print(f"Error fetching links for episode {episode_num}: {e}")
        return None

    return None

def decrypt_allanime_id(encrypted_str):
    # Port of the sed command in jerry.sh line 191
    # sed 's/../&\n/g' | sed 's/^01$/9/g;s/^08$/0/g;s/^05$/=/g;s/^0a$/2/g;s/^0b$/3/g;s/^0c$/4/g;s/^07$/?/g;s/^00$/8/g;s/^5c$/d/g;s/^0f$/7/g;s/^5e$/f/g;s/^17$/\//g;s/^54$/l/g;s/^09$/1/g;s/^48$/p/g;s/^4f$/w/g;s/^0e$/6/g;s/^5b$/c/g;s/^5d$/e/g;s/^0d$/5/g;s/^53$/k/g;s/^1e$/\&/g;s/^5a$/b/g;s/^59$/a/g;s/^4a$/r/g;s/^4c$/t/g;s/^4e$/v/g;s/^57$/o/g;s/^51$/i/g;'
    
    mapping = {
        "01": "9", "08": "0", "05": "=", "0a": "2", "0b": "3", "0c": "4", "07": "?", "00": "8",
        "5c": "d", "0f": "7", "5e": "f", "17": "/", "54": "l", "09": "1", "48": "p", "4f": "w",
        "0e": "6", "5b": "c", "5d": "e", "0d": "5", "53": "k", "1e": "&", "5a": "b", "59": "a",
        "4a": "r", "4c": "t", "4e": "v", "57": "o", "51": "i"
    }
    
    result = ""
    for i in range(0, len(encrypted_str), 2):
        chunk = encrypted_str[i:i+2]
        result += mapping.get(chunk, chunk) # Default to chunk if not found (though sed doesn't seem to have default, it just passes through?)
        # Actually the sed command only replaces matches.
    
    return result

def download_episode(url, output_path):
    """
    Downloads the episode using ffmpeg for m3u8 or curl for others.
    """
    print(f"Downloading to {output_path}...")
    
    if ".m3u8" in url:
        cmd = [
            "ffmpeg", "-y", "-i", url, 
            "-c", "copy", "-bsf:a", "aac_adtstoasc", 
            output_path
        ]
        # Suppress output unless error
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg failed: {e.stderr.decode()}")
            return False
    else:
        # Direct download
        try:
            subprocess.run(["curl", "-L", "-o", output_path, url], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

def main():
    parser = argparse.ArgumentParser(description="Jerry Series Downloader")
    parser.add_argument("--title", required=True, help="Anime Title")
    parser.add_argument("--provider", required=True, help="Provider Name")
    parser.add_argument("--provider-id", required=True, help="Provider ID")
    parser.add_argument("--episodes", type=int, required=True, help="Total Episodes")
    parser.add_argument("--start", type=int, default=1, help="Start Episode")
    
    args = parser.parse_args()
    
    # Setup directories
    download_base = Path.home() / "Downloads" / "jerry" / "offline"
    anime_dir = download_base / args.title
    anime_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = anime_dir / CACHE_FILE_NAME
    
    # Load cache
    cache = {}
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                cache = json.load(f)
        except json.JSONDecodeError:
            pass
            
    print(f"Starting download for: {args.title}")
    print(f"Provider: {args.provider}, Total Episodes: {args.episodes}")
    
    for ep in range(args.start, args.episodes + 1):
        ep_str = str(ep)
        
        if cache.get(ep_str) == "completed":
            print(f"Episode {ep} already downloaded. Skipping.")
            continue
            
        print(f"Processing Episode {ep}...")
        
        link = None
        if args.provider == "allanime":
            link = get_allanime_links(args.provider_id, ep)
        else:
            print(f"Provider {args.provider} not yet supported in python script.")
            break
            
        if not link:
            print(f"Could not find link for Episode {ep}")
            continue
            
        output_filename = f"{args.title} - Episode {ep}.mp4"
        output_path = anime_dir / output_filename
        
        success = download_episode(link, str(output_path))
        
        if success:
            print(f"Episode {ep} completed.")
            cache[ep_str] = "completed"
            with open(cache_file, "w") as f:
                json.dump(cache, f)
            send_notification("Jerry Downloader", f"Downloaded {args.title} - Episode {ep}")
        else:
            print(f"Failed to download Episode {ep}")
            
    print("Download queue finished.")

if __name__ == "__main__":
    main()
