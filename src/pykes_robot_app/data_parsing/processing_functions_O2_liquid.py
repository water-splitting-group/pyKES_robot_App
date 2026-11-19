from pathlib import Path

import numpy as np

from pyKES.utilities.unit_handler import Quantity

from pykes_robot_app.data_parsing.raw_data_reading_functions import read_robot_log_file
from pykes_robot_app.data_parsing.baseline_correction import correct_baseline
from pykes_robot_app.data_parsing.oxygen_from_intensity import calculate_oxygen_from_intensity
from pykes_robot_app.data_parsing.general_processing_functions import (
    processing_data,
    convert_umol_L_to_mol,
    FILE_NAME_COLUMN,
)
from pykes_robot_app.parameters import PROCESSING_PARAMETERS

def raw_data_reading_function_O2_liquid(directory: Path, metadata_dict):
    """
    Read the robot log file named in the 'File name O2' column of an experiment.

    Parameters
    ----------
    directory : Path
        Directory containing the raw data files.
    metadata_dict : dict
        Metadata of the experiment, as returned by the metadata retrieval function.

    Returns
    -------
    raw_data_dict : dict
        Raw data, as returned by read_robot_log_file.
    """

    return read_robot_log_file(Path(directory) / metadata_dict[FILE_NAME_COLUMN])

def processing_function_O2_liquid(raw_data_dict, metadata_dict):
    """
    Process liquid phase O2 data given in umol/L: baseline correction, then max
    rate and max O2, once with O2 from the sensor's phase reading and once with
    O2 from its luminescence intensity during irradiation.

    Parameters
    ----------
    raw_data_dict : dict
        Raw data, as returned by the raw data reading function.
    metadata_dict : dict
        Metadata of the experiment, as returned by the metadata retrieval function.

    Returns
    -------
    processed_O2 : dict
        Baseline correction and intensity calibration, plus the processed data,
        max rate and max O2 of each O2 signal under 'intensity' and 'phase'.
    """

    time = raw_data_dict['time_s']
    start = raw_data_dict['irradiation_start_s']
    end = raw_data_dict['irradiation_end_s']
    parameters = PROCESSING_PARAMETERS['processing_parameters']

    oxygen_from_intensity, intensity_parameters, intensity_drift = calculate_oxygen_from_intensity(raw_data_dict)
    irradiated = (time >= start) & (time < end)
    oxygen_signals = {'intensity': np.where(irradiated, oxygen_from_intensity, raw_data_dict['measurement_raw']),
                      'phase': raw_data_dict['measurement_raw']}

    # Fitted outside the irradiation window only, where both signals are the phase reading
    baseline, baseline_with_step, _ = correct_baseline(time, oxygen_signals['phase'], start, end,
                                                       parameters['baseline_polynomial_order'])

    processed_O2 = {'baseline_umol_L': baseline,
                    'lbc_fit_umol_L': baseline_with_step,
                    'baseline_unit': 'umol/L',
                    'oxygen_from_intensity_umol_L': oxygen_from_intensity,
                    'intensity_model_parameters': intensity_parameters,
                    'intensity_drift': intensity_drift,
                    }

    for signal_name, oxygen in oxygen_signals.items():
        data_corrected = oxygen - baseline
        data_quantity = convert_umol_L_to_mol(data_corrected,
                                              liquid_phase_volume_ml = parameters['liquid_phase_volume_ml'])

        processed_O2[signal_name] = processing_data(time = Quantity(time, 's'),
                                                    data = data_quantity,
                                                    start = Quantity(start, 's'),
                                                    end = Quantity(end, 's'),
                                                    metadata_dict = metadata_dict)
        processed_O2[signal_name]['data_corrected_umol_L'] = data_corrected

    return processed_O2

def test_function():

    import tempfile
    import pandas as pd

    from pykes_robot_app.data_parsing.oxygen_from_intensity import evaluate_intensity_model

    # Synthetic robot log: O2 levels off during a 600 s irradiation, which heats
    # the sample by 6 K and scatters the phase-based O2 like pulsed light
    oxygen_plateau_umol_L = 60.
    rise_time_s = 40.
    time_step = 3.5
    noise_umol_L = 0.012 # white noise of the clean robot runs
    intensity_model = [165., 0.98, 0.034, -0.02]
    phases = [('DEGASSING', 'FIRESTING-START', 300), ('PREREACTION-BASELINE', 'FIRESTING-START', 900),
              ('REACTION', 'LAMP-ON', 600), ('POSTREACTION-BASELINE', 'LAMP-OFF', 300)]

    rows = []
    phase_start = 0.
    for status, command, phase_duration in phases:
        for duration in np.arange(phase_start, phase_start + phase_duration, time_step):
            rows.append({'duration': duration, 'status': status, 'command': command})
        phase_start += phase_duration

    log = pd.DataFrame(rows)
    rng = np.random.default_rng(0)
    time_since_irradiation = log['duration'] - 1200
    irradiated = log['status'] == 'REACTION'

    oxygen = (5 - 1e-4 * log['duration'] + 250 * np.exp(-log['duration'] / 60)
              + oxygen_plateau_umol_L * (1 - np.exp(-np.clip(time_since_irradiation, 0, None) / rise_time_s)))
    temperature = 24 + 2 * np.exp(-log['duration'] / 300) + 6 * np.clip(time_since_irradiation / 600, 0, 1)

    log['uM_1'] = np.where(irradiated,
                           oxygen * np.exp(rng.normal(0, 0.5, len(log))),
                           oxygen + rng.normal(0, noise_umol_L, len(log)))
    log['signal_intensity_1'] = (evaluate_intensity_model(np.vstack([oxygen, temperature - 24]), *intensity_model)
                                 * (1 + np.where(irradiated, 0.02, 0.001) * rng.standard_normal(len(log))))
    log['optical_temperature_2'] = temperature

    metadata_dict = {'experiment_name': 'SYNTHETIC-1', FILE_NAME_COLUMN: 'SYNTHETIC-1.csv'}

    with tempfile.TemporaryDirectory() as directory:
        log.to_csv(Path(directory) / metadata_dict[FILE_NAME_COLUMN], index = False)
        raw_data_dict = raw_data_reading_function_O2_liquid(directory, metadata_dict)

    processed = processing_function_O2_liquid(raw_data_dict, metadata_dict)

    liquid_volume_L = PROCESSING_PARAMETERS['processing_parameters']['liquid_phase_volume_ml'] * 1e-3
    window = processed['intensity']['max_rate_window_s']
    true_rate = oxygen_plateau_umol_L * (1 - np.exp(-window / rise_time_s)) / window * liquid_volume_L
    print(f"True rate: {true_rate:.5f} umol/s, max O2: {oxygen_plateau_umol_L * liquid_volume_L:.4f} umol")
    for signal_name in ['intensity', 'phase']:
        print(f"From {signal_name}: rate {processed[signal_name]['max_rate_umol_s']:.5f} umol/s, "
              f"max O2 {processed[signal_name]['max_oxygen_umol']:.4f} umol")

if __name__ == "__main__":
    test_function()
