import os
from typing import Literal, Protocol, Type

import pandas as pd

DataProcesorTypes = Literal["mocked"] | Literal["gcp"]


class DataProcesor(Protocol):
    def data_to_pandas(self, data: str) -> pd.DataFrame | None:
        ...


class GcpDataProcesor(DataProcesor):
    def data_to_pandas(self, data: str) -> pd.DataFrame | None:
        return None


class MockedDataProcesor(DataProcesor):
    def data_to_pandas(self, data: str) -> pd.DataFrame | None:
        if not os.path.exists(data):
            return None

        columns = {
            "region": "region",
            "origin_coord": "origin",
            "destination_coord": "destination",
            "datetime": "timestamp",
            "datasource": "source",
        }

        df = pd.read_csv(data).rename(columns=columns)  # type: ignore

        # Transform point columns to change from 'POINT (. .)' to '(. .)'
        df["origin"] = df["origin"].str.replace(  # type: ignore
            r"POINT \((\d+\.\d+) (\d+\.\d+)\)", r"\1 \2", regex=True
        )
        df["destination"] = df["destination"].str.replace(  # type: ignore
            r"POINT \((\d+\.\d+) (\d+\.\d+)\)", r"\1 \2", regex=True
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S")  # type: ignore

        df[["origin_x", "origin_y"]] = (
            df["origin"].str.split(" ", n=1, expand=True).astype(float)  # type: ignore
        )
        df[["destination_x", "destination_y"]] = (
            df["destination"].str.split(" ", n=1, expand=True).astype(float)  # type: ignore
        )
        df = df.drop(columns=["origin", "destination"])  # type: ignore

        return df


class DataProcesorFactory:
    buckets: dict[DataProcesorTypes, Type[DataProcesor]] = {
        "mocked": MockedDataProcesor,
        "gcp": GcpDataProcesor,
    }

    @classmethod
    def create(cls, bucket: DataProcesorTypes) -> DataProcesor:
        return cls.buckets[bucket]()
