# Parameters used during data processing
PROCESSING_PARAMETERS = {
    'processing_parameters': {
                        'offset': 0,
                        'baseline_polynomial_order': 4,
                        'liquid_phase_volume_ml': 8.5, # 5.1 mL water + 4 x 0.85 mL stock solutions
                        # Max-rate window and (min, max) smoothing lengthscale in s, None: see docs/max_rate_settings.md
                        'max_rate_window_s': None,
                        'max_rate_lengthscale_bounds_s': None,
                    },
}

# Mapping of metadata columns to dataset groups (for visualisation)
GROUP_MAPPING = {
        'Reference': None,
        'Intensity': 'metadata/Power output [W/m^2]',
        'Duty cycle': 'metadata/Duty cycle [%]',
        'Frequency': 'metadata/Frequency [Hz]',
        'Photosensitizer':'metadata/Photosensitizer',
        'Photosensitizer concentration': 'metadata/c(photosensitizer) [M]',
        'Catalyst': 'metadata/Catalyst',
        'Catalyst concentration': 'metadata/c(catalyst) [M]',
        'Persulfate concentration': 'metadata/c(Na2S2O8) [M]',
        'pH': 'metadata/pH [-]',
        }

# Instruction for time series plotting (mapping of plot labels to dataset paths)
# and kinetic results plotting (mapping of result labels to dataset paths and units).
# Every experiment is processed twice: with O2 from the sensor's luminescence intensity during
# irradiation ('intensity') and from its phase reading ('phase'), see docs/pulsed_irradiation.md
PLOTTING_INSTRUCTIONS = {
    'time_series_instructions': {
                    'Raw': {
                        'x': 'raw_data/time_s',
                        'y': 'raw_data/measurement_raw',
                        'unit_x': 'raw_data/time_unit',
                        'unit_y': 'raw_data/measurement_unit',
                        },
                    'O2 from intensity': {
                        'x': 'raw_data/time_s',
                        'y': 'processed_data/oxygen_from_intensity_umol_L',
                        'unit_x': 'raw_data/time_unit',
                        'unit_y': 'processed_data/baseline_unit',
                        },
                    'Baseline': {
                        'x': 'raw_data/time_s',
                        'y': 'processed_data/baseline_umol_L',
                        'unit_x': 'raw_data/time_unit',
                        'unit_y': 'processed_data/baseline_unit',
                        },
                    'Baseline corrected (intensity)': {
                        'x': 'raw_data/time_s',
                        'y': 'processed_data/intensity/data_corrected_umol_L',
                        'unit_x': 'raw_data/time_unit',
                        'unit_y': 'processed_data/baseline_unit',
                        },
                    'Baseline corrected (phase)': {
                        'x': 'raw_data/time_s',
                        'y': 'processed_data/phase/data_corrected_umol_L',
                        'unit_x': 'raw_data/time_unit',
                        'unit_y': 'processed_data/baseline_unit',
                        },
                    'Reaction (intensity)': {
                        'x': 'processed_data/intensity/time_reaction_s',
                        'y': 'processed_data/intensity/data_reaction_umol',
                        'unit_x': 'processed_data/intensity/time_unit',
                        'unit_y': 'processed_data/intensity/data_unit',
                        },
                    'Reaction (phase)': {
                        'x': 'processed_data/phase/time_reaction_s',
                        'y': 'processed_data/phase/data_reaction_umol',
                        'unit_x': 'processed_data/phase/time_unit',
                        'unit_y': 'processed_data/phase/data_unit',
                        },
                    'Smoothed (intensity)': {
                        'x': 'processed_data/intensity/time_reaction_s',
                        'y': 'processed_data/intensity/smoothed_gaussian_umol',
                        'x_point': 'processed_data/intensity/max_oxygen_time_s',
                        'y_point': 'processed_data/intensity/max_oxygen_umol',
                        'unit_x': 'processed_data/intensity/time_unit',
                        'unit_y': 'processed_data/intensity/smoothed_gaussian_unit',
                        },
                    'Smoothed (phase)': {
                        'x': 'processed_data/phase/time_reaction_s',
                        'y': 'processed_data/phase/smoothed_gaussian_umol',
                        'x_point': 'processed_data/phase/max_oxygen_time_s',
                        'y_point': 'processed_data/phase/max_oxygen_umol',
                        'unit_x': 'processed_data/phase/time_unit',
                        'unit_y': 'processed_data/phase/smoothed_gaussian_unit',
                        },
                    'Rate (intensity)': {
                        'x': 'processed_data/intensity/time_rising_part_s',
                        'y': 'processed_data/intensity/rate_gaussian_umol_s',
                        'x_point': 'processed_data/intensity/max_rate_time_s',
                        'y_point': 'processed_data/intensity/max_rate_umol_s',
                        'unit_x': 'processed_data/intensity/time_unit',
                        'unit_y': 'processed_data/intensity/rate_gaussian_unit',
                        },
                    'Rate (phase)': {
                        'x': 'processed_data/phase/time_rising_part_s',
                        'y': 'processed_data/phase/rate_gaussian_umol_s',
                        'x_point': 'processed_data/phase/max_rate_time_s',
                        'y_point': 'processed_data/phase/max_rate_umol_s',
                        'unit_x': 'processed_data/phase/time_unit',
                        'unit_y': 'processed_data/phase/rate_gaussian_unit',
                        },
                },

    'kinetic_results_instructions': {
        'Max rate (intensity)': {'Value': 'processed_data/intensity/max_rate_umol_s',
                                 'Unit': 'Rate / umol/s'},
        'Max rate (phase)': {'Value': 'processed_data/phase/max_rate_umol_s',
                             'Unit': 'Rate / umol/s'},
        'Max O2 (intensity)': {'Value': 'processed_data/intensity/max_oxygen_umol',
                               'Unit': 'O2 / umol'},
        'Max O2 (phase)': {'Value': 'processed_data/phase/max_oxygen_umol',
                           'Unit': 'O2 / umol'},
    },

    'results_table_instructions': {
        'Max. rate, intensity (umol/s)': {'result': 'processed_data/intensity/max_rate_umol_s',
                                          'format': '.5f'},
        'Max. rate, phase (umol/s)': {'result': 'processed_data/phase/max_rate_umol_s',
                                      'format': '.5f'},
        'Max. rate window (s)': {'result': 'processed_data/intensity/max_rate_window_s',
                                 'format': '.1f'},
        'Max. O2, intensity (umol)': {'result': 'processed_data/intensity/max_oxygen_umol',
                                      'format': '.4f'},
        'Max. O2, phase (umol)': {'result': 'processed_data/phase/max_oxygen_umol',
                                  'format': '.4f'},
        'Max. rate flags, intensity': {'result': 'processed_data/intensity/max_rate_flags'},
        'Max. rate flags, phase': {'result': 'processed_data/phase/max_rate_flags'},
        'Intensity drift': {'result': 'processed_data/intensity_drift',
                            'format': '.3f'},
    },
}
