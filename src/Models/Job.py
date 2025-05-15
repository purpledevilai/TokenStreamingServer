import os
from datetime import datetime
import uuid
from AWS.DynamoDB import get_item, put_item, delete_item, get_all_items_by_index
from pydantic import BaseModel
from typing import Optional
from enum import Enum

JOBS_TABLE_NAME = os.environ["JOBS_TABLE_NAME"]
JOBS_PRIMARY_KEY = os.environ["JOBS_PRIMARY_KEY"]

class JobStatus(str, Enum):
    queued = "queued"
    in_progress = "in_progress"
    error = "error"
    completed = "completed"

class Job(BaseModel):
    job_id: str
    owner_id: str
    status: JobStatus
    message: Optional[str] = None
    data: dict
    created_at: int
    updated_at: int


def job_exists(job_id: str) -> bool:
    return get_item(JOBS_TABLE_NAME, JOBS_PRIMARY_KEY, job_id) != None

def create_job(
        owner_id: str,
        status: str = JobStatus.queued,
        message: str = None,
        data: dict = {}
    ) -> Job:
    job_id = str(uuid.uuid4())
    created_at = int(datetime.now().timestamp())
    updated_at = created_at
    job = Job(
        job_id=job_id,
        owner_id=owner_id,
        status=status,
        message=message,
        data=data,
        created_at=created_at,
        updated_at=updated_at
    )
    put_item(JOBS_TABLE_NAME, job.model_dump())
    return job

def get_job(job_id: str) -> Job:
    item = get_item(JOBS_TABLE_NAME, JOBS_PRIMARY_KEY, job_id)
    if item == None:
        raise Exception(f"Job {job_id} not found", 404)
    return Job(**item)

def get_job_for_owner(job_id: str, owner_id: str) -> Job:
    job = get_job(job_id)
    if job.owner_id != owner_id:
        raise Exception(f"Job {job_id} not found", 404)
    return job

def save_job(job: Job) -> Job:
    job.updated_at = int(datetime.now().timestamp())
    put_item(JOBS_TABLE_NAME, job.model_dump())
    return job

def delete_job(job_id: str) -> None:
    delete_item(JOBS_TABLE_NAME, JOBS_PRIMARY_KEY, job_id)

def get_jobs_for_owner(owner_id: str) -> list[Job]:
    return [Job(**item) for item in get_all_items_by_index(JOBS_TABLE_NAME, "owner_id", owner_id)]