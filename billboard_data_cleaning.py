import pandas as pd
import numpy as np
import requests
import swifter
import re
# Import dependencies for Spotipy
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Import Client ID and Client Secret
from config import cid, secret

# Read in Billboard Top 100 dataset
df = pd.read_csv('./Resources/charts.csv')

# Convert date column to date type
df['date'] = pd.to_datetime(df['date'])
# Create new column for year
df['year'] = df['date'].dt.year
# Remove special characters from artist and song name
# df['artist'] = df['artist'].str.replace(r"\(.*\)","")
# df['song'] = df['song'].str.replace(r"\(.*\)","")

df['song'] = df['song'].str.replace("\"", "") \
                        # .str.replace(",", "") \
                        # .str.replace("!", "")


# Create new column showing number of weeks in #1 spot (if exists)
# df['weeks-at-no1'] = df[df['rank']==1].groupby(['song', 'artist'], as_index=False).count()['date']

# Remove single quotes/apostrophes from song names
df['song'] = df['song'].str.replace("'", "")

# Create new dataframe of all unique Billboard charting songs
unique_billboard_tracks_df = df.groupby(['song','artist', 'year'], as_index=False).agg({'peak-rank': 'min', 
                                                                                        'weeks-on-board': 'max',
                                                                                        'weeks-at-no1': 'max'})
# unique_billboard_tracks_df['weeks-at-no1'] = df[df['rank']==1].groupby(['song', 'artist'], as_index=False).count()['date']

# Create separate dataframes for each decade
billboard_1960s = unique_billboard_tracks_df[(unique_billboard_tracks_df['year']<1970) & (unique_billboard_tracks_df['year']>=1960)]
billboard_1970s = unique_billboard_tracks_df[(unique_billboard_tracks_df['year']<1980) & (unique_billboard_tracks_df['year']>=1970)]
billboard_1980s = unique_billboard_tracks_df[(unique_billboard_tracks_df['year']<1990) & (unique_billboard_tracks_df['year']>=1980)]
billboard_1990s = unique_billboard_tracks_df[(unique_billboard_tracks_df['year']<2000) & (unique_billboard_tracks_df['year']>=1990)]
billboard_2000s = unique_billboard_tracks_df[(unique_billboard_tracks_df['year']<2010) & (unique_billboard_tracks_df['year']>=2000)]
billboard_2010s = unique_billboard_tracks_df[(unique_billboard_tracks_df['year']<2020) & (unique_billboard_tracks_df['year']>=2010)]
billboard_2020s = unique_billboard_tracks_df[unique_billboard_tracks_df['year']>=2020]

# Create list of dataframes
billboard_dfs = [billboard_1960s, billboard_1970s, billboard_1980s, billboard_1990s, billboard_2000s, billboard_2010s, billboard_2020s]

# Display dataframe
unique_billboard_tracks_df.head()
unique_billboard_tracks_df[unique_billboard_tracks_df['weeks-at-no1'].isnull()==False]


# SPOTIFY API

# Create objects for accessing Spotify API
client_credentials_manager = SpotifyClientCredentials(client_id=cid, client_secret=secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# Run search query with song title and artist strings
def search_spotify(song_title, artist):
    try:
        searchResults = sp.search(q=f"artist:{artist} track:{song_title}", type="track")
        track_id = searchResults['tracks']['items'][0]['id']
        return track_id
    except:
        pass
        # print(f"'{song_title}' by {artist} returned 0 results.")

# Return list with different substrings combinations for song titles containing ()
def adjust_parens(song_title):
    combinations = []

    strip_parens = ' '.join(song_title.strip(')(').split(')'))
    strip_parens = ' '.join(strip_parens.strip(' (').split('(')).replace('  ',' ')
    combinations.append(strip_parens)

    try:
        inside_parens = re.findall(r'\(.*?\)', song_title)[0].strip('()').strip()
    except IndexError:
        pass
        
    try:
        left_parens = song_title.split(f"({inside_parens})")[0].strip()
        if (left_parens not in combinations) & (len(left_parens) > 0): 
            combinations.append(left_parens)
    except:
        left_parens = "NA"

    try:
        right_parens = song_title.split(f"({inside_parens})")[1].strip()
        if (right_parens not in combinations) & (len(right_parens) > 0): 
            combinations.append(right_parens)
    except:
        right_parens = "NA"

    return combinations

# Retrieve track ID from Spotify given the artist and song title
def get_track_id(song_title, artist):
    while True:
        # Select first artist if multiple listed with "Featuring" keyword
        if 'Featuring' in artist:
            artist = artist.split(' Featuring ')[0]
        # Select first artist if multiple listed with "with", "With", or "," substrings
        elif ' with ' in artist:
            artist = artist.split(' with ')[0]
        elif ' With ' in artist:
            artist = artist.split(' With ')[0]
        elif "," in artist:
            artist = artist.split(',')[0]

        # Make initial API search, return ID string if found
        found_id = search_spotify(song_title, artist)
        if found_id:
            return found_id

        # Search artist and song title (replacing words ending in "in" to "ing")
        song_title = re.sub(r"in\b", 'ing ', song_title)
        found_id = search_spotify(song_title, artist)
        if found_id:
            return found_id

        if '(' in song_title:
            for item in adjust_parens(song_title):
                found_id = search_spotify(item, artist)
                if found_id:
                    return found_id
                
        # Check for '/' character in song_title
        if '/' in song_title:
            # Try string on left side of '/'
            song_title = song_title.split('/')[0]
            found_id = search_spotify(song_title, artist)
            if found_id:
                return found_id

            # Try string on right side of '/'
            try:
                song_title = song_title.split('/')[1]
                found_id = search_spotify(song_title, artist)
                if found_id:
                    return found_id
            except:
                pass

        # Check for '&' character in artist name
        if ' & ' in artist:
            artist = artist.split(' & ')[0]
            found_id = search_spotify(song_title, artist)
            if found_id:
                return found_id
        # Check for 'X' character in artist name
        if ' X ' in artist:
            artist = artist.split(' X ')[0]
            found_id = search_spotify(song_title, artist)
            if found_id:
                return found_id
        # Check for 'x' character in artist name
        if ' x ' in artist:
            artist = artist.split(' x ')[0]
            found_id = search_spotify(song_title, artist)
            if found_id:
                return found_id
            
        # Print song title and artist for non-match
        if found_id:
            return found_id
        
        break

# Returns tuple of audio features from Spotify for specified track_id
def get_audio_features(id):
    try:
        search_results = sp.audio_features(id)[0]
        danceability = search_results['danceability']
        energy = search_results['energy']
        key = search_results['key']
        loudness = search_results['loudness']
        mode = search_results['mode']
        speechiness = search_results['speechiness']
        acousticness = search_results['acousticness']
        instrumentalness = search_results['instrumentalness']
        liveness = search_results['liveness']
        valence = search_results['valence']
        tempo = search_results['tempo']
        duration_ms = search_results['duration_ms']
        time_signature = search_results['time_signature']
    except:
        return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan

    return danceability, energy, key, loudness, mode, speechiness, acousticness, instrumentalness, liveness, \
                valence, tempo, duration_ms, time_signature

# Add new "track_id" column for 1960's dataset based on Spotify API calls and export as csv
billboard_1960s['track_id'] = billboard_1960s[['song', 'artist']].swifter.apply(lambda row:get_track_id(row.song,row.artist),axis=1)
billboard_1960s.to_csv(f'./Resources/billboard_1960s.csv', index=False)

