from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from bson import ObjectId


class CompanySettingsUpdate(BaseModel):
    company_name: str
    slogan: str = ""
    logo: Optional[str] = None
    address: str = ""
    email: str = ""
    phone: str = ""
    social_links: Dict[str, str] = {}
    tax_id: str = ""


class CompanySettingsResponse(BaseModel):
    id: str = Field(alias="_id")
    company_name: str
    slogan: str = ""
    logo: Optional[str] = None
    address: str = ""
    email: str = ""
    phone: str = ""
    social_links: Dict[str, str] = {}
    tax_id: str = ""
    created_at: datetime
    updated_at: datetime

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True

    @classmethod
    def from_mongo(cls, doc: dict) -> "CompanySettingsResponse":
        if "_id" in doc and isinstance(doc["_id"], ObjectId):
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
