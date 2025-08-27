import pathlib

from xarray_sentinel import eopf_metadata

DATA_FOLDER = pathlib.Path(__file__).parent / "data"

SLC_IW = (
    DATA_FOLDER
    / "S1B_IW_SLC__1SDV_20210401T052622_20210401T052650_026269_032297_EFA4.SAFE"
)


def test_to_snake_recursive() -> None:
    metadata = {"qualityInformation": {"qualityDataList": [{"qualityData": 2}]}}
    expected = {"quality_information": {"quality_data_list": [{"quality_data": 2}]}}

    res = eopf_metadata.to_snake_recursive(metadata)

    assert res == expected


def test_build_other_metadata() -> None:
    res = eopf_metadata.build_other_metadata(SLC_IW)
    expected_quality_information = {
        "product_quality_index": 0.0,
        "quality_data_list": [
            {
                "azimuth_time": "2021-04-01T05:26:24.209990",
                "downlink_quality": {
                    "i_input_data_mean": 0.3338871002197266,
                    "q_input_data_mean": 0.08810008317232132,
                    "input_data_mean_outside_nominal_range_flag": False,
                    "i_input_data_std_dev": 10.48145961761475,
                    "q_input_data_std_dev": 10.50522994995117,
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
                    "mean_pg_product_amplitude": 0.624697744846344,
                    "std_dev_pg_product_amplitude": 0.006798196118324995,
                    "mean_pg_product_phase": 0.9386667609214783,
                    "std_dev_pg_product_phase": 0.01930363848805428,
                    "pg_product_derivation_failed_flag": False,
                    "invalid_downlink_params_flag": True,
                },
                "raw_data_analysis_quality": {
                    "i_bias": 0.3338871002197266,
                    "i_bias_significance_flag": True,
                    "q_bias": 0.08810008317232132,
                    "q_bias_significance_flag": True,
                    "iq_gain_imbalance": 0.9977372884750366,
                    "iq_gain_significance_flag": True,
                    "iq_quadrature_departure": 0.04520197957754135,
                    "iq_quadrature_departure_significance_flag": True,
                },
                "doppler_centroid_quality": {
                    "dc_method": "Data Analysis",
                    "doppler_centroid_uncertain_flag": False,
                },
                "image_quality": {
                    "image_statistics": {
                        "output_data_mean": {"re": -0.01723112, "im": 0.01067772},
                        "output_data_std_dev": {"re": 85.68334, "im": 85.67197},
                    },
                    "output_data_mean_outside_nominal_range_flag": True,
                    "output_data_st_dev_outside_nominal_range_flag": True,
                },
            }
        ],
    }
    assert len(res) == 5

    assert res["quality_information"] == expected_quality_information
