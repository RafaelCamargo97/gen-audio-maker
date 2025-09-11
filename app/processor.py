from pathlib import Path
from job_manager import JobManager
from gemini_audiobook_creator import generate_audio_from_blocks
from wav_handler import concatenate_audio_blocks
from pdf_handler import process_pdf_to_blocks


def create_job_folders(base_data_dir: Path, job_id: str) -> tuple[Path, Path, Path, Path]:
    """Creates the folder structure for a given job ID and returns key paths."""
    job_dir = base_data_dir / job_id
    text_input_dir = job_dir / "text-input"
    audio_input_dir = job_dir / "audio-input"
    audio_output_dir = job_dir / "audio-output"
    audio_output_blocks_dir = audio_output_dir / "audio-blocks"
    final_audio_dir = audio_output_dir / "final-audio"

    # Create all directories
    for d in [job_dir, text_input_dir, audio_input_dir, audio_output_dir, audio_output_blocks_dir, final_audio_dir]:
        d.mkdir(parents=True, exist_ok=True)

    return text_input_dir, audio_input_dir, audio_output_blocks_dir, final_audio_dir


async def run_conversion_pipeline(job_id: str, text_input_dir: Path, audio_input_dir: Path,
                                  audio_output_blocks_dir: Path, final_audio_dir: Path):
    try:
        # --- Step 1: Process PDF to text blocks ---
        JobManager.update_job_status(job_id, "processing", "Step 1/3: Splitting PDF into text blocks...")
        print(f"[{job_id}] Starting Step 1: PDF Processing")
        num_blocks = process_pdf_to_blocks(source_pdf_path=text_input_dir, output_dir=audio_input_dir)
        if num_blocks == 0:
            raise ValueError("No text blocks were generated from the source file.")
        print(f"[{job_id}] Finished Step 1: Created {num_blocks} text blocks.")

        # --- Step 2: Generate audio from text blocks ---
        JobManager.update_job_status(job_id, "processing", "Step 2/3: Generating audio..."
                                                           " (This may take a while)")
        print(f"[{job_id}] Starting Step 2: Audio Generation")
        await generate_audio_from_blocks(text_input_dir=audio_input_dir,
                                         audio_output_blocks_dir=audio_output_blocks_dir)
        print(f"[{job_id}] Finished Step 2: Audio files generated.")

        # --- Step 3: Concatenate audio blocks ---
        JobManager.update_job_status(job_id, "processing", "Step 3/3: Combining audio files...")
        print(f"[{job_id}] Starting Step 3: Concatenation")
        concatenate_audio_blocks(base_audio_folder=audio_output_blocks_dir, final_audio_dir=final_audio_dir)
        print(f"[{job_id}] Finished Step 3: Final audiobook created.")

        # --- Final Step: Mark as complete ---
        JobManager.update_job_status(job_id, "complete", "Your audiobook is ready for download!")
        print(f"[{job_id}] Job completed successfully.")

    except Exception as e:
        print(f"[{job_id}] An error occurred in the pipeline: {e}")
        JobManager.update_job_status(job_id, "error", f"An error occurred: {e}")