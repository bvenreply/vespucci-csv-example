from collections.abc import Mapping, MutableMapping, MutableSequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence, cast, no_type_check
import click
import tempfile as tmp
import logging
import subprocess as sp
from pathlib import Path
from os import listdir
from base64 import b32encode
import shutil
import sys
from hashlib import sha256
import ulid

from st_hsdatalog.HSD.HSDatalog import (
    HSDatalog as HSDatalogFactory,
    HSDatalog_v2,
)

from vic.acquisitioninfo import AcquisitionInfo, TagEvent
from vic.deviceconfig import DeviceConfig
from vic.models import (
    Device,
    Source,
    SensorConfigEntry,
    Component,
    DataItem,
    VespucciInertialCsvDataset,
)

PACKAGE_NAME = "vic"

DIGEST_READ_BUFFER_LENGTH = 512 * 2**4
FILENAME_DIGEST_TRUNCATION_LENGTH = 8

log: logging.Logger = cast(logging.Logger, None)


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


@click.command()
@click.argument("input-dir")
@click.option("--output-dir")
@click.option("--log-level", default="INFO")
def run(input_dir: str, output_dir: str, log_level: str) -> None:

    logging.basicConfig(level=log_level.upper())
    global log
    log = logging.getLogger(PACKAGE_NAME)

    input_path = Path(input_dir).absolute()

    if not input_path.exists():
        raise Exception(f"Input dir does not exist: {input_path}")

    if not input_path.is_dir():
        raise Exception(
            f"Input dir exists but is not a directory: {input_path}"
        )

    output_path = Path(output_dir).absolute()

    if not output_path.exists():
        if not output_path.parent.exists():
            raise Exception(
                "Output dir does not exist and neither does the parent"
            )

        log.debug(
            "Output folder %s does not exist, it will created", output_path
        )
    else:
        if not output_path.is_dir():
            raise Exception(
                f"Output dir exists but is not a directory: {input_path}"
            )

        log.debug("Output folder %s exists, no need to create it")

    with tmp.TemporaryDirectory() as temp_dir:
        temp_path_in = Path(temp_dir).absolute()

        log.debug("Created temp input dir: %s", temp_path_in)

        assert temp_path_in.exists() and temp_path_in.is_dir()

        with tmp.TemporaryDirectory() as temp_dir_out:
            temp_path_out = Path(temp_dir_out).absolute()

            log.debug("Created temp output dir: %s", temp_path_out)

            assert temp_path_out.exists() and temp_path_out.is_dir()

            do_conversion(input_path, output_path, temp_path_in, temp_path_out)

    log.debug("All done")

@no_type_check
def get_sensor_config_unit(component: Component, config_entry: str) -> str:
    if component.name.endswith("_acc"):
        return "g"
    elif component.name.endswith("_gyro"):
        return "mdps"
    else:
        raise Exception("Cannot get sensor config unit")


def do_conversion(
    input_path: Path, output_path: Path, temp_path_in: Path, temp_path_out: Path
) -> None:

    log.debug("Copying input folder to temp path")

    _ = shutil.copytree(input_path, temp_path_in, dirs_exist_ok=True)

    log.info("Starting conversion program...")

    _process = sp.run(
        (
            "python",
            str(Path(__file__).parent.joinpath("hsdatalog_to_unico.py")),
            "-s",
            "all",
            "-t",
            "-f",
            "CSV",
            "-o",
            str(temp_path_out),
            str(temp_path_in),
        ),
        stdout=sys.stdout,
        stderr=sys.stderr,
        check=True,
    )

    log.info("Conversion from `.dat` succeeded")

    log.debug("Assembling dataset metadata")

    hsd: HSDatalog_v2 = HSDatalogFactory().create_hsd(
        acquisition_folder=str(temp_path_in)
    )

    acq_info = hsd.get_acquisition_info()

    acq_info_validated = AcquisitionInfo.model_validate(acq_info)

    source = Source.model_validate({"blob_id": "none", "metadata": acq_info})

    log.debug("Datalog source info: %s", source)

    device_config_valid = DeviceConfig.model_validate(hsd.get_device())

    components_valid: MutableSequence[Component] = []

    device_config_components = device_config_valid.get_components()

    device: MutableMapping[str, Any] = {
        "components": components_valid,
        "board_id": device_config_valid.board_id,
        "fw_id": device_config_valid.fw_id,
        "metadata": {}
    }

    for device_config_component in device_config_components:

        odr_config = SensorConfigEntry.model_validate(
            {"value": device_config_component.odr, "unit": "Hz"}
        )

        fs_config = SensorConfigEntry.model_validate(
            {"value": device_config_component.fs, "unit": get_sensor_config_unit(device_config_component, "fs")}
        )

        component_valid = Component(
            name=device_config_component.name,
            config={"odr": odr_config, "fs": fs_config}
        )

        log.debug("Adding config for sensor %s:\n%s", component_valid.name, component_valid)

        components_valid.append(component_valid)

    device_valid = Device.model_validate(device)

    log.debug("Component metadata:\n%s", device_config_valid)

    tags = set(item["Label"] for item in hsd.get_time_tags())

    subfolders = tuple(
        temp_path_out.joinpath(item) for item in listdir(temp_path_out)
    )

    assert all(item.exists() and item.is_dir() for item in subfolders)
    assert set(item.name for item in subfolders) == tags

    log.debug("Detected tag set: %s", tags)

    data_items = []

    tag_ranges = TagRange.from_tag_events(acq_info_validated.tag_events)

    log.debug("Computed tag ranges: %s", tag_ranges)

    for subfolder in subfolders:

        one_tag_ranges = tuple(
            tag_range
            for tag_range in tag_ranges
            if tag_range.label == subfolder.name
        )

        log.debug("Processing subfolder %s", subfolder)

        files = tuple(subfolder.joinpath(item) for item in listdir(subfolder))

        assert all(file.name.endswith(".csv") for file in files)
        assert len(files) == len(one_tag_ranges)

        for tag_range, file in zip(one_tag_ranges, files):

            digest = sha256()

            with open(file, "rb") as file_handle:
                while (
                    read_bytes := file_handle.read(DIGEST_READ_BUFFER_LENGTH)
                ) != b"":
                    digest.update(read_bytes)

            file_id = b32encode(digest.digest()).decode("utf-8").lower()

            # Length of a 32 byte string encoded in base32 (4 bytes of padding).
            assert len(file_id) == 56
            assert file_id.endswith("====")

            ext = "csv"

            file_name = f"{file_id[:8]}.{ext}"

            file.rename(file.with_name(file_name))

            file_item = {
                "id": file_id,
                "relative_path": f"{subfolder.name}/{file_name}",
                "type": "text/csv",
                "extension": ext,
            }

            data_item = {
                "class": tag_range.label,
                "start_time": tag_range.start_time,
                "end_time": tag_range.end_time,
                "file": file_item,
                "source": source,
                "device": device_valid
            }

            data_item_valid = DataItem.model_validate(data_item)
            data_items.append(data_item_valid)

    dataset = VespucciInertialCsvDataset(
        name="my converted dataset",
        description="My dataset description",
        id=str(ulid.ULID()).lower(),
        classes=list(tags),
        data=data_items,
        metadata={},
    )

    _ = shutil.copytree(temp_path_out, output_path, dirs_exist_ok=True)

    with open(output_path.joinpath("dataset-meta.json"), "wt") as file_handle:
        file_handle.write(dataset.model_dump_json(indent=2))

if __name__ == "__main__":
    run()
