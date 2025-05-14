# Twitch Recorder

A Python tool for recording Twitch streams/VODs with synchronized chat.

## Files

1. record_720p.py - Main recording script
   Usage:
   python record_720p.py CHANNEL_NAME --duration 2h (live stream)
   python record_720p.py CHANNEL --vod VOD_ID --start 1h30m --end 2h15m (VOD clip)
   python record_720p.py CHANNEL --watch (watch while recording)

2. convert_chat_to_subs.py - Chat to subtitles converter
   Usage:
   python convert_chat_to_subs.py path/to/chat.json

3. move_recordings.py - File organizer
   Usage:
   python move_recordings.py --target D:

## Requirements
- Python 3.8+
- FFmpeg in PATH
- Packages:
  pip install chat_downloader==0.2.8 streamlink==7.3.0
