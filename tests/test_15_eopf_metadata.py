import pathlib

from xarray_sentinel import eopf_metadata

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_S3 = (
    DATA_FOLDER
    / "S1A_S3_SLC__1SDV_20210401T152855_20210401T152914_037258_04638E_6001.SAFE"
)
SLC_S3_VH_annotation = (
    SLC_S3
    / "annotation"
    / "s1a-s3-slc-vh-20210401t152855-20210401t152914-037258-04638e-001.xml"
)


def test_to_snake_recursive() -> None:
    metadata = {"qualityInformation": {"qualityDataList": [{"qualityData": 2}]}}
    expected = {"quality_information": {"quality_data_list": [{"quality_data": 2}]}}

    res = eopf_metadata.to_snake_recursive(metadata)

    assert res == expected


def test_build_other_metadata() -> None:
    res = eopf_metadata.build_other_metadata(SLC_S3_VH_annotation)
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

    assert len(res) == 5

    assert res["quality_information"] == expected_quality_information
