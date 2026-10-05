from __future__ import annotations

import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import shapefile


@dataclass(frozen=True)
class PointShapeRecord:
    attributes: dict[str, str]
    longitude: float
    latitude: float


def read_point_shapefile_zip(
    path: Path,
    *,
    encoding: str = "cp932",
) -> list[PointShapeRecord]:
    """Read exactly one Point Shapefile from a ZIP archive.

    This function owns archive/Shapefile I/O only. Source-specific field
    interpretation remains the caller's responsibility.
    """
    if not path.exists():
        raise RuntimeError(f"missing Shapefile ZIP: {path}")

    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        with zipfile.ZipFile(path) as archive:
            archive.extractall(temp_dir)

        shp_files = list(temp_dir.rglob("*.shp"))
        if len(shp_files) != 1:
            raise RuntimeError(
                f"{path}: expected exactly one .shp file, got {len(shp_files)}"
            )

        reader = shapefile.Reader(str(shp_files[0]), encoding=encoding)
        try:
            if reader.shapeType != shapefile.POINT:
                raise RuntimeError(
                    f"{path}: expected POINT Shapefile, got {reader.shapeTypeName}"
                )

            fields = [field[0] for field in reader.fields[1:]]
            records: list[PointShapeRecord] = []

            for index, shape_record in enumerate(reader.iterShapeRecords(), start=1):
                points = shape_record.shape.points
                if len(points) != 1:
                    raise RuntimeError(
                        f"{path}: record {index}: expected one point, got {len(points)}"
                    )

                longitude, latitude = points[0]
                if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                    raise RuntimeError(
                        f"{path}: record {index}: coordinate out of range: "
                        f"{longitude!r}, {latitude!r}"
                    )

                attributes = {
                    field: "" if value is None else str(value).strip()
                    for field, value in zip(fields, shape_record.record)
                }
                records.append(
                    PointShapeRecord(
                        attributes=attributes,
                        longitude=longitude,
                        latitude=latitude,
                    )
                )

            return records
        finally:
            reader.close()
