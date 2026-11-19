"""O2 from the luminescence intensity on synthetic robot runs whose phase reading pulsed light disturbs."""

import numpy as np
import pytest

from pykes_robot_app.data_parsing.oxygen_from_intensity import (
    calculate_oxygen_from_intensity,
    evaluate_intensity_model,
    fit_intensity_calibration,
)
from pykes_robot_app.data_parsing.processing_functions_O2_liquid import processing_function_O2_liquid

from test_max_rate import TIME_STEP, LIQUID_VOLUME_L, calculate_continuous_curve, calculate_true_max_rate

# -----------------------------------------------------------------------------
# Synthetic robot run: degassing from air saturation, pre-reaction baseline,
# 600 s irradiation that heats the sample, post-reaction baseline
# -----------------------------------------------------------------------------

DEGASSING_END = 1200.            # s
IRRADIATION_START = 2100.        # s
IRRADIATION_END = 2700.          # s
TOTAL_TIME = 3000.               # s
AIR_SATURATION = 250.            # umol/L
DEGASSING_TIME_CONSTANT = 120.   # s

# Unquenched intensity at room temperature, quenchable fraction, Stern-Volmer constant (L/umol), temperature coefficient (1/K)
TRUE_INTENSITY_MODEL = (165., 0.98, 0.034, -0.02)
ROOM_TEMPERATURE = 24.           # C
DEGASSING_COOLING = 2.           # K, the sample cools down to room temperature during degassing ...
COOLING_TIME_CONSTANT = 500.     # s
LAMP_HEATING = 6.                # K, ... and heats up linearly during irradiation

PHASE_SCATTER = 0.5              # log-normal scatter of the phase-based O2 under pulsed light
CLEAN_INTENSITY_NOISE = 0.001    # relative intensity noise without light ...
PULSED_INTENSITY_NOISE = 0.02    # ... and under pulsed light, as on the robot runs
SEEDS = 5

def simulate_run(seed: int, irradiation_intensity_noise: float = PULSED_INTENSITY_NOISE):
    """
    Synthetic raw data of a robot run under pulsed light.

    Parameters
    ----------
    seed : int
        Seed of the noise realization.
    irradiation_intensity_noise : float, optional
        Relative intensity noise during irradiation.

    Returns
    -------
    raw_data_dict : dict
        Raw data, as returned by read_robot_log_file.
    true_oxygen : np.ndarray
        Noise-free O2 of the measurements, in umol/L.
    """

    time = np.arange(0, TOTAL_TIME, TIME_STEP)
    irradiated = (time >= IRRADIATION_START) & (time < IRRADIATION_END)
    irradiation_progress = np.clip((time - IRRADIATION_START) / (IRRADIATION_END - IRRADIATION_START), 0, 1)

    oxygen = (AIR_SATURATION * np.exp(-time / DEGASSING_TIME_CONSTANT)
              + calculate_continuous_curve(time - IRRADIATION_START))
    temperature = (ROOM_TEMPERATURE + DEGASSING_COOLING * np.exp(-time / COOLING_TIME_CONSTANT)
                   + LAMP_HEATING * irradiation_progress)
    intensity = evaluate_intensity_model(np.vstack([oxygen, temperature - ROOM_TEMPERATURE]), *TRUE_INTENSITY_MODEL)

    rng = np.random.default_rng(seed)
    oxygen_from_phase = np.where(irradiated, oxygen * np.exp(PHASE_SCATTER * rng.standard_normal(time.size)), oxygen)
    intensity_noise = np.where(irradiated, irradiation_intensity_noise, CLEAN_INTENSITY_NOISE)
    intensity = intensity * (1 + intensity_noise * rng.standard_normal(time.size))

    measured = time >= DEGASSING_END
    calibration = time < IRRADIATION_START

    raw_data_dict = {'time_s': time[measured],
                     'measurement_raw': oxygen_from_phase[measured],
                     'signal_intensity': intensity[measured],
                     'irradiation_start_s': IRRADIATION_START,
                     'irradiation_end_s': IRRADIATION_END,
                     'calibration_oxygen_umol_L': oxygen[calibration],
                     'calibration_intensity': intensity[calibration],
                     'calibration_temperature_C': temperature[calibration]}

    return raw_data_dict, oxygen[measured]

def calculate_irradiation_errors(seed: int, irradiation_intensity_noise: float) -> np.ndarray:
    """
    Error of the intensity-based O2 during irradiation, relative to the plateau.

    Parameters
    ----------
    seed : int
        Seed of the noise realization.
    irradiation_intensity_noise : float
        Relative intensity noise during irradiation.

    Returns
    -------
    np.ndarray
        Error of every irradiated sample, as a fraction of the largest true O2.
    """

    raw_data_dict, true_oxygen = simulate_run(seed, irradiation_intensity_noise)
    oxygen, _, _ = calculate_oxygen_from_intensity(raw_data_dict)

    time = raw_data_dict['time_s']
    irradiated = (time >= IRRADIATION_START) & (time < IRRADIATION_END)

    return (oxygen[irradiated] - true_oxygen[irradiated]) / true_oxygen[irradiated].max()

def test_calibration_recovers_intensity_model():
    raw_data_dict, _ = simulate_run(0)
    temperature = raw_data_dict['calibration_temperature_C']

    parameters = fit_intensity_calibration(raw_data_dict['calibration_oxygen_umol_L'],
                                           raw_data_dict['calibration_intensity'],
                                           temperature)

    # The fitted unquenched intensity refers to the irradiation start temperature
    unquenched_intensity, quenchable_fraction, stern_volmer_constant, temperature_coefficient = TRUE_INTENSITY_MODEL
    expected = [unquenched_intensity * (1 + temperature_coefficient * (temperature[-1] - ROOM_TEMPERATURE)),
                quenchable_fraction, stern_volmer_constant]

    assert parameters[:3] == pytest.approx(expected, rel=0.01)
    assert parameters[3] == pytest.approx(temperature_coefficient, rel=0.05)

def test_drift_follows_lamp_heating():
    raw_data_dict, _ = simulate_run(0)

    _, _, intensity_drift = calculate_oxygen_from_intensity(raw_data_dict)

    assert intensity_drift == pytest.approx(1 + TRUE_INTENSITY_MODEL[3] * LAMP_HEATING, rel=0.005)

def test_oxygen_from_intensity_without_noise():
    errors = calculate_irradiation_errors(0, CLEAN_INTENSITY_NOISE)

    assert np.abs(errors).max() < 0.01

def test_oxygen_from_intensity_is_unbiased_under_pulsed_light():
    errors = np.concatenate([calculate_irradiation_errors(seed, PULSED_INTENSITY_NOISE) for seed in range(SEEDS)])

    assert abs(np.mean(errors)) < 0.005
    assert np.sqrt(np.mean(errors**2)) < 0.04

def test_processing_recovers_max_rate_under_pulsed_light():
    rate_ratios = []
    for seed in range(SEEDS):
        raw_data_dict, _ = simulate_run(seed)
        processed = processing_function_O2_liquid(raw_data_dict, {})['intensity']
        true_rate = calculate_true_max_rate(calculate_continuous_curve, processed['max_rate_window_s'])
        rate_ratios.append(processed['max_rate_umol_s'] / true_rate)

    assert np.median(rate_ratios) == pytest.approx(1, abs=0.1)
    assert max(rate_ratios) < 1.15

def test_signals_differ_only_during_irradiation():
    raw_data_dict, _ = simulate_run(0)
    time = raw_data_dict['time_s']
    irradiated = (time >= IRRADIATION_START) & (time < IRRADIATION_END)

    processed = processing_function_O2_liquid(raw_data_dict, {})
    intensity_corrected = processed['intensity']['data_corrected_umol_L']
    phase_corrected = processed['phase']['data_corrected_umol_L']

    assert phase_corrected == pytest.approx(raw_data_dict['measurement_raw'] - processed['baseline_umol_L'])
    assert intensity_corrected[~irradiated] == pytest.approx(phase_corrected[~irradiated])
    assert intensity_corrected[irradiated] == pytest.approx(processed['oxygen_from_intensity_umol_L'][irradiated]
                                                            - processed['baseline_umol_L'][irradiated])
