# move_recordings.py
import os
import shutil
from pathlib import Path
from datetime import datetime

def move_recordings(source_dir='recordings', target_drive='D:'):
    """
    Moves recordings to another drive while maintaining structure:
    D:\\Recordings\<channel>\<date>\<files>
    """
    target_base = Path(target_drive) / 'Recordings'
    
    for channel in os.listdir(source_dir):
        channel_path = Path(source_dir) / channel
        
        if not channel_path.is_dir():
            continue
            
        print(f"\nProcessing channel: {channel}")
        
        for recording in channel_path.glob('*.*'):
            # Skip non-recording files
            if not (recording.suffix in ['.mp4', '.ass', '.json']):
                continue
                
            # Get recording date from filename (format: channel_YYYY-MM-DD_HHMMSS)
            try:
                date_part = recording.stem.split('_')[-2]
                record_date = datetime.strptime(date_part, '%Y-%m-%d').date()
            except (IndexError, ValueError):
                record_date = datetime.now().date()
                
            # Create target directory
            target_dir = target_base / channel / str(record_date)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Move file
            try:
                shutil.move(str(recording), str(target_dir))
                print(f"Moved: {recording.name} → {target_dir}")
            except Exception as e:
                print(f"Failed to move {recording.name}: {e}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='recordings', help='Source directory')
    parser.add_argument('--target', default='D:', help='Target drive letter')
    args = parser.parse_args()
    
    move_recordings(args.source, args.target)
