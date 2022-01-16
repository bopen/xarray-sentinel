import functools
import os
import typing as T
from xml.etree import ElementTree

import pkg_resources
import xmlschema

PathType = T.Union[str, "os.PathLike[str]"]
PathOrFileType = T.Union[PathType, T.TextIO]


SENTINEL1_NAMESPACES = {
    "safe": "http://www.esa.int/safe/sentinel-1.0",
    "s1": "http://www.esa.int/safe/sentinel-1.0/sentinel-1",
    "s1sarl1": "http://www.esa.int/safe/sentinel-1.0/sentinel-1/sar/level-1",
}

SENTINEL1_FOLDER = pkg_resources.resource_filename(__name__, "resources/sentinel1")
SENTINEL1_SCHEMAS = {
    "manifest": os.path.join(SENTINEL1_FOLDER, "my-xfdu.xsd"),
    "annotation": os.path.join(SENTINEL1_FOLDER, "s1-level-1-product.xsd"),
    "calibration": os.path.join(SENTINEL1_FOLDER, "s1-level-1-calibration.xsd"),
}

SENTINEL2_NAMESPACES = {
    "safe": "http://www.esa.int/safe/sentinel/1.1",
}


def get_ancillary_data_paths(
    base_path: PathType,
    product_files: T.Dict[str, str],
) -> T.Dict[str, T.Dict[str, T.Dict[str, str]]]:
    ancillary_data_paths: T.Dict[str, T.Dict[str, T.Dict[str, str]]] = {}
    for filename, filetype in product_files.items():
        # HACK: no easy way to normalise the path component of a urlpath
        file_path = os.path.join(base_path, os.path.normpath(filename))
        name = os.path.basename(filename)
        try:
            subswath, _, pol = os.path.basename(name).rsplit("-", 8)[1:4]
        except ValueError:
            continue
        swath_dict = ancillary_data_paths.setdefault(subswath.upper(), {})
        pol_dict = swath_dict.setdefault(pol.upper(), {})
        pol_dict[filetype] = file_path
    return ancillary_data_paths


@functools.lru_cache
def cached_sentinel1_schemas(schema_type: str) -> xmlschema.XMLSchema:
    return xmlschema.XMLSchema(SENTINEL1_SCHEMAS[schema_type])


def parse_tag(
    xml_path: PathOrFileType,
    query: str,
    schema_type: str = "annotation",
    validation: str = "skip",
) -> T.Dict[str, T.Any]:
    schema = cached_sentinel1_schemas(schema_type)
    xml_tree = ElementTree.parse(xml_path)
    tag_dict: T.Dict[str, T.Any] = schema.to_dict(xml_tree, query, validation=validation)  # type: ignore
    assert isinstance(tag_dict, dict)
    return tag_dict


def parse_tag_list(
    xml_path: PathOrFileType,
    query: str,
    schema_type: str = "annotation",
    validation: str = "skip",
) -> T.List[T.Dict[str, T.Any]]:
    schema = cached_sentinel1_schemas(schema_type)
    xml_tree = ElementTree.parse(xml_path)
    tag_list: T.List[T.Dict[str, T.Any]] = schema.to_dict(xml_tree, query, validation=validation)  # type: ignore
    assert isinstance(tag_list, list)
    return tag_list


def parse_azimuth_fm_rate(
    annotation_path: PathOrFileType,
) -> T.List[T.Dict[str, T.Any]]:
    azimuth_fm_rate = []
    for afmr in parse_tag_list(annotation_path, ".//azimuthFmRate"):
        poly = [float(c) for c in afmr["azimuthFmRatePolynomial"]["$"].split()]
        afmr["azimuthFmRatePolynomial"] = poly
        azimuth_fm_rate.append(afmr)
    return azimuth_fm_rate


def parse_dc_estimate(annotation_path: PathOrFileType) -> T.List[T.Dict[str, T.Any]]:
    dc_estimate = []
    for de in parse_tag_list(annotation_path, ".//dcEstimate"):
        poly = [float(c) for c in de["dataDcPolynomial"]["$"].split()]
        de["dataDcPolynomial"] = poly
        de.pop("fineDceList")  # drop large unused data
        dc_estimate.append(de)
    return dc_estimate


def findtext(
    tree: ElementTree.ElementTree,
    query: str,
    namespaces: T.Dict[str, str] = SENTINEL1_NAMESPACES,
) -> str:
    value = tree.findtext(query, namespaces=namespaces)
    if value is None:
        raise ValueError(f"query={query} returned None")
    return value


def findall(
    tree: ElementTree.ElementTree,
    query: str,
    namespaces: T.Dict[str, str] = SENTINEL1_NAMESPACES,
) -> T.List[str]:
    tags = tree.findall(query, namespaces=namespaces)
    values: T.List[str] = []
    for tag in tags:
        if tag.text is None:
            raise ValueError(f"query={query} returned None")
        values.append(tag.text)
    return values


@functools.lru_cache
def parse_manifest_sentinel1(
    manifest_path: PathOrFileType,
) -> T.Tuple[T.Dict[str, T.Any], T.Dict[str, str]]:
    # We use ElementTree because we didn't find a XSD definition for the manifest
    manifest = ElementTree.parse(manifest_path)

    familyName = findtext(manifest, ".//safe:platform/safe:familyName")
    if familyName != "SENTINEL-1":
        raise ValueError(f"familyName={familyName} not supported")

    number = findtext(manifest, ".//safe:platform/safe:number")
    instrumentMode = findtext(manifest, ".//s1sarl1:instrumentMode/s1sarl1:mode")
    swaths = findall(manifest, ".//s1sarl1:instrumentMode/s1sarl1:swath")
    polarizations = findall(manifest, ".//s1sarl1:transmitterReceiverPolarisation")
    productType = findtext(manifest, ".//s1sarl1:productType")
    ascendingNodeTime = findtext(manifest, ".//s1:ascendingNodeTime")

    orbitProperties_pass = findtext(manifest, ".//s1:pass")
    if orbitProperties_pass not in {"ASCENDING", "DESCENDING"}:
        raise ValueError(f"pass={orbitProperties_pass} not supported")

    orbitNumber = findall(manifest, ".//safe:orbitNumber")
    if len(orbitNumber) != 2 or orbitNumber[0] != orbitNumber[1]:
        raise ValueError(f"orbitNumber={orbitNumber} not supported")

    relative_orbit = findall(manifest, ".//safe:relativeOrbitNumber")
    if len(relative_orbit) != 2 or relative_orbit[0] != relative_orbit[1]:
        raise ValueError(f"relativeOrbitNumber={relative_orbit} not supported")

    attributes = {
        "constellation": "sentinel-1",
        "platform": "sentinel-1" + number.lower(),
        "instrument": ["c-sar"],
        "sat:orbit_state": orbitProperties_pass.lower(),
        "sat:absolute_orbit": int(orbitNumber[0]),
        "sat:relative_orbit": int(relative_orbit[0]),
        "sat:anx_datetime": ascendingNodeTime + "Z",
        "sar:frequency_band": "C",
        "sar:instrument_mode": instrumentMode,
        "sar:polarizations": polarizations,
        "sar:product_type": productType,
        "xs:instrument_mode_swaths": swaths,
    }

    files = {}

    for file_tag in manifest.findall(".//dataObjectSection/dataObject"):
        location_tag = file_tag.find(".//fileLocation")
        if location_tag is not None:
            file_href = location_tag.attrib["href"]
            file_type = file_tag.attrib["repID"]
            files[file_href] = file_type

    return attributes, files
