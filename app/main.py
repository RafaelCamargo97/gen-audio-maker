from fastapi import FastAPI
from processor import run_conversion_pipeline, create_job_folders
from job_manager import JobManager
from pathlib import Path
import uuid

app = FastAPI()

# Define a root directory for all job-related data
DATA_DIR = Path(__file__).resolve().parent.parent / "data/job-data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/create-job")
async def create_job():

    #Upload File

    job_id = str(uuid.uuid4())

    JobManager.job_statuses(job_id=job_id, status="accepted", progress=0)

    (text_input_dir, audio_input_dir, audio_output_blocks_dir,
     final_audio_dir) = create_job_folders(base_data_dir=DATA_DIR, job_id=job_id)

    # save file in job structure

    run_conversion_pipeline(job_id, text_input_dir, audio_input_dir, audio_output_blocks_dir, final_audio_dir)

    return {"job_id": job_id}
