import argparse
import re
import subprocess
import sys
import signal
import time
import shutil
import os
import threading
from datetime import datetime
from pathlib import Path
import subprocess

def convert_for_youtube(ass_path):
    """Converts .ass to YouTube-compatible .vtt or .srt"""
    vtt_path = ass_path.with_suffix('.vtt')
    
    # Convert using ffmpeg
    cmd = [
        'ffmpeg',
        '-i', str(ass_path),
        '-loglevel', 'error',
        '-stats',
        '-c:s', 'webvtt',  # YouTube's preferred format
        str(vtt_path)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Converted to YouTube-compatible: {vtt_path}")
        return vtt_path
    except Exception as e:
        print(f"Conversion failed: {e}")
        return None



def parse_duration(dur_str):
    # supports formats like '1h35m', '10m', '45s', 'HH:MM:SS', 'MM:SS', 'SS'
    if not dur_str:
        return None
    # match HH:MM:SS, MM:SS, or SS
    hms_match = re.match(r'^(?:(\d+):)?(?:(\d+):)?(\d+)$', dur_str)
    if hms_match:
        groups = hms_match.groups()
        nums = [int(g) if g else 0 for g in groups]
        if hms_match.group(1) and hms_match.group(2):  # H:M:S
            hours, minutes, seconds = nums
        elif hms_match.group(2):  # M:S
            hours = 0
            minutes, seconds = nums[1], nums[2]
        else:  # S only
            hours = minutes = 0
            seconds = nums[2]
        return hours * 3600 + minutes * 60 + seconds
    # fallback for combined like '1h35m', '10m', '45s'
    total = 0
    for value, unit in re.findall(r'(\d+)([hms])', dur_str):
        v = int(value)
        if unit == 'h': total += v * 3600
        elif unit == 'm': total += v * 60
        elif unit == 's': total += v
    return total


class Recorder:
    def __init__(self, channel, duration=None, base_dir='recordings', watch=False, vod_id=None, start_time=None, end_time=None):
        self.channel = channel
        self.duration = duration
        self.base_dir = base_dir
        self.watch = watch
        self.vod_id = vod_id
        self.start_time = start_time
        self.end_time = end_time
        self.stream_url = None
        self.chat_proc = None
        self.video_proc = None
        self.vlc_proc = None
        self.timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        # Create channel subdirectory
        self.channel_dir = os.path.join(self.base_dir, self.channel)
        os.makedirs(self.channel_dir, exist_ok=True)

    def start_watching(self):
        """Launch VLC to watch the stream while recording"""
        if not self.watch or self.vod_id:
            return  # Only for live streams
            
        try:
            # Try common VLC installation paths
            vlc_path = None
            possible_paths = [
                r'C:\Program Files\VideoLAN\VLC\vlc.exe',
                r'C:\Program Files (x86)\VideoLAN\VLC\vlc.exe',
                '/usr/bin/vlc',  # Linux/Mac
                '/Applications/VLC.app/Contents/MacOS/VLC'  # Mac
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    vlc_path = path
                    break
                    
            if not vlc_path:
                raise FileNotFoundError("VLC not found in standard locations")
                
            # Launch VLC with stream URL
            self.vlc_proc = subprocess.Popen(
                [vlc_path, self.stream_url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            print(f'Started VLC player (pid {self.vlc_proc.pid})')
            
        except Exception as e:
            print(f"Failed to launch VLC: {str(e)}", file=sys.stderr)
            


    def fetch_stream_url(self):
        url = f'https://www.twitch.tv/videos/{self.vod_id}' if self.vod_id else f'https://www.twitch.tv/{self.channel}'
        cmd = ['streamlink', '--stream-url', url, '720p60,best']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print('Error fetching stream URL:', result.stderr, file=sys.stderr)
            sys.exit(1)
        self.stream_url = result.stdout.strip()
        print('Stream URL:', self.stream_url)

    def start_chat(self):
        url = f'https://www.twitch.tv/videos/{self.vod_id}' if self.vod_id else f'https://www.twitch.tv/{self.channel}'
        #out_file = os.path.join(self.channel_dir, f"{self.channel}_{self.timestamp}_chat.json")
        out_file = os.path.join(self.channel_dir, f"{self.channel}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_chat.json")
        cmd = ['chat_downloader', url, '--message_groups', 'all', '--output', out_file, '--quiet']
        if self.vod_id and self.start_time:
            cmd += ['--start', str(parse_duration(self.start_time))]
        if self.vod_id and self.end_time:
            cmd += ['--end', str(parse_duration(self.end_time))]
        proc = subprocess.Popen(cmd)
        print(f'Started chat_downloader (pid {proc.pid})')
        return proc, out_file

    def _pump_ffmpeg_output(self, pipe):
        for line in iter(pipe.readline, ''):
            sys.stderr.write(line)
        pipe.close()

    def start_video(self):
        #out_file = os.path.join(self.channel_dir, f"{self.channel}_{self.timestamp}.mp4")
        out_file = os.path.join(self.channel_dir, f"{self.channel}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.mp4")
        cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-analyzeduration', '1M', '-probesize', '1M'
        ]
        if self.vod_id:
            if self.start_time:
                cmd += ['-ss', str(parse_duration(self.start_time))]
            cmd += ['-i', self.stream_url]
            if self.end_time:
                start_sec = parse_duration(self.start_time) or 0
                end_sec = parse_duration(self.end_time)
                cmd += ['-to', str(end_sec - start_sec)]
        else:
            cmd += ['-i', self.stream_url]
            if self.duration:
                cmd += ['-t', str(self.duration)]
        cmd += ['-c', 'copy', out_file]

        self.video_proc = subprocess.Popen(
            cmd, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True
        )
        threading.Thread(
            target=self._pump_ffmpeg_output,
            args=(self.video_proc.stderr,), daemon=True
        ).start()
        print(f'Started ffmpeg (pid {self.video_proc.pid})')
        print('The video is downloading, please wait. Might take a while with slower internet\n'
              'or if the stream is on going, consider changing the quality options on line 121.')
                
        

    def run(self):
        signal.signal(signal.SIGINT, lambda s, f: (print('Interrupt, stopping...', file=sys.stderr), self.video_proc.terminate()))
        self.fetch_stream_url()
        self.start_watching() if self.watch and not self.vod_id else None
        self.chat_proc, chat_file = self.start_chat()
        self.start_video()
        try:
            self.video_proc.wait()
        except KeyboardInterrupt:
            pass
        finally:
            # Give chat_downloader time to finish downloading messages
            if self.chat_proc and self.chat_proc.poll() is None:
                print('Waiting for chat_downloader to finish...', file=sys.stderr)
                try:
                    self.chat_proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    print('chat_downloader timeout, terminating...', file=sys.stderr)
                    self.chat_proc.terminate()
                    self.chat_proc.wait()
            print('Converting chat to subtitles...')
            subprocess.run(['python', 'convert_chat_to_subs.py', chat_file, 
                           str(parse_duration(self.start_time) if self.start_time and self.vod_id else '0')])
            ass_path = Path(chat_file).with_suffix('.ass')
            if ass_path.exists():
                youtube_sub = convert_for_youtube(ass_path)
                if youtube_sub:
                    print(f"Upload this file to YouTube: {youtube_sub}")

            def _terminate(self):
                # terminate video only; chat handled separately
                if self.video_proc and self.video_proc.poll() is None:
                    self.video_proc.terminate()


def main():
    parser = argparse.ArgumentParser(description='Record Twitch stream/VOD and chat')
    parser.add_argument('channel')
    parser.add_argument('-d', '--duration', default=None)
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--vod', default=None)
    parser.add_argument('--start', default=None)
    parser.add_argument('--end', default=None)
    args = parser.parse_args()

    dur_sec = parse_duration(args.duration) if args.duration else None
    if args.duration and (dur_sec is None or dur_sec <= 0):
        print('Invalid duration format', file=sys.stderr)
        sys.exit(1)

    Recorder(
        channel=args.channel,
        duration=dur_sec,
        watch=args.watch,
        vod_id=args.vod,
        start_time=args.start,
        end_time=args.end
    ).run()

if __name__ == '__main__':
    main()
