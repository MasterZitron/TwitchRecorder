import sys
import json
import re
from pathlib import Path
from datetime import timedelta

def parse_duration(dur_str):
    # supports formats like '1h35m', '10m', '45s', 'HH:MM:SS', 'MM:SS', 'SS'
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

if len(sys.argv) < 2:
    print(f"Usage: python {Path(__file__).name} <chat.json> [start_time]")
    sys.exit(1)

json_path = Path(sys.argv[1])
ass_output_path = json_path.with_suffix('.ass')

if not json_path.exists():
    print(f"Error: JSON file not found: {json_path}")
    sys.exit(1)
try:
    chat_data = json.loads(json_path.read_text(encoding='utf-8'))
    print(f"Total messages loaded: {len(chat_data)}")
except json.JSONDecodeError as e:
    print(f"Error parsing JSON: {e}")
    sys.exit(1)

is_vod_format = any('time_in_seconds' in msg for msg in chat_data)

base_timestamp = None
for m in chat_data:
    if m.get('message_type') == 'text_message' or m.get('action_type') == 'text_message':
        if is_vod_format:
            base_timestamp = m.get('time_in_seconds', 0) * 1_000_000
        else:
            base_timestamp = m.get('timestamp', 0)
        break

if base_timestamp is None:
    print("Error: No text_message entries in JSON.")
    sys.exit(1)

# Enhanced ASS header with better styling
ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Chat,Arial,28,&H00FFFFFF,&H00000000,-1,0,1,2,3,1,10,10,10,1


[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def format_ass_time(us):
    td = timedelta(microseconds=us)
    total = td.total_seconds()
    h = int(total // 3600)
    m = int((total % 3600) // 60)
    s = int(total % 60)
    cs = int((total - int(total)) * 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"

# Chat display configuration
SLOT_HEIGHT = 32
NUM_SLOTS = 20
slots = [1080 - SLOT_HEIGHT*(i+1) for i in range(NUM_SLOTS)]
slot_assignments = {}  # {slot_index: expiration_time}

ass_events = []
message_queue = []

# Duplicate message filtering
seen_messages = {}  # {user: (message, timestamp)}
filtered_chat = []

for m in chat_data:
    if not (m.get('message_type') == 'text_message' or m.get('action_type') == 'text_message'):
        continue

    user = m.get('author',{}).get('display_name','Unknown')
    text = m.get('message','').strip()
    timestamp = m.get('time_in_seconds', 0) if is_vod_format else m.get('timestamp', 0) // 1_000_000

    # Skip if same user sent same message in same second
    last_msg, last_time = seen_messages.get(user, (None, -1))
    if text == last_msg and timestamp == last_time:
        continue
    
    if not text:
        continue

    seen_messages[user] = (text, timestamp)
    filtered_chat.append(m)

    # Timestamp calculation
    if is_vod_format:
        clip_start = parse_duration(sys.argv[2]) if len(sys.argv) > 2 else 0
        message_time = int((m.get('time_in_seconds', 0) - clip_start) * 1_000_000)
    else:
        message_time = int(m.get('timestamp', 0)) - int(base_timestamp)
    
    message_time = max(0, message_time)
    color = m.get('colour','#FFFFFF').lstrip('#')
    message_queue.append((message_time, user, text, m))

message_queue.sort(key=lambda x: x[0])
chat_data = filtered_chat
print(f"Filtered to {len(chat_data)} unique messages")
# Process messages with proper slot management
MESSAGE_DURATION = 4_000_000  # 4 seconds display time

for msg_time, user, text, msg_data in message_queue:
    
    # Find available slot
    assigned_slot = None
    current_time = msg_time
    
    # Check for expired slots
    for slot, expires in list(slot_assignments.items()):
        if current_time >= expires:
            del slot_assignments[slot]
    
    # Find first available slot
    for slot in range(NUM_SLOTS):
        if slot not in slot_assignments:
            assigned_slot = slot
            break
    
    # If no slots available, use earliest expiring
    if assigned_slot is None:
        assigned_slot = min(slot_assignments.items(), key=lambda x: x[1])[0]
        current_time = slot_assignments[assigned_slot]
    
    # Calculate display times
    start_us = current_time
    end_us = start_us + MESSAGE_DURATION
    slot_assignments[assigned_slot] = end_us
    y = slots[assigned_slot]
    
    # Handle color for VOD 
    author_data = msg_data.get('author', {}) if isinstance(msg_data, dict) else {}
    color = author_data.get('colour', '#FFFFFF').lstrip('#')

    # Convert hex to ASS format (BBGGRR)
    if len(color) == 6:
        # Properly format color (RRGGBB -> BBGGRR)
        bgr = f"&H{color[4:6]}{color[2:4]}{color[0:2]}&"
    else:
        # Fallback to white if color malformed
        bgr = "&HFFFFFF&"

    # Generate ASS line with proper styling
    ass_line = (
        f"Dialogue: 0,{format_ass_time(start_us)},{format_ass_time(end_us)},Chat,,0,0,0,,"
        f"{{\\an1\\pos(50,{y})\\c{bgr}\\3a&H00&\\bord4\\blur2\\1a&H00&\\3c&H000000&}}"
        f"{user}: {{\\c&HFFFFFF&}}{text}"
    )
    ass_events.append(ass_line)
# Write ASS file
with open(ass_output_path, 'w', encoding='utf-8') as f:
    f.write(ass_header)
    f.write("\n".join(ass_events))

print(f"Generated ASS subtitles: {ass_output_path}")

# Clean up JSON
try:
    json_path.unlink()
    print(f"Deleted chat JSON: {json_path}")
except OSError as e:
    print(f"Error deleting JSON: {e}", file=sys.stderr)
