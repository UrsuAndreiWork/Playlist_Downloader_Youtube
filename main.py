import re
import zipfile

import yt_dlp
import os
import requests
from bs4 import BeautifulSoup
import json


def download_ffmpeg(ffmpeg_folder="ffmpeg_bin"):
    """
    Downloads and extracts a portable FFmpeg binary to a specified folder if not already present.
    """
    ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl.zip"
    ffmpeg_zip = "ffmpeg.zip"

    # Check if FFmpeg binary already exists
    ffmpeg_exe_path = os.path.join(ffmpeg_folder, "ffmpeg.exe")
    if os.path.exists(ffmpeg_exe_path):
        print("FFmpeg is already downloaded and available.")
        return ffmpeg_folder

    # Download the FFmpeg zip
    print("Downloading FFmpeg...")
    response = requests.get(ffmpeg_url, stream=True)
    with open(ffmpeg_zip, "wb") as file:
        for chunk in response.iter_content(chunk_size=1024):
            file.write(chunk)

    # Extract FFmpeg
    print("Extracting FFmpeg...")
    with zipfile.ZipFile(ffmpeg_zip, "r") as zip_ref:
        zip_ref.extractall(ffmpeg_folder)

    # Clean up zip file
    os.remove(ffmpeg_zip)

    # Find the path to the FFmpeg binary
    for root, dirs, files in os.walk(ffmpeg_folder):
        if "ffmpeg.exe" in files or "ffmpeg" in files:
            print("FFmpeg setup completed.")
            return root
    print("FFmpeg binary not found after extraction!")
    return None

def read_json_file(file_name):
    """
    Reads playlist data from a JSON file.

    :param file_name: Name of the JSON file
    :return: A list of playlist objects
    """
    try:
        with open(file_name, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"File {file_name} not found.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file {file_name}: {e}")
        return []

def extract_playlist_links(url):
    """
    Extracts video titles and links from a YouTube playlist page.

    :param url: The URL of the YouTube playlist or video
    :return: A list of dictionaries with 'title' and 'link' keys
    """
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        script_tags = soup.find_all('script')
        playlist_data = None

        for tag in script_tags:
            if tag.string and 'ytInitialData' in tag.string:
                json_data_match = re.search(r'var ytInitialData = ({.*?});', tag.string)
                if json_data_match:
                    playlist_data = json_data_match.group(1)
                    break

        if not playlist_data:
            print("No playlist data found.")
            return []

        data = json.loads(playlist_data)
        playlist_items = (
            data.get('contents', {})
            .get('twoColumnWatchNextResults', {})
            .get('playlist', {})
            .get('playlist', {})
            .get('contents', [])
        )

        videos = []
        for item in playlist_items:
            video_renderer = item.get("playlistPanelVideoRenderer", {})
            title = video_renderer.get("title", {}).get("simpleText", "No Title")
            video_id = video_renderer.get("navigationEndpoint", {}).get(
                "watchEndpoint", {}
            ).get("videoId", "")
            link = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
            if link:
                videos.append({"title": title, "link": link})

        return videos

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON data: {e}")
        return []


def download_audio(videos, ffmpeg_path, download_folder="music"):
    """
    Downloads audio using yt-dlp.
    """
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    for video in videos:
        title = video['title']
        link = video['link']
        print(f"Downloading audio: {title} from {link}")
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(download_folder, f"{title}.%(ext)s"),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': "mp3",
                    'preferredquality': '192',
                }],
                'ffmpeg_location': ffmpeg_path,  # Correctly placed here
                'quiet': False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])
            print(f"Downloaded audio: {title}")
        except Exception as e:
            print(f"Error downloading audio {title}: {e}")


def download_video(videos, ffmpeg_path, download_folder="videos"):
    """
    Downloads videos with audio using yt-dlp.
    """
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    for video in videos:
        title = video['title']
        link = video['link']
        print(f"Downloading video: {title} from {link}")
        try:
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': os.path.join(download_folder, f"{title}.%(ext)s"),
                'merge_output_format': 'mp4',
                "ffmpeg_location": ffmpeg_path,
                'quiet': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])
            print(f"Downloaded video: {title}")
        except Exception as e:
            print(f"Error downloading video {title}: {e}")


ffmpeg_folder = "ffmpeg_bin"
ffmpeg_path = download_ffmpeg(ffmpeg_folder)
if ffmpeg_path:
    file_name = "playlists.json"  # JSON file containing playlist links and attributes
    playlist_data = read_json_file(file_name)

    for playlist in playlist_data:
        url = playlist['link']
        with_video = playlist.get('with_video', False)  # Default to False if not provided
        print(f"Processing playlist: {url} | With video: {with_video}")

        videos = extract_playlist_links(url)
        if with_video:
            download_video(videos,ffmpeg_path)
        else:
            download_audio(videos,ffmpeg_path)
else:
    print("Failed to set up FFmpeg.")