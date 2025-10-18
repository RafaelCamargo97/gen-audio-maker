import asyncio
import os
import re
import struct
import time
from pathlib import Path
from typing import Dict, Union, List, Callable
from dotenv import load_dotenv
from google import genai
from google.genai import types
from app.api_manager import ApiKeyManager, is_quota_error, get_api_keys

try:
    from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError
except ImportError:
    class ResourceExhausted(Exception):
        pass

    class GoogleAPICallError(Exception):
        pass

# --- Configuration ---
load_dotenv()
MAX_CONCURRENT_REQUESTS = int(os.environ["MAX_CONCURRENT_REQUESTS"])
GEMINI_TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL")

# Add your style instruction here
#STYLE_INSTRUCTION = "Leia em uma voz grave e calma."
STYLE_INSTRUCTION = ""

# --- Rate Limiting Configuration ---
API_REQUEST_LIMIT = int(os.environ["API_REQUEST_LIMIT"])
API_REQUEST_WINDOW_SECONDS = int(os.environ["API_REQUEST_WINDOW_SECONDS"])
class RateLimiter:
    def __init__(self, limit: int = 3, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self.timestamps: List[float] = []
        self.lock = asyncio.Lock()

    async def wait_for_slot(self):
        while True:
            async with self.lock:
                now = time.monotonic()
                # Remove timestamps outside the window
                self.timestamps = [ts for ts in self.timestamps if ts > now - self.window]

                if len(self.timestamps) < self.limit:
                    self.timestamps.append(now)
                    return  # Slot acquired

                # Calculate time to wait for the oldest request to expire
                time_to_wait = max(self.timestamps[0] + self.window - now, 0.001)

            await asyncio.sleep(time_to_wait)

def save_binary_file(file_name: Union[str, Path], data: bytes):
    with open(file_name, "wb") as f:
        f.write(data)


def parse_audio_mime_type(mime_type: str) -> Dict[str, Union[int, None]]:
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.lower().split(";")
    for param_part in parts:
        param = param_part.strip()
        if param.startswith("audio/l"):
            try:
                bits_per_sample = int(param.split("l", 1)[1])
            except (ValueError, IndexError):
                pass
        elif param.startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError):
                pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    params = parse_audio_mime_type(mime_type)
    bps, sr = params["bits_per_sample"], params["rate"]
    if bps is None or sr is None: raise ValueError(f"MIME type parse error: {mime_type}")
    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(audio_data), b"WAVE", b"fmt ",
                         16, 1, 1, sr, sr * (bps // 8), bps // 8, bps, b"data", len(audio_data))
    return header + audio_data


# --- Core TTS Generation Logic ---
def sync_generate_and_save_tts(api_key: str, text_content: str, output_audio_path: Union[str, Path]):
    client = genai.Client(api_key=api_key)
    # Prepend the style instruction to the text_content.
    instructed_text_content = f"{STYLE_INSTRUCTION}. {text_content}"

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=instructed_text_content)])]
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Algenib")
            )))
    try:
        response_chunks = client.models.generate_content_stream(
            model=GEMINI_TTS_MODEL, contents=contents, config=generate_content_config)
    except Exception as e:
        raise RuntimeError(
            f"API call setup failed for {Path(output_audio_path).name}. Original error: {type(e).__name__}") from e

    audio_data_found = False
    for chunk in response_chunks:
        if (chunk.candidates and chunk.candidates[0].content and
                chunk.candidates[0].content.parts and chunk.candidates[0].content.parts[0].inline_data and
                chunk.candidates[0].content.parts[0].inline_data.data):
            inline_data = chunk.candidates[0].content.parts[0].inline_data
            if inline_data.mime_type.lower() == "audio/wav":
                final_audio_data = inline_data.data
            else:
                final_audio_data = convert_to_wav(inline_data.data, inline_data.mime_type)
            save_binary_file(output_audio_path, final_audio_data)
            audio_data_found = True
            break
        elif chunk.text:
            print(f"Warning: Text from TTS API for {Path(output_audio_path).name}: {chunk.text}")
    if not audio_data_found:
        raise RuntimeError(f"No audio data in API response stream for {Path(output_audio_path).name}")

# --- Asynchronous Worker and Processing Logic ---
async def process_file_attempt(
        txt_file_path: Path, output_audio_path: Path, audio_converted_dir: Path, api_key: str,
        rate_limiter: RateLimiter, progress_callback: callable
):
    """Core logic for a single file processing attempt. Separated to be wrapped by a semaphore."""
    input_filename = txt_file_path.name
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        text_content = f.read().strip()
    if not text_content:
        print(f"Warning: '{input_filename}' is empty. Skipping.")
        return  # Indicate success (nothing to do)

    await rate_limiter.wait_for_slot() # Cleaner call
    key_suffix = api_key[-4:]
    print(f"'{input_filename}' converting (using API key ...{key_suffix})...")

    await asyncio.to_thread(
        sync_generate_and_save_tts, api_key, text_content, output_audio_path
    )
    progress_callback()
    print(f"'{output_audio_path.name}' is ready.")
    try:
        txt_file_path.rename(audio_converted_dir / txt_file_path.name)
    except OSError as move_err:
        print(f"Warning: Created '{output_audio_path.name}', but failed to move '{input_filename}': {move_err}")


def is_quota_error(e: Exception) -> bool:
    """Checks if a given exception is a quota-related error."""
    actual_error = e.__cause__ if e.__cause__ else e
    error_str = str(actual_error).upper()

    if isinstance(actual_error, ResourceExhausted):
        return True
    if "429" in error_str and ("RESOURCE_EXHAUSTED" in error_str or "QUOTA" in error_str or "RATE LIMIT" in error_str):
        return True
    if isinstance(actual_error, GoogleAPICallError) and getattr(actual_error, 'code', None) == 429:
        return True

    return False


async def worker(
        name: str,
        queue: asyncio.Queue,
        key_manager: ApiKeyManager,
        semaphore: asyncio.Semaphore,
        stop_event: asyncio.Event,
        rate_limiter: RateLimiter,
        audio_output_blocks_dir: Path,
        audio_converted_dir: Path,
        progress_callback: callable
):
    """A worker task that processes files from the queue until it receives a sentinel (None)."""
    while True:

        txt_file_path: Path = await queue.get()

        # If we get the sentinel, acknowledge it and exit the loop.
        if txt_file_path is None:
            queue.task_done()
            break

        try:
            # Check for key exhaustion *before* attempting to process.
            current_api_key, key_idx = await key_manager.get_key_for_processing()

            if current_api_key is None:
                # All keys are exhausted. Re-queue the file and signal all workers to stop.
                print(f"[{name}] All keys exhausted. Re-queueing '{txt_file_path.name}' and signaling stop.")
                await queue.put(txt_file_path)
                queue.task_done()
                stop_event.set()
                continue

            output_audio_path = audio_output_blocks_dir / (txt_file_path.stem + ".wav")

            # Use the semaphore to limit true concurrency of API calls
            async with semaphore:
                await process_file_attempt(txt_file_path, output_audio_path, audio_converted_dir, current_api_key,
                                           rate_limiter, progress_callback)
        except Exception as e:
            if is_quota_error(e):
                short_error_msg = str(e.__cause__ or e).splitlines()[0]
                print(
                    f"[{name}] Quota error on '{txt_file_path.name}' with key #{key_idx + 1}. "
                    f"Re-queueing file. Error: {short_error_msg}"
                )
                await key_manager.report_quota_error(key_idx)
                await queue.put(txt_file_path)  # Re-queue the file for a later attempt
            else:
                print(
                    f"[{name}] NON-quota error on '{txt_file_path.name}'. Skipping file. Error: {e}"
                )
        finally:
            # CRITICAL: Signal that the task from the queue is done, regardless of outcome.
            queue.task_done()


def natural_sort_key(text_to_sort: str):
    return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', text_to_sort)]


# --- Main Orchestration ---
async def generate_audio_from_blocks(text_input_dir: Path, audio_output_blocks_dir: Path, audio_converted_dir: Path,
                                     progress_callback: callable):

    raw_api_keys = get_api_keys()

    try:
        key_manager = ApiKeyManager(raw_api_keys)
    except ValueError:
        print(f"Error: No Gemini API keys found. Please set at least one of {', '.join(raw_api_keys)}.")
        return

    print(f"Initialized with {len(key_manager.api_keys)} API key(s).")

    if not text_input_dir.exists() or not text_input_dir.is_dir():
        print(f"Error: Input directory '{text_input_dir}' does not exist.")
        return

    txt_files = sorted(text_input_dir.glob("block*.txt"), key=lambda path: natural_sort_key(path.name))

    if not txt_files:
        print(f"No 'block*.txt' files found in '{text_input_dir}'.")
        return

    print(f"Found {len(txt_files)} .txt files to process.")

    # --- Setup for worker pattern ---
    file_queue = asyncio.Queue()
    for txt_file in txt_files:
        await file_queue.put(txt_file)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    stop_event = asyncio.Event()

    # --- Create rate limiter ---
    rate_limiter = RateLimiter(API_REQUEST_LIMIT, API_REQUEST_WINDOW_SECONDS)

    # --- Create and start worker tasks ---
    worker_tasks = []
    for i in range(MAX_CONCURRENT_REQUESTS):
        task = asyncio.create_task(
            worker(f"Worker-{i + 1}", file_queue, key_manager, semaphore, stop_event, rate_limiter,
                   audio_output_blocks_dir, audio_converted_dir, progress_callback)
        )
        worker_tasks.append(task)

    # --- Wait for all files to be processed ---
    # This will block until `task_done()` has been called for every file
    # that was initially put into the queue.
    await file_queue.join()

    # --- Shutdown ---
    print("All initial files have been processed at least once. Finalizing...")

    for _ in worker_tasks:
        await file_queue.put(None)

    # Wait for all worker tasks to finish.
    await asyncio.gather(*worker_tasks, return_exceptions=True)

    # --- Final Status Report ---
    if file_queue.empty():
        print("TTS processing finished successfully for all files!")
    else:
        print(
            f"\nProcessing stopped because all API keys were exhausted. "
            f"{file_queue.qsize()} file(s) could not be processed:"
        )
        while not file_queue.empty():
            remaining_file = file_queue.get_nowait()
            print(f"  - {remaining_file.name}")