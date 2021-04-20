import functools
import os
import pathlib
import typing as T
from xml.etree import ElementTree

import pkg_resources
import xmlschema

PathType = T.Union[str, "os.PathLike[str]"]


SENTINEL1_NAMESPACES = {
    "safe": "http://www.esa.int/safe/sentinel-1.0",
    "s1": "http://www.esa.int/safe/sentinel-1.0/sentinel-1",
    "s1sarl1": "http://www.esa.int/safe/sentinel-1.0/sentinel-1/sar/level-1",
}

SENTINEL2_NAMESPACES = {
    "safe": "http://www.esa.int/safe/sentinel/1.1",
}


def get_ancillary_data_paths(
    manifest_path: PathType, product_files: T.Dict[str, str],
) -> T.Dict[str, T.Dict[str, T.Dict[str, str]]]:
    folder = pathlib.Path(manifest_path).parent

    type_mapping = {
        "s1Level1CalibrationSchema": "calibration_path",
        "s1Level1MeasurementSchema": "measurement_path",
        "s1Level1NoiseSchema": "noise_path",
        "s1Level1ProductSchema": "annotation_path",
    }
    ancillary_data_paths: T.Dict[str, T.Dict[str, T.Dict[str, str]]] = {}
    for filename, filetype in product_files.items():
        if filetype not in type_mapping:
            continue
        file_path = folder / filename
        name = os.path.basename(filename)
        subswath, _, pol = os.path.basename(name).rsplit("-", 8)[1:4]
        swath_dict = ancillary_data_paths.setdefault(subswath, {})
        type_dict = swath_dict.setdefault(type_mapping[filetype], {})
        type_dict[pol] = str(file_path)
    return ancillary_data_paths


@functools.lru_cache()
def sentinel1_schemas(schema_type: str) -> xmlschema.XMLSchema:
    support_dir = pkg_resources.resource_filename(__name__, "resources/sentinel1")
    schema_paths = {
        "manifest": os.path.join(support_dir, "my-xfdu.xsd"),
        "product": os.path.join(support_dir, "s1-level-1-product.xsd"),
    }
    return xmlschema.XMLSchema(schema_paths[schema_type])


def parse_tag_dict(
    xml_path: PathType, schema_type: str, query: str,
) -> T.Dict[str, T.Any]:
    xml_path = os.fspath(xml_path)
    schema = sentinel1_schemas(schema_type)
    tag_list: T.Dict[str, T.Any] = schema.to_dict(xml_path, query)
    return tag_list


def parse_tag_list(
    xml_path: PathType, schema_type: str, query: str,
) -> T.List[T.Dict[str, T.Any]]:
    xml_path = os.fspath(xml_path)
    schema = sentinel1_schemas(schema_type)
    tag_list: T.List[T.Dict[str, T.Any]] = schema.to_dict(xml_path, query)
    return tag_list


def parse_attitude(annotation_path: PathType) -> T.List[T.Dict[str, T.Any]]:
    return parse_tag_list(annotation_path, "product", ".//attitude")


def parse_orbit(annotation_path: PathType) -> T.List[T.Dict[str, T.Any]]:
    return parse_tag_list(annotation_path, "product", ".//orbit")


def parse_geolocation_grid_points(
    annotation_path: PathType,
) -> T.List[T.Dict[str, T.Any]]:
    return parse_tag_list(annotation_path, "product", ".//geolocationGridPoint")


def parse_swath_timing(annotation_path: PathType) -> T.Dict[str, T.Any]:
    return parse_tag_dict(annotation_path, "product", ".//swathTiming")


@functools.lru_cache()
def parse_product_information(annotation_path: PathType) -> T.Dict[str, T.Any]:
    return parse_tag_dict(annotation_path, "product", ".//productInformation")


def parse_processing_information(
    annotation_path: PathType,
) -> T.List[T.Dict[str, T.Any]]:
    return parse_tag_list(annotation_path, "product", ".//processingInformation")


def parse_image_information(annotation_path: PathType) -> T.Dict[str, T.Any]:
    return parse_tag_dict(annotation_path, "product", ".//imageInformation")


def parse_azimuth_fm_rate(annotation_path: PathType) -> T.List[T.Dict[str, T.Any]]:
    azimuth_fm_rate = []
    for afmr in parse_tag_list(annotation_path, "product", ".//azimuthFmRate"):
        poly = [float(c) for c in afmr["azimuthFmRatePolynomial"]["$"].split()]
        afmr["azimuthFmRatePolynomial"] = poly
        azimuth_fm_rate.append(afmr)
    return azimuth_fm_rate


def parse_dc_estimate(annotation_path: PathType) -> T.List[T.Dict[str, T.Any]]:
    dc_estimate = []
    for de in parse_tag_list(annotation_path, "product", ".//dcEstimate"):
        poly = [float(c) for c in de["dataDcPolynomial"]["$"].split()]
        de["dataDcPolynomial"] = poly
        de.pop("fineDceList")  # drop large unused data
        dc_estimate.append(de)
    return dc_estimate


def open_manifest(
    product_path: PathType,
) -> T.Tuple[pathlib.Path, ElementTree.ElementTree]:
    product_path = pathlib.Path(product_path)
    if product_path.is_dir():
        product_path = product_path / "manifest.safe"
    return product_path, ElementTree.parse(product_path)


@functools.lru_cache()
def parse_manifest_sentinel1(
    manifest: ElementTree.ElementTree,
) -> T.Tuple[T.Dict[str, T.Any], T.Dict[str, str]]:
    familyName = manifest.findtext(
        ".//safe:platform/safe:familyName", namespaces=SENTINEL1_NAMESPACES
    )
    if familyName != "SENTINEL-1":
        raise ValueError(f"{familyName=} not supported")

    number = manifest.findtext(
        ".//safe:platform/safe:number", namespaces=SENTINEL1_NAMESPACES
    )
    if number is None:
        raise ValueError(f"{number=} not supported")

    instrumentMode = manifest.findtext(
        ".//s1sarl1:instrumentMode/s1sarl1:mode", namespaces=SENTINEL1_NAMESPACES
    )

    swaths = manifest.findall(
        ".//s1sarl1:instrumentMode/s1sarl1:swath", namespaces=SENTINEL1_NAMESPACES
    )

    transmitterReceiverPolarisation = manifest.findall(
        ".//s1sarl1:transmitterReceiverPolarisation", namespaces=SENTINEL1_NAMESPACES
    )

    productType = manifest.findtext(
        ".//s1sarl1:standAloneProductInformation/s1sarl1:productType",
        namespaces=SENTINEL1_NAMESPACES,
    )

    orbitProperties_pass = manifest.findtext(
        ".//s1:orbitProperties/s1:pass", namespaces=SENTINEL1_NAMESPACES
    )
    if orbitProperties_pass not in {"ASCENDING", "DESCENDING"}:
        raise ValueError(f"{orbitProperties_pass=} not supported")

    ascendingNodeTime = manifest.findtext(
        ".//s1:orbitProperties/s1:ascendingNodeTime", namespaces=SENTINEL1_NAMESPACES
    )
    if ascendingNodeTime is None:
        raise ValueError(f"{ascendingNodeTime=} not supported")

    orbitNumber = manifest.findall(
        ".//safe:orbitReference/safe:orbitNumber", namespaces=SENTINEL1_NAMESPACES
    )
    if (
        len(orbitNumber) != 2
        or orbitNumber[0].text != orbitNumber[1].text
        or orbitNumber[0].text is None
    ):
        raise ValueError(f"orbitNumber={[o.text for o in orbitNumber]} not supported")

    relativeOrbitNumber = manifest.findall(
        ".//safe:orbitReference/safe:relativeOrbitNumber",
        namespaces=SENTINEL1_NAMESPACES,
    )
    if (
        len(relativeOrbitNumber) != 2
        or relativeOrbitNumber[0].text != relativeOrbitNumber[1].text
        or relativeOrbitNumber[0].text is None
    ):
        raise ValueError(
            f"relativeOrbitNumber={[o.text for o in relativeOrbitNumber]} not supported"
        )

    attributes = {
        "constellation": "sentinel-1",
        "platform": "sentinel-1" + number.lower(),
        "instrument": ["c-sar"],
        "sat:orbit_state": orbitProperties_pass.lower(),
        "sat:absolute_orbit": int(orbitNumber[0].text),
        "sat:relative_orbit": int(relativeOrbitNumber[0].text),
        "sat:anx_datetime": ascendingNodeTime + "Z",
        "sar:frequency_band": "C",
        "sar:instrument_mode": instrumentMode,
        "sar:polarizations": [p.text for p in transmitterReceiverPolarisation],
        "sar:product_type": productType,
        "xs:instrument_mode_swaths": [s.text for s in swaths],
    }

    files = {}

    for file_tag in manifest.findall(".//dataObjectSection/dataObject"):
        location_tag = file_tag.find(".//fileLocation")
        if location_tag is not None:
            file_href = location_tag.attrib["href"]
            file_type = file_tag.attrib["repID"]
            files[file_href] = file_type

    return attributes, files


# unused until we add an interface to access original metadata
def parse_original_manifest_sentinel1(
    manifest_path: PathType,
) -> T.Tuple[T.Dict[str, T.Any], T.Dict[str, str]]:
    schema = sentinel1_schemas("manifest")

    xml_metadata = {}
    for xml_tags in schema.to_dict(manifest_path, ".//xmlData"):
        for key, value in xml_tags.items():
            xml_metadata[key] = value

    fileLocation = schema.to_dict(manifest_path, ".//fileLocation")

    return xml_metadata, fileLocation


def parse_manifest_sentinel2(
    manifest: ElementTree.ElementTree,
) -> T.Tuple[T.Dict[str, T.Any], T.Dict[str, str]]:
    familyName = manifest.findtext(
        ".//safe:platform/safe:familyName", namespaces=SENTINEL2_NAMESPACES
    )
    if familyName != "SENTINEL":
        raise ValueError(f"{familyName=} not supported")

    number = manifest.findtext(
        ".//safe:platform/safe:number", namespaces=SENTINEL2_NAMESPACES
    )
    if number is None:
        raise ValueError(f"{number=} not supported")

    orbitNumber_tag = manifest.find(
        ".//safe:orbitReference/safe:orbitNumber", namespaces=SENTINEL2_NAMESPACES
    )
    if orbitNumber_tag is None:
        raise ValueError("orbitNumber not found")
    groundTrackDirection = orbitNumber_tag.attrib["groundTrackDirection"]
    if groundTrackDirection not in {"ascending", "descending"}:
        raise ValueError(f"{groundTrackDirection=} not supported")

    orbitNumber = manifest.findtext(
        ".//safe:orbitReference/safe:orbitNumber",
        default="-1",
        namespaces=SENTINEL2_NAMESPACES,
    )

    relativeOrbitNumber = manifest.findtext(
        ".//safe:orbitReference/safe:relativeOrbitNumber",
        default="-1",
        namespaces=SENTINEL2_NAMESPACES,
    )

    mtd_product_tag = manifest.find(
        ".//dataObject[@ID='S2_Level-1C_Product_Metadata']/byteStream/fileLocation",
        namespaces=SENTINEL2_NAMESPACES,
    )
    if (
        mtd_product_tag is not None
        and "MTD_MSIL1C.xml" in mtd_product_tag.attrib["href"]
    ):
        product_type = "S2MSIl1C"
    else:
        raise ValueError(f"{mtd_product_tag=} not suppoorted")

    attributes = {
        "constellation": "sentinel-2",
        "platform": "sentinel-" + number.lower(),
        "instrument": ["msi"],
        "sat:orbit_state": groundTrackDirection.lower(),
        "sat:absolute_orbit": int(orbitNumber),
        "sat:relative_orbit": int(relativeOrbitNumber),
        "xs:product_type": product_type,
    }

    files = {}

    for file_tag in manifest.findall(".//dataObjectSection/dataObject"):
        location_tag = file_tag.find(".//fileLocation")
        if location_tag is not None:
            file_href = location_tag.attrib["href"]
            file_type = file_tag.attrib["ID"]
            files[file_href] = file_type

    return attributes, files
