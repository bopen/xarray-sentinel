import re
import warnings
from typing import Any

import fsspec
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
    fixed: Any
    if isinstance(struct, dict):
        fixed = {}
        for k, v in struct.items():
            if k == "@count":
                continue
            if k[-5:] == "_list":
                try:
                    fixed[k] = fix_lists(struct[k][k[:-5]])
                except Exception:
                    fixed[k] = fix_lists(fix_lists(struct[k]))
            else:
                fixed[k] = fix_lists(struct[k])
    elif isinstance(struct, list):
        fixed = [fix_lists(v) for v in struct]
    else:
        fixed = struct
    return fixed


def filter_metadata_dict(image_information: dict[str, Any]) -> dict[str, Any]:
    image_information = to_snake_recursive(image_information)  # type: ignore
    image_information = fix_lists(image_information)
    return image_information


def build_azimuth_fm_rate_list(
    azimuth_fm_rate_list: list[dict[str, Any] | list[Any]],
) -> list[dict[str, Any] | list[Any]]:
    azimuth_fm_rate_list_out: list[dict[str, Any] | list[Any]] = []
    for item in azimuth_fm_rate_list:
        azimuth_fm_rate_polynomial_str = item["azimuth_fm_rate_polynomial"]["$"]  # type: ignore
        azimuth_fm_rate_list_out.append(
            {
                "azimuth_time": item["azimuth_time"],  # type: ignore
                "azimuth_fm_rate_polynomial": np.fromstring(
                    azimuth_fm_rate_polynomial_str, sep=" "
                ).tolist(),
            }
        )
    return azimuth_fm_rate_list_out


def build_general_annotation(general_annotation: dict[str, Any]) -> dict[str, Any]:
    general_annotation = filter_metadata_dict(general_annotation)
    _ = general_annotation.pop("orbit_list")
    _ = general_annotation.pop("attitude_list")
    general_annotation["azimuth_fm_rate_list"] = build_azimuth_fm_rate_list(
        general_annotation["azimuth_fm_rate_list"]
    )
    return general_annotation


def build_other_metadata(annotation_urlpath: esa_safe.PathType) -> dict[str, Any]:
    warnings.warn("This is an unofficial, alpha converter", UserWarning)
    with fsspec.open(annotation_urlpath) as fp:
        quality_information = esa_safe.parse_tag(fp, "//qualityInformation")
        quality_information = filter_metadata_dict(quality_information)
        general_annotation = esa_safe.parse_tag(fp, "//generalAnnotation")
        general_annotation = build_general_annotation(general_annotation)
        image_information = esa_safe.parse_tag(fp, "//imageAnnotation")
        image_information = filter_metadata_dict(image_information)
        swath_merginig = esa_safe.parse_tag(fp, "//swathMerging")
        swath_merginig = filter_metadata_dict(swath_merginig)
        swath_timing = esa_safe.parse_tag(fp, "//swathTiming")
        swath_timing = filter_metadata_dict(swath_timing)

    other_metadata = {
        "quality_information": quality_information,
        "general_annotation": general_annotation,
        "image_annotation": image_information,
        "swath_timing": swath_timing,
        "swath_merginig": swath_merginig,
    }
    return other_metadata
