import datetime
from typing import Any

import requests
import shapely
import structlog
import typer

DEFAULT_ODATA_URL: str = "https://catalogue.dataspace.copernicus.eu/odata/v1"
DEFAULT_PRODUCTS_ODATA_FILTER_TEMPLATE = (
    "((Collection/Name eq 'SENTINEL-1' "
    "and (Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'instrumentShortName' and att/OData.CSC.StringAttribute/Value eq 'SAR') "
    "and (contains(Name,'GRD') and contains(Name,'_COG') "
    "and OData.CSC.Intersects(area=geography'{geometry_wkt}'))) "
    "and (Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'operationalMode' and att/OData.CSC.StringAttribute/Value eq 'IW') "
    "and Attributes/OData.CSC.IntegerAttribute/any(att:att/Name eq 'relativeOrbitNumber' and att/OData.CSC.IntegerAttribute/Value eq {relative_orbit}))) "
    "and ContentDate/Start ge {start_date_iso}Z and ContentDate/Start lt {stop_date_iso}Z)"
)
LOGGER = structlog.getLogger(__name__)


class DataSpaceClient:

    def __init__(
        self,
        odata_url: str = DEFAULT_ODATA_URL,
        products_odata_filter_template: str = DEFAULT_PRODUCTS_ODATA_FILTER_TEMPLATE,
    ) -> None:
        self.odata_url = odata_url
        self.products_odata_filter_template = products_odata_filter_template

    def build_sentinel1_products_odata_filter(
        self,
        start_date: datetime.datetime,
        stop_date: datetime.datetime,
        relative_orbit: int,
        bbox: tuple[float, float, float, float] = (-180, -90, 180, 90),
    ) -> str:
        geometry = shapely.box(*bbox)
        geometry_wkt = f"SRID=4326;{geometry.wkt}"
        sentinel1_products_odata_filter = self.products_odata_filter_template.format(
            geometry_wkt=geometry_wkt,
            start_date_iso=start_date.isoformat(),
            stop_date_iso=stop_date.isoformat(),
            relative_orbit=relative_orbit,
        )
        return sentinel1_products_odata_filter

    def search_sentinel1_products(
        self,
        start_date: datetime.datetime,
        stop_date: datetime.datetime,
        relative_orbit: int,
        bbox: tuple[float, float, float, float] = (-180, -90, 180, 90),
        limit: int = 100,
        log: structlog.BoundLogger = LOGGER,
    ) -> dict[str, Any]:
        product_url = f"{self.odata_url}/Products"
        odata_filter = self.build_sentinel1_products_odata_filter(
            start_date, stop_date, relative_orbit, bbox
        )
        params = {
            "$filter": odata_filter,
            "$top": limit,
        }
        resp = requests.get(product_url, params=params)
        resp.raise_for_status()
        return resp.json()


def get_s3paths(results: list[Any]) -> list[str]:
    return sorted([result.get("S3Path") for result in results])


def search_sentinel1_products(
    start_date: str = "2024-01-01",
    stop_date: str = "2024-12-31",
    relative_orbit: int = 22,
    bbox: tuple[float, float, float, float] = (6.75, 36.62, 18.48, 47.11),
    limit: int = 100,
    odata_url: str = DEFAULT_ODATA_URL,
) -> None:
    dataspace_client = DataSpaceClient(odata_url)
    resutls = dataspace_client.search_sentinel1_products(
        start_date, stop_date, relative_orbit, bbox, limit
    )
    results = get_s3paths(resutls["value"])
    for res in results:
        print(res)


if __name__ == "__main__":
    typer.run(search_sentinel1_products)
