# Twitch Recorder

A Python tool for recording Twitch streams/VODs with synchronized chat.

## Requirements

- Python 3.8+
- Required packages:
  ```bash
  pip install chat_downloader==0.2.8 streamlink==7.3.0

- FFmpeg (must be in PATH)

## Files

### record_720p.py
Main recording script. Records video and chat simultaneously.

Usage:
```bash
# Record live stream (2 hours max)
python record_720p.py CHANNEL --duration 2h (starts recording the livestream, then stops after it has recorded 2 hours)

# Record VOD segment (1:30-2:15)
python record_720p.py CHANNEL --vod VOD_ID --start 1h30m --end 2h15m (VOD_ID is the numbers on a twitch video link, https://www.twitch.tv/videos/-->2457952948<--,
                                                                     starts recording at 01:30:00 of a vod, and stops at 02:15:00)

# Watch while recording
python record_720p.py CHANNEL --watch (watch a live stream while its recording with VLC. Requires VLC to be installed (obviously...))

Replace CHANNEL with any twitch channel name.
```

### convert_chat_to_subs.py
Converts chat JSON to subtitles (ASS for local use in VLC, VTT for YouTube).

Automatically runs after recording. Can be manually executed:
```bash
python convert_chat_to_subs.py path/to/chat.json
```

### move_recordings.py
Organizes files by channel/date to another drive.

Usage:
```bash
python move_recordings.py --target D (moves the files to the D:\Recordings directory)

# Change folder location
python move_recordings.py --source "path/to/folder" (example: --source "D:\TwitchLives\WatchLater\Streams" will save the recordings to the "Streams folder")
