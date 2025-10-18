from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.responses import HTMLResponse
from app.processor import run_conversion_pipeline, create_job_folders
from app.story_creator import run_story_creation_pipeline
from app.job_manager import JobManager
from pathlib import Path
from pydantic import BaseModel, Field
import uuid

class StoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    summary: str = Field(..., min_length=10, max_length=2000)
    chapters: int = Field(..., gt=0, le=20)
    chars_per_chapter: int = Field(..., gt=100, le=10000)

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# Define a root directory for all job-related data
DATA_DIR = Path(__file__).resolve().parent.parent / "data/job-data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/create-job")
async def create_job(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Accepts a PDF file, creates a unique job, saves the file,
    and starts the conversion pipeline in the background.
    """

    job_id = str(uuid.uuid4())

    try:

        # Create the necessary directory structure for this job
        (text_input_dir, audio_input_dir, audio_converted_dir, audio_output_blocks_dir,
         final_audio_dir) = create_job_folders(base_data_dir=DATA_DIR, job_id=job_id)

        # Save the uploaded file
        source_pdf_path = text_input_dir / file.filename
        with open(source_pdf_path, "wb") as buffer:
            buffer.write(await file.read())
        print(f"File '{file.filename}' saved for job {job_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize job: {e}")

    # Set the initial status
    JobManager.update_job_status(job_id=job_id, status="accepted", message="Job accepted and queued.")

    # Add the long-running task to the background
    background_tasks.add_task(run_conversion_pipeline, job_id=job_id, text_input_dir=text_input_dir,
                              audio_input_dir=audio_input_dir, audio_converted_dir=audio_converted_dir,
                              audio_output_blocks_dir=audio_output_blocks_dir, final_audio_dir=final_audio_dir)

    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """
    Retrieves the current status of a conversion job.
    """
    try:
        return JobManager.retrieve_job_status(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job ID not found")

@app.post("/create-story-job")
async def create_story_job(background_tasks: BackgroundTasks, request: StoryRequest):
    job_id = str(uuid.uuid4())
    try:
        # Create a simpler folder structure for story jobs
        job_dir = DATA_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize story job: {e}")

    JobManager.update_job_status(job_id=job_id, status="accepted", message="Story job accepted.")
    background_tasks.add_task(run_story_creation_pipeline, job_id=job_id, base_data_dir=DATA_DIR, story_params=request.dict())
    return {"job_id": job_id}


@app.get("/download/{job_id}")
async def download_file(job_id: str):
    job_dir = DATA_DIR / job_id

    # Check for story PDF first
    story_dir = job_dir / "final-story"
    if story_dir.exists():
        # Find the first PDF in the directory
        pdf_files = list(story_dir.glob("*.pdf"))
        if pdf_files:
            return FileResponse(path=pdf_files[0], media_type='application/pdf', filename=pdf_files[0].name)

    # Check for audiobook WAV next
    audio_dir = job_dir / "audio-output" / "final-audio"
    audio_file = audio_dir / "final_audio.wav"
    print(audio_file)
    if audio_file.exists():
        return FileResponse(path=audio_file, media_type='audio/wav', filename='final_audio.wav')

    # If neither exists, raise an error
    raise HTTPException(status_code=404, detail="Final file not ready or job ID not found.")