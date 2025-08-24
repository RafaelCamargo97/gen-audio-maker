GenAI Audiobook & Video Creator
===============================

This project is a complete, multi-stage pipeline designed to transform a text document (PDF or .txt) into a full-length audiobook, and then set that audiobook to a seamlessly looping background video.

It leverages Google's powerful Gemini Text-to-Speech API for high-quality audio generation and uses robust Python libraries for media processing, ensuring an efficient and automated workflow from text to final video.

Features
--------

-   **End-to-End Automation:** A four-stage process that takes a single source file and produces a final video with minimal manual intervention.
-   **Intelligent Text Processing:** Automatically splits large text documents into smaller, manageable chunks without cutting off sentences.
-   **High-Performance TTS Generation:** Uses an asynchronous, concurrent processing model to convert text to speech rapidly.
-   **Robust API Key Management:** Intelligently cycles through multiple Gemini API keys to overcome rate limits and quota exhaustion, maximizing throughput.
-   **Seamless Media Looping:** Creates long-form audio and video by concatenating shorter clips with smooth crossfades, perfect for long audiobook formats.
-   **Flexible and Configurable:** Key parameters like character limits, concurrency, and output duration can be easily adjusted within the scripts.

How It Works: The Four-Stage Pipeline
-------------------------------------

The project operates as a sequential pipeline. You run each script in order, and the output of one stage becomes the input for the next.

codeMermaid

```
graph TD
    A[Source .PDF/.TXT File] --> B{Stage 1: Text Preparation};
    B --> C[Numbered blockX.txt Files];
    C --> D{Stage 2: Text-to-Speech};
    D --> E[Numbered blockX.wav Files];
    E --> F{Stage 3: Audio Concatenation};
    F --> G[Single whole_audiobook.wav];
    G & H[Background video.mp4] --> I{Stage 4: Video Assembly};
    I --> J[Final video_final.mp4];

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style J fill:#ccf,stroke:#333,stroke-width:2px
```

#### Stage 1: Text Preparation (process_text.py)

This script acts as the preprocessor. It finds your source document, reads all the text, and prepares it for the Text-to-Speech engine.

-   **Input:** A single .pdf or .txt file located in the text-input folder.

    -   **Process:**

    -   Extracts all text content from the source file.

        -   Cleans up line breaks and whitespace.

        -   Splits the entire text into smaller blocks (e.g., 4000 characters each). The splitting logic is sentence-aware, meaning it will not cut a sentence in half.

    -   **Output:** A series of numbered text files (block1.txt, block2.txt, etc.) in the audio-input folder.

#### Stage 2: Text-to-Speech Generation (generate_audio.py)

This is the core engine of the project. It takes the text blocks and converts them into individual audio files using the Gemini API.

-   **Input:** The blockX.txt files from the audio-input folder.

    -   **Process:**

    -   It creates a pool of asynchronous "workers" to process files concurrently.

        -   It manages a list of your Gemini API keys. When one key hits its rate limit (quota exhausted), the script automatically switches to the next available key.

        -   A semaphore limits the number of simultaneous API requests to avoid overwhelming the service.

        -   Each text block is sent to the Gemini TTS API and the resulting audio is saved as a .wav file.

    -   **Output:** A series of numbered audio files (block1.wav, block2.wav, etc.) in the audio-output folder. Processed text files are moved to audio-input/converted.

#### Stage 3: Audio Concatenation (concatenate_audio.py)

This script assembles the individual audio snippets into a single, cohesive audiobook file.

-   **Input:** The blockX.wav files from the audio-output folder.

    -   **Process:**

    -   Numerically sorts all the .wav files to ensure they are in the correct order.

        -   Adds a short, configurable pause (e.g., 350ms) between each audio clip to create natural breaks.

        -   Concatenates all clips and pauses into one long audio file.

    -   **Output:** A single whole_audiobook.wav file saved in the audio-output/whole-audiobook subfolder.

#### Stage 4: Video Assembly (create_video.py)

The final stage takes your complete audiobook and a background video, combining them into a final product.

-   **Input:**

    -   A background video file (e.g., video.mp4) in the media folder.

    -  The final audiobook file (e.g., audio.mp3 or .wav) in the media folder. (You will need to move the file from Stage 3 here).

    -   **Process:**

    -   Loops the background video seamlessly using a crossfade effect until it reaches a target duration (e.g., 1 hour).

        -   Attaches the audiobook to the looped video, replacing any original audio.

    -   **Output:** A final video_final.mp4 file in the media folder.

Getting Started
---------------

Follow these steps to set up and run the project.

### Prerequisites

-   Python 3.8 or higher

- pip for installing packages
- git (optional, for cloning the repository)

### 1\. Project Structure

Your project must follow this folder structure for the scripts to work correctly:

codeCode

```
project-folder/
├── data/
│   ├── text-input/
│   │   └── my_book.pdf
│   ├── audio-input/            # STAGE 1 OUTPUT / STAGE 2 INPUT
│   └── audio-output/           # STAGE 2 OUTPUT / STAGE 3 INPUT
│       └── whole-audiobook/    # STAGE 3 OUTPUT
├── media/
│    ├── video.mp4           # Your background video for Stage 4
│    └── audio.mp3           # Your final audiobook for Stage 4
├── src/
│   ├── __init__.py                  # Good practice, can be empty
│   ├── gemini_audiobook_creator.py      # Renamed for clarity
│   ├── pdf_cleaner.py
│   ├── pdf_handler.py
│   ├── wav_handler.py
│   └── video_loop.py
│
├── .gitignore
├── README.md
└── requirements.txt
```

### 2\. Install Dependencies

Install all the necessary Python libraries using the provided requirements.txt file.

codeBash

```
pip install -r requirements.txt
```
This will install google-generativeai, pydub, moviepy, and PyPDF2.

### 3\. Configure API Keys

The Text-to-Speech script requires Google Gemini API keys.

-   Obtain one or more API keys from Google AI Studio [Google AI Studio](https://www.google.com/url?sa=E&q=https%3A%2F%2Faistudio.google.com%2Fapp%2Fapikey).

    -   Set them as environment variables. This is the most secure way to handle keys. The script is configured to look for variables named GEMINI_API_KEY, GEMINI_API_KEY2, GEMINI_API_KEY3, etc.

    **On Windows (Command Prompt):**

    codeCmd

    ```
    set GEMINI_API_KEY="YOUR_FIRST_API_KEY"
    set GEMINI_API_KEY2="YOUR_SECOND_API_KEY"
    ```

    **On macOS/Linux:**

    codeBash

    ```
    export GEMINI_API_KEY="YOUR_FIRST_API_KEY"
    export GEMINI_API_KEY2="YOUR_SECOND_API_KEY"
    ```

### 4\. Running the Pipeline

Execute the scripts one by one in the correct order.

**Step 1: Prepare the Text**\
Place your .pdf or .txt file in the text-input folder and run:

codeBash

```
python process_text.py
```

This will create blockX.txt files in audio-input.

**Step 2: Generate the Audio**\
Run the main TTS script. This may take a long time depending on the amount of text.

codeBash

```
python generate_audio.py
```

This will create blockX.wav files in audio-output.

**Step 3: Concatenate the Audio Clips**

codeBash

```
python concatenate_audio.py
```

This will create whole_audiobook.wav in audio-output/whole-audiobook.

**Step 4: Assemble the Final Video**

-   **Move the audiobook:** Copy whole_audiobook.wav from its folder into the media folder. You can rename it to audio.mp3 or audio.wav.

    -   **Add background video:**Place your desired background video (e.g., video.mp4) in the media folder.

    -   Run the final script:

    codeBash

    ```
    python create_video.py
    ```

This will create video_final.mp4 in the media folder.

Configuration
-------------

You can customize the behavior by editing the configuration variables at the top of each script:

-   **process_text.py**:

    -   CHARACTER_LIMIT: Max characters per text block. Gemini has limits, so 4000-4500 is a safe range.

    -   **generate_audio.py**:

    -   MAX_CONCURRENT_REQUESTS: Number of parallel API calls. Be mindful of API rate limits. 3 to 5 is a good starting point.

        -   STYLE_INSTRUCTION: Add a string to prepend a reading style instruction to every text block (e.g., "Read in a calm, deep voice.").

    -   **concatenate_audio.py**:

    -   pause = AudioSegment.silent(duration=350): Change 350 to your desired pause length in milliseconds between sentences.

    -   **create_video.py**:

    -   LOOP_DURATION_SECONDS: The total length of the final video in seconds (e.g.,3600 for 1 hour).

        -   CROSSFADE_TIME: The duration of the fade effect between video/audio loops.