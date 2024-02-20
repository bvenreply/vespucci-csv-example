from collections.abc import Mapping, MutableMapping, Sequence
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class DeviceConfigComponent(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str

    odr: int
    fs: Optional[float] = None
    enable: bool
    samples_per_ts: int
    dim: int
    ioffset: float
    measodr: float
    usb_dps: int
    sd_dps: int
    sensitivity: float
    data_type: str
    sensor_category: int
    c_type: int
    stream_id: int
    ep_id: int


def name_mapping(
    key: str, mapping_value: MutableMapping[str, Any]
) -> Mapping[str, Any]:
    mapping_value["name"] = key

    return mapping_value


def to_named_sequence(
    mapping: Mapping[str, MutableMapping[str, Any]]
) -> Sequence[Mapping[str, Any]]:
    return tuple(name_mapping(key, value) for key, value in mapping.items())


class DeviceConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    board_id: int
    fw_id: int

    component_data: Sequence[Any] = Field(alias="components")

    def get_components(
        self, filter_disabled: bool = True
    ) -> Sequence[DeviceConfigComponent]:

        return tuple(
            DeviceConfigComponent.model_validate(item)
            for mapping in self.component_data
            for item in to_named_sequence(mapping)
            if "odr" in item and ((not filter_disabled) or item["enable"])
        )
