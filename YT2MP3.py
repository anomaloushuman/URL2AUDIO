import os
import yt_dlp as youtube_dl  # Use yt-dlp instead of youtube-dl
from pydub import AudioSegment
import librosa
import numpy as np
import asyncio
from shazamio import Shazam
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TALB, TPE1, APIC, TXXX
import time

# Function to download audio from YouTube URL using yt-dlp
def download_audio(url):
    # Use a timestamp to create a unique file name
    timestamp = int(time.time())
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
        'outtmpl': f'downloaded_audio_{timestamp}.%(ext)s'
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        audio_file = f'downloaded_audio_{timestamp}.mp3'
    return audio_file

# Function to analyze the tempo and key of the audio file
def analyze_audio(file_path):
    # Load the audio file using librosa
    y, sr = librosa.load(file_path, sr=None)
    
    # Analyze the tempo (beats per minute)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    
    # Use harmonic feature to find key
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    return tempo, chroma

# Function to map the chroma vector to a musical key
def get_key_from_chroma(chroma_vector):
    if chroma_vector.size > 0:  # Check if chroma_vector has any elements
        # Check if the chroma vector is not empty and has the expected shape
        if chroma_vector.shape[1] > 0:
            # Get the index of the maximum value in the chroma vector
            index = np.argmax(np.sum(chroma_vector, axis=1))  # Sum over frames to get a single index
            keys = ['C', 'C♯/D♭', 'D', 'D♯/E♭', 'E', 'F', 'F♯/G♭', 'G', 'G♯/A♭', 'A', 'A♯/B♭', 'B']
            return keys[index]
    return "Unable to determine key"

# Function to save the audio file in the desired format
def save_audio(input_file, output_format='mp3'):
    # Ensure the Library directory exists in the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    library_dir = os.path.join(script_dir, "Library")
    if not os.path.exists(library_dir):
        os.makedirs(library_dir)  # Create the Library directory if it doesn't exist

    # Load the audio file using pydub
    audio = AudioSegment.from_file(input_file)
    
    # Output path with a timestamp to ensure uniqueness
    timestamp = int(time.time())
    output_path = os.path.join(library_dir, f"downloaded_audio_{timestamp}.{output_format}")
    
    # Save the file as MP3 or WAV
    if output_format == 'mp3':
        audio.export(output_path, format='mp3', bitrate="320k")
    elif output_format == 'wav':
        audio.export(output_path, format='wav')
    
    return output_path


async def get_song_info(file_path):
    shazam = Shazam()
    out = await shazam.recognize(file_path)
    return out

def add_metadata_to_audio(output_path, song_info, tempo, key):
    # Extract metadata from song_info
    track = song_info['track']
    title = track['title']
    artist = track['subtitle']
    
    # Extract album information from the metadata
    album = "Unknown Album"  # Default value
    if 'sections' in track:
        for section in track['sections']:
            if section['type'] == 'SONG':
                for metadata in section['metadata']:
                    if metadata['title'] == 'Album':
                        album = metadata['text']
                        break

    # Load the audio file
    audio = MP3(output_path)

    # Check if ID3 tags already exist
    if audio.tags is None:
        audio.add_tags()  # Create ID3 tags if they don't exist

    # Update ID3 tags
    audio.tags.clear()  # Clear existing tags to avoid conflicts
    audio.tags.add(TIT2(encoding=3, text=title))  # Title
    audio.tags.add(TPE1(encoding=3, text=artist))  # Artist
    audio.tags.add(TALB(encoding=3, text=album))   # Album

    # Add custom metadata for tempo and key
    audio.tags.add(TXXX(encoding=3, desc='Tempo', text=str(tempo)))  # Tempo
    audio.tags.add(TXXX(encoding=3, desc='Key', text=key))  # Key

    # Add cover art (if applicable)
    cover_art_url = track['images'].get('coverart', None)
    if cover_art_url:
        import requests
        from io import BytesIO

        # Download the cover art
        response = requests.get(cover_art_url)
        cover_art = BytesIO(response.content)

        # Add cover art to the audio file
        audio.tags.add(APIC(
            encoding=3,  # 3 is for ID3v2.3
            mime='image/jpeg',  # MIME type
            type=3,  # 3 is for the cover image
            desc='Cover',
            data=cover_art.getvalue()
        ))

    # Save the changes to the original file
    audio.save(output_path)

    # Create the directory structure: Library/Artist/Album
    script_dir = os.path.dirname(os.path.abspath(__file__))
    library_dir = os.path.join(script_dir, "Library", artist, album)
    if not os.path.exists(library_dir):
        os.makedirs(library_dir)  # Create the directories if they don't exist

    # Rename the file to the song title (replace spaces with underscores)
    safe_title = title.replace(" ", "_")  # Replace spaces with underscores
    new_file_name = f"{safe_title}.mp3"
    new_file_path = os.path.join(library_dir, new_file_name)

    # Move the file to the new location
    os.rename(output_path, new_file_path)

    # Print the success message with title and artist
    print(f"Song detected: {title} by {artist}")

    return new_file_path

# Main Program
if __name__ == "__main__":
    url = input("Enter the URL to download the audio: ")
    try:
        # Step 1: Download the audio file
        downloaded_audio = download_audio(url)
        print(f"Downloaded audio file: {downloaded_audio}")
        
        # Step 2: Analyze the audio file (tempo and key)
        tempo, chroma = analyze_audio(downloaded_audio)
        print(f"Tempo: {tempo} BPM")
        
        # Get the musical key from the chroma vector
        musical_key = get_key_from_chroma(chroma)
        print(f"Key (Musical): {musical_key}")
        
        # Step 3: Save the file automatically as MP3
        output_path = save_audio(downloaded_audio, output_format='mp3')
        
        song_info = asyncio.run(get_song_info(output_path))
        
        new_file_path = add_metadata_to_audio(output_path, song_info, tempo, musical_key)
        print(f"Audio, information, and cover photo saved to: {new_file_path}")
    
    except Exception as e:
        print(f"An error occurred: {e}")
