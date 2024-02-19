from collections.abc import Set
from typing import Sequence
from pydantic import BaseModel, ConfigDict, Field
import datetime

class TagEvent(BaseModel):
    label: str = Field(alias="l")
    is_set: bool = Field(alias="e")
    timestamp: datetime.datetime = Field(alias="ta")

class AcquisitionInfo(BaseModel):

    model_config = ConfigDict(extra="allow")

    name: str
    description: str = ""
    uuid: str

    start_time: datetime.datetime
    end_time: datetime.datetime

    tag_events: Sequence[TagEvent] = Field(alias="tags")

    def tag_set(self) -> Set[str]:
        return set(
            event.label for event in self.tag_events if event.is_set
        )
