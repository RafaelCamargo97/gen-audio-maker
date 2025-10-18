import threading

class JobManager:

    job_statuses = {}
    _lock = threading.Lock()

    @classmethod
    def update_job_status(cls, job_id: str, status: str, message: str, progress: int = -1):
        """Updates the status and message for a given job."""
        with cls._lock:
            if job_id not in cls.job_statuses:
                cls.job_statuses[job_id] = {}

            cls.job_statuses[job_id]["status"] = status
            cls.job_statuses[job_id]["message"] = message

            if progress >= 0:
                cls.job_statuses[job_id]["progress"] = progress

    @classmethod
    def increment_job_progress(cls, job_id: str, increment: float):
        """Safely increments the progress for a given job."""
        with cls._lock:
            if job_id in cls.job_statuses:
                current_progress = cls.job_statuses[job_id].get("progress", 0)
                cls.job_statuses[job_id]["progress"] = current_progress + increment

    @classmethod
    def retrieve_job_status(cls, job_id: str):
        """Retrieves the status object for a given job."""
        with cls._lock:
            return cls.job_statuses.get(job_id, {}).copy()