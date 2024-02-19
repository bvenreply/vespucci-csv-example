

from collections.abc import Mapping, Sequence
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class Source(BaseModel):
    blob_id: Optional[str]
    metadata: Mapping[str, Any]

class SensorConfigEntry(BaseModel):
    value: float
    unit: Optional[str]

class Sensor(BaseModel):
    type: str
    name: Optional[str]
    config: Mapping[str, SensorConfigEntry]

class Component(BaseModel):
    name: Optional[str]
    sensors: Sequence[Sensor]

class DataFile(BaseModel):
    id: str
    type: str
    extension: str
    relative_path: str

class DataItem(BaseModel):
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    class_label: Optional[str] = Field(alias="class")
    file: DataFile

    source: Optional[Source]

class VespucciInertialCsvDataset(BaseModel):
    name: str
    description: Optional[str]
    id: str
    classes: Sequence[str]
    metadata: Mapping[str, Any]

    data: Sequence[DataItem]
