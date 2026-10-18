import pathlib

import pytest
from stac_validator import stac_validator

from xarray_sentinel import eopf_metadata, esa_safe

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
)
SLC_IW1_VV_annotation = (
    SLC_IW
    / "annotation"
    / "s1b-iw1-slc-vv-20210401t052624-20210401t052649-026269-032297-004.xml"
)
SLC_S3 = (
    DATA_FOLDER
    / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
)
SLC_S3_VH_annotation = (
    SLC_S3
    / "annotation"
    / "s1a-s3-slc-vh-20210401t152855-20210401t152914-037258-04638e-001.xml"
)
GRD_IW = (
    DATA_FOLDER
    / "S1B_IW_GRDH_1SDV_20210401T052623_20210401T052648_026269_032297_ECC8.SAFE"
)
GRD_IW_VV_annotation = (
    GRD_IW
    / "annotation"
    / "s1b-iw-grd-vv-20210401t052623-20210401t052648-026269-032297-001.xml"
)


def test_to_snake_recursive() -> None:
    metadata = {
        "qualityInformation": {"qualityDataList": [{"qualityData": 2}]},
        "t0": 1,
    }
    expected = {
        "quality_information": {"quality_data_list": [{"quality_data": 2}]},
        "t0": 1,
    }

    res = eopf_metadata.to_snake_recursive(metadata)

    assert res == expected


def test_build_other_metadata() -> None:
    res = eopf_metadata.build_other_metadata(
        esa_safe.parse_xml(SLC_S3_VH_annotation), "S01SSMSLC"
    )
    expected_quality_information = {
        "product_quality_index": 0.0,
        "quality_data_list": [
            {
                "azimuth_time": "2021-04-01T15:28:55.111501",
                "downlink_quality": {
                    "i_input_data_mean": 0.06302300840616226,
                    "q_input_data_mean": 0.114902101457119,
                    "input_data_mean_outside_nominal_range_flag": False,
                    "i_input_data_std_dev": 1.674363970756531,
                    "q_input_data_std_dev": 1.515843987464905,
                    "input_data_st_dev_outside_nominal_range_flag": False,
                    "num_downlink_input_data_gaps": 0,
                    "downlink_gaps_in_input_data_significant_flag": False,
                    "num_downlink_input_missing_lines": 0,
                    "downlink_missing_lines_significant_flag": False,
                    "num_instrument_input_data_gaps": 0,
                    "instrument_gaps_in_input_data_significant_flag": False,
                    "num_instrument_input_missing_lines": 0,
                    "instrument_missing_lines_significant_flag": False,
                    "num_ssb_error_input_data_gaps": 0,
                    "ssb_error_gaps_in_input_data_significant_flag": False,
                    "num_ssb_error_input_missing_lines": 0,
                    "ssb_error_missing_lines_significant_flag": False,
                    "chirp_source_used": "Nominal",
                    "pg_source_used": "Extracted",
                    "rrf_spectrum_used": "Extended Tapered",
                    "replica_reconstruction_failed_flag": False,
                    "mean_pg_product_amplitude": 0.8810305595397949,
                    "std_dev_pg_product_amplitude": 0.006521929986774921,
                    "mean_pg_product_phase": 0.07730674743652344,
                    "std_dev_pg_product_phase": 0.01562887243926525,
                    "pg_product_derivation_failed_flag": False,
                    "invalid_downlink_params_flag": True,
                },
                "raw_data_analysis_quality": {
                    "i_bias": 0.06302300840616226,
                    "i_bias_significance_flag": True,
                    "q_bias": 0.114902101457119,
                    "q_bias_significance_flag": True,
                    "iq_gain_imbalance": 1.104575037956238,
                    "iq_gain_significance_flag": True,
                    "iq_quadrature_departure": -0.5162643194198608,
                    "iq_quadrature_departure_significance_flag": True,
                },
                "doppler_centroid_quality": {
                    "dc_method": "Data Analysis",
                    "doppler_centroid_uncertain_flag": False,
                },
                "image_quality": {
                    "image_statistics": {
                        "output_data_mean": {"re": -0.02062067, "im": 0.01445807},
                        "output_data_std_dev": {"re": 6.993358, "im": 6.996273},
                    },
                    "output_data_mean_outside_nominal_range_flag": True,
                    "output_data_st_dev_outside_nominal_range_flag": True,
                },
            }
        ],
    }

    assert set(res) == {
        "eopf_category",
        "title",
        "image_number",
        "quality_information",
        "general_annotation",
        "image_annotation",
        "burst_timing",
    }

    assert res["quality_information"] == expected_quality_information

    general_annotation = res["general_annotation"]
    replica = general_annotation["replica_information_list"][0]["reference_replica"]
    fm_rate = general_annotation["azimuth_fm_rate_list"][0]

    assert all(isinstance(c, float) for c in replica["amplitude_coefficients"])
    assert all(isinstance(c, float) for c in fm_rate["azimuth_fm_rate_polynomial"])
    assert "t0" in fm_rate
    assert "burst_list" not in res["burst_timing"]

    res = eopf_metadata.build_other_metadata(
        esa_safe.parse_xml(SLC_IW1_VV_annotation), "S01SIWSLC", burst_index=1
    )
    burst_timing = res["burst_timing"]

    assert all(isinstance(s, float) for s in burst_timing["first_valid_sample"])
    assert "byte_offset" not in burst_timing
    assert burst_timing["azimuth_time"] == "2021-04-01T05:26:26.966491"


@pytest.mark.parametrize(
    "safe,annotation",
    [
        [SLC_S3, SLC_S3_VH_annotation],
        [SLC_IW, SLC_IW1_VV_annotation],
        [GRD_IW, GRD_IW_VV_annotation],
    ],
)
def test_build_stac_discovery(safe: pathlib.Path, annotation: pathlib.Path) -> None:
    item = eopf_metadata.build_stac_discovery(
        "test", safe / "manifest.safe", esa_safe.parse_xml(annotation)
    )

    validator = stac_validator.StacValidate()
    result = validator.validate_dict(item)

    assert result, validator.message
    west, south, east, north = item["bbox"]
    assert west < east and south < north
    assert item["properties"]["product:type"].startswith("S01S")
    start, end = (
        item["properties"]["start_datetime"],
        item["properties"]["end_datetime"],
    )
    assert start < item["properties"]["datetime"] < end
