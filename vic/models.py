from collections.abc import Mapping, Sequence
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from vic.deviceconfig import DeviceConfigComponent

log = logging.getLogger(__name__)


class Source(BaseModel):
    blob_id: Optional[str]
    metadata: Mapping[str, Any]


class SensorConfigEntry(BaseModel):
    value: float
    unit: Optional[str]


class Component(BaseModel):
    name: Optional[str]
    config: Mapping[str, SensorConfigEntry]

    @staticmethod
    def from_device_config_component(
        device_config_component: DeviceConfigComponent,
    ) -> "Component":
        odr_config = SensorConfigEntry.model_validate(
            {"value": device_config_component.odr, "unit": "Hz"}
        )

        fs_config = SensorConfigEntry.model_validate(
            {
                "value": device_config_component.fs,
                "unit": device_config_component.get_sensor_config_unit("fs"),
            }
        )

        component_valid = Component(
            name=device_config_component.name,
            config={"odr": odr_config, "fs": fs_config},
        )

        return component_valid


class Device(BaseModel):
    components: Sequence[Component]
    metadata: Mapping[str, Any]


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

    device: Device
    source: Optional[Source]


class VespucciInertialCsvDataset(BaseModel):
    name: str
    description: Optional[str]
    id: str
    classes: Sequence[str]
    metadata: Mapping[str, Any]

    data: Sequence[DataItem]
