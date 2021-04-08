import os
import pathlib
import typing as T
from xml.etree import ElementTree
import datetime as dt

SENTINEL1_NAMESPACES = {
    "safe": "http://www.esa.int/safe/sentinel-1.0",
    "s1": "http://www.esa.int/safe/sentinel-1.0/sentinel-1",
    "s1sarl1": "http://www.esa.int/safe/sentinel-1.0/sentinel-1/sar/level-1",
}

SENTINEL2_NAMESPACES = {
    "safe": "http://www.esa.int/safe/sentinel/1.1",
}


GGP_CONVERT: T.Dict[str, T.Callable[[str], T.Any]] = {
    "azimuthTime": lambda x: x,
    "line": int,
    "pixel": int,
}


ATTITUDE_CONVERT: T.Dict[str, T.Callable[[str], T.Any]] = {
    "time": lambda t: dt.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%f"),
    "frame": str,
}


ORBIT_CONVERT: T.Dict[str, T.Callable[[str], T.Any]] = {
    "time": lambda t: dt.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%f"),
    "frame": str,
}


def parse_attitude(
    annotation: ElementTree.ElementTree,
) -> T.List[T.Any]:
    attitude = []
    for attitude_tag in annotation.findall(".//attitude"):
        att = {}
        for tag in attitude_tag:
            converter = ATTITUDE_CONVERT.get(tag.tag, float)
            att[tag.tag] = converter(str(tag.text))
        attitude.append(att)
    return attitude


def parse_orbit(
    annotation: ElementTree.ElementTree,
) -> T.List[T.Any]:
    orbit = []
    for orbit_tag in annotation.findall(".//orbit"):
        orb = {}
        for tag in orbit_tag:
            if str(tag.text).strip():
                converter = ORBIT_CONVERT.get(tag.tag, float)
                orb[tag.tag] = converter(str(tag.text))
            else:
                orb[tag.tag] = {}
                for sub_tag in tag:
                    converter = ORBIT_CONVERT.get(sub_tag.tag, float)
                    orb[tag.tag][sub_tag.tag] = converter(str(sub_tag.text))
        orbit.append(orb)
    return orbit


def parse_geolocation_grid_points(
    annotation: ElementTree.ElementTree,
) -> T.Dict[T.Tuple[int, int], T.Any]:
    geolocation_grid_points = {}
    for ggp_tag in annotation.findall(".//geolocationGridPoint"):
        ggp = {}
        for tag in ggp_tag:
            converter = GGP_CONVERT.get(tag.tag, float)
            ggp[tag.tag] = converter(str(tag.text))
        geolocation_grid_points[ggp["line"], ggp["pixel"]] = ggp
    return geolocation_grid_points


def open_manifest(
    product_folder: T.Union[str, "os.PathLike[str]"]
) -> ElementTree.ElementTree:
    product_folder = pathlib.Path(product_folder)
    if product_folder.is_dir():
        product_folder = product_folder / "manifest.safe"
    return ElementTree.parse(product_folder)


def parse_manifest_sentinel1(
    manifest: ElementTree.ElementTree,
) -> T.Tuple[T.Dict[str, T.Any], T.Dict[str, str]]:
    familyName = manifest.findtext(
        ".//safe:platform/safe:familyName", namespaces=SENTINEL1_NAMESPACES
    )
    if familyName != "SENTINEL-1":
        raise ValueError(f"{familyName} not supported")

    number = manifest.findtext(
        ".//safe:platform/safe:number", namespaces=SENTINEL1_NAMESPACES
    )
    if number is None:
        raise ValueError(f"{number} not supported")

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
        raise ValueError(f"{orbitProperties_pass}= not supported")

    ascendingNodeTime = manifest.findtext(
        ".//s1:orbitProperties/s1:ascendingNodeTime", namespaces=SENTINEL1_NAMESPACES
    )
    if ascendingNodeTime is None:
        raise ValueError(f"{ascendingNodeTime} not supported")

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


def parse_manifest_sentinel2(
    manifest: ElementTree.ElementTree,
) -> T.Tuple[T.Dict[str, T.Any], T.Dict[str, str]]:
    familyName = manifest.findtext(
        ".//safe:platform/safe:familyName", namespaces=SENTINEL2_NAMESPACES
    )
    if familyName != "SENTINEL":
        raise ValueError(f"{familyName} not supported")

    number = manifest.findtext(
        ".//safe:platform/safe:number", namespaces=SENTINEL2_NAMESPACES
    )
    if number is None:
        raise ValueError(f"{number} not supported")

    orbitNumber_tag = manifest.find(
        ".//safe:orbitReference/safe:orbitNumber", namespaces=SENTINEL2_NAMESPACES
    )
    if orbitNumber_tag is None:
        raise ValueError("orbitNumber not found")
    groundTrackDirection = orbitNumber_tag.attrib["groundTrackDirection"]
    if groundTrackDirection not in {"ascending", "descending"}:
        raise ValueError(f"{groundTrackDirection} not supported")

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
        raise ValueError(f"{mtd_product_tag} not suppoorted")

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

