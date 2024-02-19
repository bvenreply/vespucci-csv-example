from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Mapping
import pandas as pd

from deviceconfig import Component


@dataclass
class ComponentData:
    name: str
    component: Component
    data: pd.DataFrame

    def __init__(self, name: str, component: Component, data: pd.DataFrame):
        self.name = name
        self.component = component
        self.data = data


    @staticmethod
    def collate(component_data: Iterable["ComponentData"]) -> pd.DataFrame:

        component_data = tuple(cd.data.drop("Time", axis=1) for cd in component_data)
        # print(component_data)
        conc: pd.DataFrame = pd.concat(component_data, axis=1, sort=False)
        print(conc)
        return conc.drop_duplicates()