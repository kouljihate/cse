from datetime import datetime
from typing import Optional, Literal
from bson import ObjectId
from pydantic import BaseModel, Field, model_validator


class ActivityCreate(BaseModel):
    customer_id: str = Field(..., description="Customer user ID")
    service_id: str = Field(..., description="Service ID")
    assigned_employees: list[str] = Field(..., description="Employee IDs who get the tasks")
    status: Literal["pending", "in_progress", "completed", "cancelled"] = "pending"
    notes: Optional[str] = None


class ActivityUpdate(BaseModel):
    status: Optional[Literal["pending", "in_progress", "completed", "cancelled"]] = None
    notes: Optional[str] = None
    assigned_employees: Optional[list[str]] = None


class ActivityResponse(BaseModel):
    id: str = Field(alias="_id")
    customer_id: str
    customer_name: Optional[str] = None
    service_id: str
    service_name: Optional[str] = None
    assigned_employees: list[str] = []
    assigned_employee_names: list[str] = []
    status: str
    notes: Optional[str] = None
    task_count: int = 0
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def convert_object_id(cls, data):
        if isinstance(data, dict):
            for key in ("_id", "customer_id", "service_id"):
                if key in data and isinstance(data[key], ObjectId):
                    data[key] = str(data[key])
            if "assigned_employees" in data and data["assigned_employees"]:
                data["assigned_employees"] = [
                    str(e) if isinstance(e, ObjectId) else e
                    for e in data["assigned_employees"]
                ]
        return data
