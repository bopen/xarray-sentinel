import re
import warnings
from typing import Any
from xml.etree import ElementTree

import numpy as np

from . import esa_safe


# taken from pydantic.alias_generators, MIT license
def to_snake(camel: str) -> str:
    """Convert a PascalCase, camelCase, or kebab-case string to snake_case.

    Args:
        camel: The string to convert.

    Returns
    -------
        The converted string in snake_case.
    """
    # Handle the sequence of uppercase letters followed by a lowercase letter
    snake = re.sub(
        r"([A-Z]+)([A-Z][a-z])", lambda m: f"{m.group(1)}_{m.group(2)}", camel
    )
    # Insert an underscore between a lowercase letter and an uppercase letter
    snake = re.sub(r"([a-z])([A-Z])", lambda m: f"{m.group(1)}_{m.group(2)}", snake)
    # Insert an underscore between a digit and an uppercase letter
    snake = re.sub(r"([0-9])([A-Z])", lambda m: f"{m.group(1)}_{m.group(2)}", snake)
    # Insert an underscore between a lowercase letter and a digit
    snake = re.sub(r"([a-z])([0-9])", lambda m: f"{m.group(1)}_{m.group(2)}", snake)
    # Replace hyphens with underscores to handle kebab-case
    snake = snake.replace("-", "_")
    return snake.lower()


def to_snake_recursive(
    struct: dict[str, Any] | list[Any],
) -> dict[str, Any] | list[Any]:
    if isinstance(struct, dict):
        struct = {to_snake(k): to_snake_recursive(v) for k, v in struct.items()}
    elif isinstance(struct, list):
        struct = [to_snake_recursive(v) for v in struct]
    return struct


def fix_lists(struct: Any) -> Any:
    """Simplify the xmlschema decoding of a Sentinel-1 XML to plain values.

    xmlschema writes attributes as "@name" keys and the text of an element with
    attributes under "$". On top of that the Sentinel-1 schemas use two patterns:
    arrays (floatArray, ... in s1-object-types.xsd) are strings of space separated
    numbers with a count attribute, {"@count": 3, "$": "1 2 3"}, and lists like
    burst_list hold the burst elements and a count, {"@count": 2, "burst": [...]}.

    Drop the count attributes, replace an element with attributes by its value, an
    array by a list of floats and a list by its items.
    """
    fixed: Any
    if isinstance(struct, dict):
        fixed = {}
        for k, v in struct.items():
            if k == "@count":
                continue
            # an element with attributes or an array: the dict becomes its value
            elif k == "$":
                values = (
                    [float(value) for value in v.split()] if isinstance(v, str) else v
                )
                return values
            elif k[-5:] == "_list":
                fixed[k] = fix_lists(v.get(k[:-5], []))
            else:
                fixed[k] = fix_lists(v)
    elif isinstance(struct, list):
        fixed = [fix_lists(v) for v in struct]
    else:
        fixed = struct
    return fixed


def filter_metadata_dict(image_information: dict[str, Any]) -> dict[str, Any]:
    image_information = to_snake_recursive(image_information)  # type: ignore
    image_information = fix_lists(image_information)
    return image_information


def build_general_annotation(general_annotation: dict[str, Any]) -> dict[str, Any]:
    general_annotation = filter_metadata_dict(general_annotation)
    _ = general_annotation.pop("orbit_list")
    _ = general_annotation.pop("attitude_list")
    return general_annotation


def build_other_metadata(annotation: dict[str, Any]) -> dict[str, Any]:
    warnings.warn("This is an unofficial, alpha converter", UserWarning)
    quality_information = filter_metadata_dict(annotation["qualityInformation"])
    general_annotation = build_general_annotation(annotation["generalAnnotation"])
    image_information = filter_metadata_dict(annotation["imageAnnotation"])
    swath_merging = filter_metadata_dict(annotation["swathMerging"])
    swath_timing = filter_metadata_dict(annotation["swathTiming"])

    other_metadata = {
        "quality_information": quality_information,
        "general_annotation": general_annotation,
        "image_annotation": image_information,
        "swath_timing": swath_timing,
        "swath_merging": swath_merging,
    }
    return other_metadata


PRODUCT_TIMELINESS = {"Fast-24h": "PT24H", "NRT-3h": "PT3H"}
STAC_EXTENSIONS = [
    "https://cs-si.github.io/eopf-stac-extension/v1.2.0/schema.json",
    "https://stac-extensions.github.io/product/v1.0.0/schema.json",
    "https://stac-extensions.github.io/sat/v1.1.0/schema.json",
    "https://stac-extensions.github.io/view/v1.1.0/schema.json",
    "https://stac-extensions.github.io/processing/v1.2.0/schema.json",
    "https://stac-extensions.github.io/sar/v1.3.1/schema.json",
]


def build_stac_discovery(
    item_id: str,
    manifest_path: esa_safe.PathOrFileType,
    annotation: dict[str, Any],
    footprint: list[tuple[float, float]] | None = None,
    relative_burst: int | None = None,
    namespaces: dict[str, str] = esa_safe.SENTINEL1_NAMESPACES,
) -> dict[str, Any]:
    if hasattr(manifest_path, "seek"):
        manifest_path.seek(0)
    manifest = ElementTree.parse(manifest_path).getroot()

    product_information = esa_safe.get_tag(
        annotation, "generalAnnotation/productInformation"
    )
    image_information = esa_safe.get_tag(annotation, "imageAnnotation/imageInformation")

    if footprint is None:
        # the manifest footprint is in lat,lon order
        footprint = []
        for token in esa_safe.findtext(manifest, ".//gml:coordinates").split():
            lat, lon = (float(v) for v in token.split(","))
            footprint.append((lon, lat))
        footprint.append(footprint[0])
    lons, lats = zip(*footprint)

    start_time = np.datetime64(esa_safe.findtext(manifest, ".//safe:startTime"), "us")
    stop_time = np.datetime64(esa_safe.findtext(manifest, ".//safe:stopTime"), "us")
    middle_time = start_time + (stop_time - start_time) // 2
    processing = manifest.find(".//safe:processing", namespaces=namespaces)
    facility = manifest.find(".//safe:processing/safe:facility", namespaces=namespaces)
    software = manifest.find(".//safe:facility/safe:software", namespaces=namespaces)
    assert processing is not None and facility is not None and software is not None
    mode = esa_safe.findtext(manifest, ".//s1sarl1:instrumentMode/s1sarl1:mode")
    product_type = esa_safe.findtext(manifest, ".//s1sarl1:productType")
    timeliness_category = esa_safe.findtext(
        manifest, ".//s1sarl1:productTimelinessCategory"
    )

    properties = {
        "mission": "copernicus",
        "datetime": np.datetime_as_string(middle_time) + "Z",
        "start_datetime": np.datetime_as_string(start_time) + "Z",
        "end_datetime": np.datetime_as_string(stop_time) + "Z",
        "created": processing.attrib["stop"] + "Z",
        "platform": "sentinel-1"
        + esa_safe.findtext(manifest, ".//safe:platform/safe:number").lower(),
        "instruments": ["sar"],
        "providers": [
            {"name": facility.attrib["name"], "roles": ["processor"]},
            {"name": facility.attrib["organisation"], "roles": ["producer"]},
        ],
        "constellation": "sentinel-1",
        "product:type": f"S01S{mode}{product_type}",
        "product:timeliness_category": timeliness_category,
        "product:timeliness": PRODUCT_TIMELINESS[timeliness_category],
        "processing:datetime": processing.attrib["stop"] + "Z",
        "processing:facility": facility.attrib["name"],
        "processing:software": {software.attrib["name"]: software.attrib["version"]},
        "processing:version": software.attrib["version"],
        "processing:lineage": "systematic",
        "sat:platform_international_designator": esa_safe.findtext(
            manifest, ".//safe:nssdcIdentifier"
        ),
        "sat:absolute_orbit": int(esa_safe.findall(manifest, ".//safe:orbitNumber")[0]),
        "sat:relative_orbit": int(
            esa_safe.findall(manifest, ".//safe:relativeOrbitNumber")[0]
        ),
        "sat:orbit_state": esa_safe.findtext(manifest, ".//s1:pass").lower(),
        "sat:anx_datetime": esa_safe.findtext(manifest, ".//s1:ascendingNodeTime")
        + "Z",
        "view:incidence_angle": image_information["incidenceAngleMidSwath"],
        "sar:polarizations": esa_safe.findall(
            manifest, ".//s1sarl1:transmitterReceiverPolarisation"
        ),
        "sar:instrument_mode": mode,
        "sar:frequency_band": "C",
        "sar:center_frequency": product_information["radarFrequency"] / 1e9,
        "sar:pixel_spacing_range": image_information["rangePixelSpacing"],
        "sar:pixel_spacing_azimuth": image_information["azimuthPixelSpacing"],
        "sar:observation_direction": "right",
        "sar:beam_ids": esa_safe.findall(
            manifest, ".//s1sarl1:instrumentMode/s1sarl1:swath"
        ),
        "eopf:datatake_id": esa_safe.findtext(manifest, ".//s1sarl1:missionDataTakeID"),
    }
    if relative_burst is not None:
        properties["sar:relative_burst"] = relative_burst

    stac_item = {
        "type": "Feature",
        "stac_version": "1.1.0",
        "stac_extensions": STAC_EXTENSIONS,
        "id": item_id,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[list(point) for point in footprint]],
        },
        "bbox": [min(lons), min(lats), max(lons), max(lats)],
        "properties": properties,
        "links": [],
        "assets": {},
    }
    return stac_item
