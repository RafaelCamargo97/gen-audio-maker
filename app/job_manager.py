class JobManager:

    job_statuses = {}

    @classmethod
    def update_job_status(cls, job_id: str, status: str, message: str):
        """Updates the status and message for a given job."""
        cls.job_statuses[job_id] = {
            "status": status,  # e.g., "accepted", "processing", "complete", "error"
            "message": message
        }

    @classmethod
    def retrieve_job_status(cls, job_id: str):
        """Retrieves the status object for a given job."""
        return cls.job_statuses[job_id]