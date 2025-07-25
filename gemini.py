import asyncio
import mimetypes  # Not directly used in this snippet, but was in original
import os
import re
import struct
import time
from pathlib import Path
from typing import Dict, Union, List, Tuple  # Added Tuple

from google import genai
from google.genai import types

try:
    from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError
except ImportError:
    # Define dummy exceptions if google.api_core is not available,
    # though it should be with google-generativeai
    class ResourceExhausted(Exception):
        pass


    class GoogleAPICallError(Exception):
        pass

# --- Configuration ---
INPUT_DIR = Path(r"C:\Users\rafae\PycharmProjects\gen-audio-maker\audio-input")  # Example path
OUTPUT_DIR = Path(r"C:\Users\rafae\PycharmProjects\gen-audio-maker\audio-output")  # Example path
MAX_CONCURRENT_REQUESTS = 3
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"

# Add your style instruction here
STYLE_INSTRUCTION = "Leia em uma voz grave e calma."
# --- Rate Limiting Configuration ---
API_REQUEST_LIMIT = 3
API_REQUEST_WINDOW_SECONDS = 60

request_timestamps: List[float] = []
rate_limit_lock = asyncio.Lock()


# --- API Key Manager ---
class ApiKeyManager:
    def __init__(self, api_keys: List[str]):
        self.api_keys = [key for key in api_keys if key]
        if not self.api_keys:
            # This case should ideally be caught before creating the manager,
            # but it's a good safeguard.
            raise ValueError("No API keys provided to ApiKeyManager.")
        self.current_key_index = 0
        self.quota_errors_this_key_session = 0
        self.lock = asyncio.Lock()  # Protects access to index and error count

    async def get_key_for_processing(self) -> Tuple[Union[str, None], int]:
        """Returns the current API key and its original index, or (None, -1) if all keys are exhausted."""
        async with self.lock:
            if self.current_key_index >= len(self.api_keys):
                return None, -1
            return self.api_keys[self.current_key_index], self.current_key_index

    async def report_quota_error(self) -> bool:
        """
        Reports a quota error for the current key.
        Switches key if the threshold (2 errors) is met.
        Returns True if a key switch occurred (or all keys became exhausted), False otherwise.
        """
        async with self.lock:
            if self.current_key_index >= len(self.api_keys):  # Already out of keys
                return True  # Effectively, no key to switch from, but problem persists

            current_key_for_log = self.api_keys[self.current_key_index][-4:]
            self.quota_errors_this_key_session += 1
            print(
                f"Quota error reported. Total for current key session (...{current_key_for_log}): {self.quota_errors_this_key_session}")

            if self.quota_errors_this_key_session >= 2:
                old_key_idx_for_log = self.current_key_index
                old_key_str_for_log = self.api_keys[old_key_idx_for_log][-4:]
                self.current_key_index += 1
                self.quota_errors_this_key_session = 0  # Reset for the new key session

                if self.current_key_index < len(self.api_keys):
                    new_key_str_for_log = self.api_keys[self.current_key_index][-4:]
                    print(
                        f"Key ...{old_key_str_for_log} exhausted (2 quota errors). Switching to API Key #{self.current_key_index + 1} (ending ...{new_key_str_for_log}).")
                else:
                    print(
                        f"Key ...{old_key_str_for_log} exhausted (2 quota errors). All API keys have now been tried and exhausted.")
                return True  # Key was switched or all keys are now exhausted
            return False  # Key not switched, just error count incremented

    def are_all_keys_exhausted(self) -> bool:
        """Checks if all available API keys have been marked as exhausted."""
        # Called without lock as read-only on index, but ensure index changes are locked.
        # For safety, can acquire lock if concerned about race with increment.
        # async with self.lock:
        return self.current_key_index >= len(self.api_keys)


# --- Helper Functions (save_binary_file, parse_audio_mime_type, convert_to_wav - unchanged) ---
def save_binary_file(file_name: Union[str, Path], data: bytes):
    with open(file_name, "wb") as f:
        f.write(data)


def parse_audio_mime_type(mime_type: str) -> Dict[str, Union[int, None]]:
    bits_per_sample = 16;
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
    # Adding a period and a space for better separation, hoping the model interprets it as an instruction.
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
    except Exception as e:  # Catch errors during API call setup (auth, model name etc.)
        # Re-raise preserving the original exception as the cause for better diagnosis
        raise RuntimeError(
            f"API call setup failed for {Path(output_audio_path).name}. Original error: {type(e).__name__}") from e

    audio_data_found = False
    for chunk in response_chunks:  # This can also raise errors if the stream fails
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


# --- Rate Limiting Logic (wait_for_rate_limit_slot - unchanged) ---
async def wait_for_rate_limit_slot():
    while True:
        async with rate_limit_lock:
            now = time.monotonic()
            while request_timestamps and request_timestamps[0] <= now - API_REQUEST_WINDOW_SECONDS:
                request_timestamps.pop(0)
            if len(request_timestamps) < API_REQUEST_LIMIT:
                request_timestamps.append(now);
                return
            time_to_wait = max(request_timestamps[0] + API_REQUEST_WINDOW_SECONDS - now, 0.001)
        await asyncio.sleep(time_to_wait)


# --- Asynchronous Task Processing ---
async def process_text_file_core(txt_file_path: Path, output_audio_path: Path, semaphore: asyncio.Semaphore,
                                 api_key: str):
    """Core processing for a single file with a given API key."""
    async with semaphore:
        input_filename = txt_file_path.name
        with open(txt_file_path, 'r', encoding='utf-8') as f:
            text_content = f.read().strip()
        if not text_content:
            print(f"Warning: '{input_filename}' is empty. Skipping.")
            return True  # Indicate success (nothing to do)

        await wait_for_rate_limit_slot()
        key_suffix = api_key[-4:] if api_key and len(api_key) >= 4 else "N/A"
        print(f"'{input_filename}' converting (using API key ...{key_suffix})...")

        await asyncio.to_thread(
            sync_generate_and_save_tts, api_key, text_content, output_audio_path
        )
        print(f"'{output_audio_path.name}' is ready.")
        converted_dir = INPUT_DIR / "converted"
        converted_dir.mkdir(parents=True, exist_ok=True)
        try:
            txt_file_path.rename(converted_dir / txt_file_path.name)
        except OSError as move_err:
            print(f"Warning: Created '{output_audio_path.name}', but failed to move '{input_filename}': {move_err}")
        return True  # Indicate success


async def try_process_file_with_managed_keys(
        txt_file_path: Path,
        output_audio_path: Path,
        semaphore: asyncio.Semaphore,
        key_manager: ApiKeyManager
):
    """Processes a single file, retrying with new keys from ApiKeyManager upon quota errors."""
    max_total_attempts_for_file = len(key_manager.api_keys) * 2 + 1  # Max 2 tries per key for this file + buffer

    for attempt_num in range(1, max_total_attempts_for_file + 1):
        if key_manager.are_all_keys_exhausted():
            print(f"All API keys exhausted. Cannot process '{txt_file_path.name}'.")
            break  # Exit loop for this file

        current_api_key, key_idx_for_log = await key_manager.get_key_for_processing()

        if current_api_key is None:  # Should be caught by are_all_keys_exhausted, but defensive
            print(f"No API key available from manager for '{txt_file_path.name}'. Skipping.")
            break

        key_identifier = f"Key #{key_idx_for_log + 1} (...{current_api_key[-4:]})"
        print(f"Attempting '{txt_file_path.name}' with {key_identifier} (File Attempt #{attempt_num}).")

        try:
            # process_text_file_core will raise exceptions on failure
            await process_text_file_core(txt_file_path, output_audio_path, semaphore, current_api_key)
            print(f"Successfully processed '{txt_file_path.name}' with {key_identifier}.")
            return  # File processed successfully

        except Exception as e_wrapper:
            actual_error = e_wrapper.__cause__ if e_wrapper.__cause__ else e_wrapper
            error_str = str(actual_error).upper()
            is_quota_error = False

            # More specific check for Google's ResourceExhausted exception
            if isinstance(actual_error, ResourceExhausted):
                is_quota_error = True
            elif "429" in error_str and "RESOURCE_EXHAUSTED" in error_str:  # Matches user log
                is_quota_error = True
            elif "429" in error_str and ("QUOTA" in error_str or "RATE LIMIT" in error_str):
                is_quota_error = True
            # Add other specific Gemini API error types if known for quota
            elif isinstance(actual_error, GoogleAPICallError) and actual_error.code == 429:  # Check .code if it exists
                is_quota_error = True

            if is_quota_error:
                short_error_msg = str(actual_error).splitlines()[0]
                print(f"Quota-related error with {key_identifier} for '{txt_file_path.name}': {short_error_msg}")
                await key_manager.report_quota_error()  # This might switch the key

                if key_manager.are_all_keys_exhausted():
                    print(f"All keys exhausted after quota error on '{txt_file_path.name}'.")
                    break  # Stop trying this file
                # Loop will continue, and next iteration will get current (possibly new) key
                print(f"Retrying '{txt_file_path.name}' (will use current/next available key).")
            else:
                print(f"Non-quota error processing '{txt_file_path.name}' with {key_identifier}: {e_wrapper}")
                print(f"Skipping further attempts for '{txt_file_path.name}'.")
                break  # Non-quota error, give up on this file

    else:  # Loop finished without returning (i.e., max attempts reached or broke due to exhaustion)
        print(f"Failed to process '{txt_file_path.name}' after multiple attempts or all keys exhausted.")


def natural_sort_key(path_obj: Path):
    return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', path_obj.name)]


# --- Main Orchestration ---
async def main():
    api_key_names = ["GEMINI_API_KEY5", "GEMINI_API_KEY2", "GEMINI_API_KEY3", "GEMINI_API_KEY4", "GEMINI_API_KEY"
                     , "GEMINI_API_KEY6", "GEMINI_API_KEY7", "GEMINI_API_KEY8", "GEMINI_API_KEY9"]
    raw_api_keys = [os.environ.get(key_name) for key_name in api_key_names]

    # Initialize ApiKeyManager; it will filter out None keys internally
    try:
        key_manager = ApiKeyManager(raw_api_keys)
    except ValueError:  # Raised if raw_api_keys results in an empty list for the manager
        print(f"Error: No Gemini API keys found. Please set at least one of {', '.join(api_key_names)}.")
        return

    print(f"Initialized with {len(key_manager.api_keys)} API key(s).")

    if not INPUT_DIR.exists() or not INPUT_DIR.is_dir():
        print(f"Error: Input directory '{INPUT_DIR}' does not exist.")
        return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (INPUT_DIR / "converted").mkdir(parents=True, exist_ok=True)

    txt_files = sorted(list(INPUT_DIR.glob("block*.txt")), key=natural_sort_key)
    if not txt_files:
        print(f"No 'block*.txt' files found in '{INPUT_DIR}'.");
        return
    print(f"Found {len(txt_files)} .txt files to process.")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    tasks = [
        try_process_file_with_managed_keys(
            txt_file_path,
            OUTPUT_DIR / (txt_file_path.stem + ".wav"),
            semaphore,
            key_manager
        ) for txt_file_path in txt_files
    ]
    await asyncio.gather(*tasks)
    print("TTS processing finished for all files!")


if __name__ == "__main__":
    asyncio.run(main())