from xarray_sentinel import eopf_metadata


def test_to_snake_recursive() -> None:
    metadata = {"qualityInformation": {"qualityDataList": [{"qualityData": 2}]}}
    expected = {"quality_information": {"quality_data_list": [{"quality_data": 2}]}}

    res = eopf_metadata.to_snake_recursive(metadata)

    assert res == expected
