import re
from pathlib import Path

from pydub import AudioSegment

def concatenate_audio_blocks(base_audio_folder: Path, final_audio_dir: Path):
    #base_audio_folder = Path(__file__).resolve().parent.parent / "data/audio-output"
    #output_folder = base_audio_folder / "whole-audiobook"
    #output_folder.mkdir(parents=True, exist_ok=True)  # Ensure the subfolder exists

    # Regex to identify and extract the number from the filename
    file_pattern = re.compile(r"block(\d+)\.wav")

    # List and filter .wav files that follow the blockX.wav pattern
    # Using pathlib's glob is often cleaner than os.listdir + filter
    wav_files = [
        f.name for f in base_audio_folder.glob("*.wav")
        if file_pattern.match(f.name)
    ]

    # Sort the files based on the number in the name
    sorted_files = sorted(
        wav_files,
        key=lambda filename: int(file_pattern.match(filename).group(1))
    )

    # Create a pause of 0.35 seconds (350 milliseconds)
    # It's more efficient to create the pause object once, outside the loop.
    pause = AudioSegment.silent(duration=350)

    # Concatenate the audio files
    audiobook = AudioSegment.empty()

    for filename in sorted_files:
        file_path = base_audio_folder / filename
        audio_segment = AudioSegment.from_wav(file_path)

        if not audiobook: # If the audiobook is empty, this is the first segment
            audiobook += audio_segment
        else:
            audiobook += pause + audio_segment

    # Save the final file
    final_output_path = final_audio_dir / "final_audio.wav"
    audiobook.export(final_output_path, format="wav")

    print(f"Concatenated audiobook saved to: {final_output_path}")

# Run the script
#if __name__ == "__main__":
#    concatenate_audio_blocks()