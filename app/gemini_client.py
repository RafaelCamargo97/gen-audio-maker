# gemini_client.py
import os
from typing import List, Callable, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL")
if not GEMINI_TEXT_MODEL:
    raise ValueError("GEMINI_TEXT_MODEL environment variable not set.")


async def generate_story_with_memory(
    api_key: str,
    initial_prompt: str,
    chapter_prompts: List[str],
    progress_callback: Optional[Callable] = None,
) -> str:
    """
    Generate a multi-chapter story preserving short-term 'memory' by keeping
    an explicit list of Content objects as the conversation history.

    Uses the async client methods from the google-genai SDK:
      await client.aio.models.generate_content(...)

    Args:
        api_key: API key to initialize genai.Client
        initial_prompt: first prompt (planning / story outline)
        chapter_prompts: list of prompts to request chapters (can be batched prompts)

    Returns:
        The full concatenated story text (string).
    """
    client = genai.Client(api_key=api_key)

    chat_history: List[types.Content] = []

    initial_content = types.Content(
        role="user", parts=[types.Part.from_text(text=initial_prompt)]
    )

    print("Sending story plan prompt to Gemini (initial planning)...")
    plan_response = await client.aio.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=initial_content,
        config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=10000),
    )

    # Add the user's initial prompt to history
    chat_history.append(initial_content)

    # Prefer to append the model-returned content candidate if present.
    # If not present, fall back to creating a model Content from response.text.
    if getattr(plan_response, "candidates", None) and len(plan_response.candidates) > 0:
        chat_history.append(plan_response.candidates[0].content)

    else:
        chat_history.append(
            types.Content(role="model", parts=[types.Part.from_text(text=plan_response.text)])
        )

    if progress_callback:
        progress_callback()

    # Now iterate through chapter prompts, sending the accumulated history + new prompt.
    full_story_text = ""
    for idx, prompt in enumerate(chapter_prompts, start=1):
        print(f"Sending prompt for chapter batch {idx}/{len(chapter_prompts)}...")

        prompt_content = types.Content(
            role="user", parts=[types.Part.from_text(text=prompt)]
        )

        # Build the request contents: history + this new user prompt
        request_contents = [*chat_history, prompt_content]

        chapter_response = await client.aio.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=request_contents,
            config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=10000),
        )

        # Prefer the convenient .text property for the plain generated text
        chapter_text = getattr(chapter_response, "text", None)
        if chapter_text is None:
            # Fallback: attempt to pull from first candidate
            if getattr(chapter_response, "candidates", None) and len(chapter_response.candidates) > 0:
                # candidate.content might be a Content object — prefer its text representation if available
                candidate = chapter_response.candidates[0]
                chapter_text = getattr(candidate, "text", None) or getattr(candidate, "content", None)
                if isinstance(chapter_text, types.Content):
                    # build text from parts (safe fallback)
                    parts = []
                    for p in chapter_text.parts:
                        if getattr(p, "text", None):
                            parts.append(p.text)
                    chapter_text = "\n".join(parts)
            else:
                chapter_text = ""

        # Normalize to string
        if not isinstance(chapter_text, str):
            chapter_text = str(chapter_text)

        full_story_text += chapter_text + "\n\n"

        # Update history: append the user prompt and the model content (if present)
        chat_history.append(prompt_content)
        if getattr(chapter_response, "candidates", None) and len(chapter_response.candidates) > 0:
            chat_history.append(chapter_response.candidates[0].content)
        else:
            # fallback: add model content derived from the text
            chat_history.append(
                types.Content(role="model", parts=[types.Part.from_text(text=chapter_text)])
            )

        if progress_callback:
            progress_callback()

    print("Story generation complete.")
    return full_story_text
