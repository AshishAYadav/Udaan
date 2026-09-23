from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str = Field(examples=["Flight cannot be changed because departure is within 24 hours."])


class AirportBrief(BaseModel):
    code: str = Field(examples=["DXB"])
    name: str = Field(examples=["Dubai International Airport"])
    city: str = Field(examples=["Dubai"])
