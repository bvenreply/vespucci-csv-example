from collections.abc import MutableMapping, Set
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from pydantic import BaseModel, ConfigDict, Field


class TagEvent(BaseModel):
    label: str = Field(alias="l")
    is_set: bool = Field(alias="e")
    timestamp: datetime = Field(alias="ta")


class AcquisitionInfo(BaseModel):

    model_config = ConfigDict(extra="allow")

    name: str
    description: str = ""
    uuid: str

    start_time: datetime
    end_time: datetime

    tag_events: Sequence[TagEvent] = Field(alias="tags")

    def tag_set(self) -> Set[str]:
        return set(event.label for event in self.tag_events if event.is_set)


@dataclass
class TagRange:
    label: str
    start_time: datetime
    end_time: datetime

    @staticmethod
    def from_tag_events(events: Sequence[TagEvent]) -> Sequence["TagRange"]:

        if len(events) % 2 != 0:
            raise Exception(
                "Malformed events sequence."
                " The number of events should be an even number"
            )

        ret: list[TagRange] = []
        state: MutableMapping[str, TagEvent] = {}

        for event in events:
            if event.is_set:
                if event.label in state:
                    raise Exception(
                        f"Malformed event sequence, label {event.label} "
                        "was set again without being unset first"
                    )
                state[event.label] = event
            else:
                if event.label not in state:
                    raise Exception(
                        f"Malformed event sequence, label {event.label} "
                        "was unset without being set first"
                    )
                set_event = state.pop(event.label)

                assert set_event.label == event.label
                start_time = set_event.timestamp
                end_time = event.timestamp

                assert start_time <= end_time
                ret.append(
                    TagRange(
                        label=event.label,
                        start_time=start_time,
                        end_time=end_time,
                    )
                )

        if len(state) != 0:
            raise Exception(
                f"Malformed event sequence, label {event.label} "
                "was set and never unset"
            )

        return ret
