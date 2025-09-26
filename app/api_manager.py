import asyncio
import re
import os
from pathlib import Path
from typing import List, Tuple, Union

try:
    from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError
except ImportError:
    class ResourceExhausted(Exception): pass
    class GoogleAPICallError(Exception): pass

# --- API Key Manager ---
class ApiKeyManager:
    def __init__(self, api_keys: List[str]):
        self.api_keys = [key for key in api_keys if key]
        if not self.api_keys:
            raise ValueError("No API keys provided to ApiKeyManager.")
        self.current_key_index = 0
        self.lock = asyncio.Lock()  # Protects access to the key index

    async def get_key_for_processing(self) -> Tuple[Union[str, None], int]:
        """Returns the current API key and its original index, or (None, -1) if all keys are exhausted."""
        async with self.lock:
            if self.current_key_index >= len(self.api_keys):
                return None, -1
            return self.api_keys[self.current_key_index], self.current_key_index

    async def report_quota_error(self, failed_key_index: int):
        """
        Reports a quota error for a specific key index. Switches to the next key
        if the failed key is still the currently active one.
        """
        async with self.lock:
            # Only advance the key if the error is for the *current* key.
            # This prevents a race condition where multiple tasks failing on the same
            # old key would cause us to skip multiple fresh keys.
            if self.current_key_index == failed_key_index:
                old_key_str_for_log = self.api_keys[self.current_key_index][-4:]
                self.current_key_index += 1
                if self.current_key_index < len(self.api_keys):
                    new_key_str_for_log = self.api_keys[self.current_key_index][-4:]
                    print(
                        f"Key ...{old_key_str_for_log} exhausted. Switching to API Key #{self.current_key_index + 1}"
                        f" (ending ...{new_key_str_for_log}).")
                else:
                    print(f"Key ...{old_key_str_for_log} exhausted. All API keys have now been tried.")

#    def are_all_keys_exhausted(self) -> bool:
#        """Checks if all available API keys have been marked as exhausted."""
#        # This can be called without a lock as it's a simple read.
#        return self.current_key_index >= len(self.api_keys)

def is_quota_error(e: Exception) -> bool:
    actual_error = e.__cause__ if e.__cause__ else e
    error_str = str(actual_error).upper()
    if isinstance(actual_error, ResourceExhausted):
        return True
    if "429" in error_str and ("RESOURCE_EXHAUSTED" in error_str or "QUOTA" in error_str or "RATE LIMIT" in error_str):
        return True
    if isinstance(actual_error, GoogleAPICallError) and getattr(actual_error, 'code', None) == 429:
        return True
    return False

def natural_sort_key(text_to_sort: str):
    return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', text_to_sort)]

def get_api_keys() -> List[str]:
    """Finds, sorts, and returns all GEMINI_API_KEYs from environment variables."""
    api_key_names = [key for key in os.environ if key.startswith("GEMINI_API_KEY")]
    sorted_key_names = sorted(api_key_names, key=natural_sort_key)
    return [os.environ.get(key_name) for key_name in sorted_key_names]