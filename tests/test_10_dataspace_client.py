import datetime
from xarray_sentinel import dataspace_client


def test_DataSpaceClient() -> None:
    filter_template = "{start_date_iso} {stop_date_iso} {relative_orbit} {geometry_wkt}"
    client = dataspace_client.DataSpaceClient(
        products_odata_filter_template=filter_template
    )
    date = datetime.datetime(2020, 2, 3)
    bbox = (0, 1, 2, 3)
    expected = "2020-02-03T00:00:00 2020-02-03T00:00:00 22 SRID=4326;POLYGON ((2 1, 2 3, 0 3, 0 1, 2 1))"

    res = client.build_sentinel1_products_odata_filter(date, date, 22, bbox)

    assert res == expected
