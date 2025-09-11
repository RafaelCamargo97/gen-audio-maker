import os
from pathlib import Path

from moviepy.editor import (
    VideoFileClip, AudioFileClip,
    concatenate_videoclips, concatenate_audioclips
)

# --- CONFIGURATION ---
MEDIA_FOLDER = Path(__file__).resolve().parent.parent / "data/media"
INPUT_VIDEO_NAME = "video.mp4"
INPUT_AUDIO_NAME = "audio.mp3"  # Can be .mp3, .wav, etc.
OUTPUT_VIDEO_NAME = "final_video.mp4"
OUTPUT_AUDIO_NAME = "final_audio.mp3"

LOOP_DURATION_SECONDS = 3600  # 1 hour (or 10800 for 3 hours)
CROSSFADE_TIME = 1  # in seconds
# --- END OF CONFIGURATION ---

# --- Path definitions ---
# Using pathlib's "/" operator is the modern way to join paths
video_path = MEDIA_FOLDER / INPUT_VIDEO_NAME
audio_path = MEDIA_FOLDER / INPUT_AUDIO_NAME
output_video_path = MEDIA_FOLDER / OUTPUT_VIDEO_NAME
output_audio_path = MEDIA_FOLDER / OUTPUT_AUDIO_NAME

# Check if files exist using pathlib's .exists() method
video_exists = video_path.exists()
audio_exists = audio_path.exists()

# Case 1: No media files found
if not video_exists and not audio_exists:
    print("No video or audio files found in the media folder.")
    exit()

# Case 2: Only audio found -> process just the audio with a crossfade loop
if not video_exists and audio_exists:
    print(f"Only audio found: {audio_path}")
    try:
        audio_clip = AudioFileClip(str(audio_path))
        original_duration = audio_clip.duration

        # Calculate repetitions needed to fill the target duration
        # We subtract the crossfade time as that part overlaps
        repetitions = int(LOOP_DURATION_SECONDS / (original_duration - CROSSFADE_TIME)) + 1
        print(f"Looping audio {repetitions} times with a {CROSSFADE_TIME}-second fade-in.")

        audio_clips = [audio_clip]
        for _ in range(repetitions - 1):
            # Each subsequent clip fades in to create the crossfade effect
            audio_clips.append(audio_clip.audio_fadein(CROSSFADE_TIME))

        final_audio = concatenate_audioclips(audio_clips)
        # Trim the final audio to the exact desired duration
        final_audio = final_audio.subclip(0, LOOP_DURATION_SECONDS)
        final_audio.write_audiofile(str(output_audio_path))

        print(f"Final audio exported to: {output_audio_path}")
    except Exception as e:
        print("An error occurred while processing the audio.")
        print(f"Details: {e}")
    exit()

# Case 3: Video file exists -> process it (with or without a separate audio file)
try:
    print(f"Loading video from: {video_path}")
    video_clip = VideoFileClip(str(video_path))

    repetitions = int(LOOP_DURATION_SECONDS / (video_clip.duration - CROSSFADE_TIME)) + 1
    print(f"Looping video {repetitions} times with a {CROSSFADE_TIME}-second crossfade.")

    video_clips = [video_clip]
    for _ in range(repetitions - 1):
        # crossfadein is the video equivalent of audio_fadein
        video_clips.append(video_clip.crossfadein(CROSSFADE_TIME))

    # Concatenate with a negative padding to create the visual crossfade
    final_video = concatenate_videoclips(video_clips, method="compose", padding=-CROSSFADE_TIME)
    # Trim the final video to the exact desired duration
    final_video = final_video.subclip(0, LOOP_DURATION_SECONDS)

except Exception as e:
    print("An error occurred while processing the video.")
    print(f"Details: {e}")
    exit()

# If a separate audio file also exists, loop it and add it to the final video
if audio_exists:
    try:
        print(f"Loading audio from: {audio_path}")
        audio_clip = AudioFileClip(str(audio_path))

        # This logic is repeated from Case 2; it could be moved to a function
        # in a larger application, but is fine here for clarity.
        audio_clips = [audio_clip]
        for _ in range(repetitions - 1):
            audio_clips.append(audio_clip.audio_fadein(CROSSFADE_TIME))

        final_audio = concatenate_audioclips(audio_clips)
        final_audio = final_audio.subclip(0, LOOP_DURATION_SECONDS)

        # Replace the video's original audio with the new, looped audio
        final_video = final_video.set_audio(final_audio)
    except Exception as e:
        print("An error occurred while adding the audio to the video.")
        print(f"Details: {e}")

# Export the final video file
print(f"Exporting final video to: {output_video_path}")
final_video.write_videofile(str(output_video_path), codec="libx264", audio_codec="aac")

print("Process completed successfully!")