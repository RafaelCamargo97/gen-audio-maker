# AI Content Creator: Audiobook & Story Generator

This web application leverages the power of Google's Gemini API to serve as a versatile content creation tool. It can transform PDF documents into full-length audiobooks and generate original, multi-chapter stories from a simple user prompt. The application is built with a responsive FastAPI backend and a dynamic vanilla JavaScript frontend.

![Screenshot of the application's UI](placeholder.png)

## ✨ Features

*   **PDF to Audiobook Conversion:**
    *   Upload any PDF file.
    *   Automatically splits text into intelligent blocks for high-quality TTS.
    *   Generates audio for each block concurrently for speed.
    *   Combines audio blocks into a single downloadable `.wav` file.
*   **AI Story Generation:**
    *   Provide a title, summary, and chapter details to generate a unique story.
    *   Uses a conversational AI session to maintain context and memory throughout the writing process.
    *   Generates a clean, downloadable `.pdf` of the final story.
*   **Dynamic User Interface:**
    *   Clean, tabbed interface to switch between tools.
    *   Real-time progress bar with percentage updates for long-running jobs.
    *   Asynchronous job processing—the UI remains responsive while the backend works.
*   **Robust Backend:**
    *   Built with modern FastAPI.
    *   Manages multiple Gemini API keys, automatically switching when a quota is exhausted.
    *   Built-in rate limiting to respect API usage policies.

## 🛠️ Technology Stack

*   **Backend:**
    *   Python 3.9+
    *   FastAPI (for the web framework and background tasks)
    *   Uvicorn (as the ASGI server)
    *   Google Generative AI SDK (`google-generativeai`)
    *   PyPDF2 (for PDF text extraction)
    *   Pydub (for audio manipulation)
    *   FPDF2 (for PDF generation)
*   **Frontend:**
    *   HTML5
    *   CSS3
    *   Vanilla JavaScript (no frameworks)

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running on your local machine.

### Prerequisites

*   Python 3.9 or higher.
*   Git (for cloning the repository).

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://https://github.com/RafaelCamargo97/gen-audio-maker.git
    cd gen-audio-maker
    ```

2.  **Create and activate a virtual environment:**
    *   **Windows:**
        ```bash
        python -m venv .venv
        .\.venv\Scripts\activate
        ```
    *   **macOS / Linux:**
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure your environment variables:**
    *   Make a copy of the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Open the `.env` file and add your credentials and settings.

### Environment Variables (`.env`)

This file is crucial for the application to run.

*   `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, etc.: Your Google AI Studio API keys. You must have at least one. The application will use them in numerical order.
*   `GEMINI_TTS_MODEL`: The model for Text-to-Speech. Defaults to `"models/text-to-speech"`.
*   `GEMINI_TEXT_MODEL`: The model for text generation. We recommend `"gemini-1.5-pro-latest"`.
*   `MAX_CONCURRENT_REQUESTS`: The number of simultaneous API requests for audio generation. A value between 5 and 10 is recommended.
*   `API_REQUEST_LIMIT`: The maximum number of API calls allowed in the time window (e.g., 30).
*   `API_REQUEST_WINDOW_SECONDS`: The time window for the rate limit in seconds (e.g., 60).

### Running the Application

1.  With your virtual environment activated, start the server from the root directory:
    ```bash
    uvicorn app.main:app --reload
    ```
2.  Open your web browser and navigate to `http://127.0.0.1:8000`.

## 📂 Project Structure

The project is organized with a clear separation of concerns:

```
/gen-audio-maker/
├── app/                  # Main application source code
│   ├── static/           # CSS and JavaScript files
│   ├── templates/        # HTML templates
│   ├── api_manager.py    # Manages Gemini API keys and errors
│   ├── gemini_client.py  # Handles text generation with memory
│   ├── main.py           # FastAPI server, endpoints, and UI serving
│   └── ...               # Other processing modules
├── assets/
│   └── fonts/            # Contains the DejaVuSans.ttf font for PDF generation
├── data/
│   └── job-data/         # Dynamically created folders for each job
├── prompts/              # Text files containing prompts for the AI
├── .env                  # Your local environment variables (ignored by git)
├── .env.example          # Template for the .env file
└── requirements.txt      # Python dependencies
```

## ⚙️ How It Works

The application uses an asynchronous, non-blocking architecture.

1.  The **Frontend** sends a job request (either audiobook or story) to the FastAPI **Backend**.
2.  The Backend creates a unique Job ID, saves any necessary files, and immediately returns the `job_id` to the frontend.
3.  The actual processing is handed off to a **Background Task**, ensuring the server remains responsive.
4.  The Frontend uses the `job_id` to **Poll** a `/status/{job_id}` endpoint every few seconds.
5.  The Backend's **JobManager** updates the job's status and progress percentage as the background task completes its steps.
6.  When the frontend receives a "complete" status, it displays a download link pointing to `/download/{job_id}`.

## 🎯 Project Scope & Local Execution

This application was developed as a high-fidelity **Proof of Concept (PoC)** to demonstrate the end-to-end workflow of generating AI content. It is designed and optimized for **local execution** on a personal machine.

Several architectural choices were made for simplicity and rapid development, which are important to understand:

*   **In-Memory Job Management:** The `JobManager` stores all job statuses and progress in a simple Python dictionary. This data is volatile and will be **lost if the server restarts**.
*   **Built-in Background Tasks:** The application uses FastAPI's native `BackgroundTasks`. This is an excellent tool for in-process concurrency but is not as robust as a dedicated task queue. If the server process is terminated, any running tasks are lost.
*   **Monolithic Structure:** The same FastAPI server is responsible for both serving the frontend (HTML/JS) and handling the backend API logic.

As such, it is perfectly suited for personal use, demonstration, and as a strong foundation for a more complex, production-ready system.

## 🏛️ Current Architecture (Local Execution)

The application follows a monolithic client-server architecture with asynchronous background processing for long-running tasks. The entire process is orchestrated by a single FastAPI server.

### System Design Diagram

```
[User's Browser] <------------------------------------+
     |                                                 |
     | 1. GET / (Request for Web Page)                 | 8. Polling: GET /status/{job_id}
     |                                                 |
     v                                                 |
+-------------------------------------------------------------+
|                      FastAPI Server (Uvicorn)                 |
|                                                             |
|   +---------------------+      +------------------------+   |
|   |  Frontend Serving   |----->|   API Endpoints        |   |
|   | (StaticFiles, Jinja2)|      | (/create-job, /status) |   |
|   +---------------------+      +----------+-------------+   |
|       ^                                   | 2. POST /create-job
|       | 7. Return HTML/JS/CSS             |    (Returns job_id immediately)
|       |                                   |
|       |                                   v
|       +---------------------------+  +------------------------+
|       |  In-Memory Job Manager    |< |  BackgroundTasks Module|
|       |  (job_statuses dict)      |  | (Runs conversion tasks |
|       |  (Thread-safe with Lock)  |  |  after response is sent)|
|       +---------------------------+  +----+-------------------+
|               ^   ^                        | 3. Calls processor
|               |   |                        v
|               |   +-----------------+------+------------------+
|               | 6. Read Status      |  Processing Modules     |
|               |                     |                         |
|               +---------------------+ (pdf_handler, gemini_*, |
|                 5. Update Status    |  story_creator, etc.)   |
|                                     +----------+--------------+
|                                                | 4. Writes files
|                                                v
|                                     +------------------------+
|                                     |      File System       |
|                                     | (data/job-data/{job_id})|
|                                     +------------------------+
+-------------------------------------------------------------+

```

### Component Breakdown

1.  **Frontend (Client):** A vanilla JavaScript application running in the user's browser. It handles file uploads, user input, and makes API calls. It uses a **polling** mechanism to repeatedly ask the server for the status of a job.

2.  **FastAPI Server:** The core of the application.
    *   **Frontend Serving:** It serves the initial `index.html` via Jinja2 templates and all static assets (`.css`, `.js`) via `StaticFiles`.
    *   **API Endpoints:** It exposes endpoints to create new jobs (`/create-job`, `/create-story-job`), check job status (`/status/{job_id}`), and download the final product (`/download/{job_id}`).

3.  **Job Processing (`BackgroundTasks`):** When a new job is created, FastAPI immediately returns a `job_id` and schedules the long-running task (e.g., `run_conversion_pipeline`) to run in the background. This "fire and forget" model keeps the API responsive.

4.  **State Management (`JobManager`):** A simple, in-memory Python class that holds a dictionary of all job statuses. It is the single source of truth for job progress. A `threading.Lock` is used to prevent race conditions, ensuring that concurrent progress updates from audio generation workers are handled safely.

5.  **File System:** All data related to a specific job (the uploaded PDF, intermediate text blocks, final audio/PDF files) is stored in a uniquely named folder within `data/job-data/`, using the `job_id` as the folder name. This isolates each job's data.
```

---

### **3. New Section: Future Improvement (AWS Placeholder)**

This section is intentionally left as a placeholder, exactly as you requested, setting the stage for future planning.

```markdown
## ☁️ Future Improvement: AWS Production Architecture

While the current design is optimized for local execution, the application is built with modular components that make it a strong candidate for a scalable, cloud-native architecture on AWS. A potential system design for this would aim to address the limitations of the PoC (e.g., in-memory state, in-process task handling) by leveraging managed cloud services.

*[Future AWS architecture diagram and detailed component explanation to be added here.]*