"""O2 from the luminescence intensity of the FireSting sensor, whose phase reading pulsed irradiation disturbs."""

import numpy as np
from scipy.optimize import curve_fit

# -----------------------------------------------------------------------------
# Intensity calibration, see docs/pulsed_irradiation.md
# -----------------------------------------------------------------------------

INITIAL_QUENCHABLE_FRACTION = 0.9
INITIAL_STERN_VOLMER_CONSTANT = 0.03   # L/umol
MAX_FIT_EVALUATIONS = 20000

# The sensor's temperature reading, and with it the phase-based O2, settles this long after irradiation
POST_IRRADIATION_SETTLING_S = 60.

def evaluate_intensity_model(oxygen_and_temperature, unquenched_intensity, quenchable_fraction,
                             stern_volmer_constant, temperature_coefficient):
    """
    Luminescence intensity after the two-site Stern-Volmer model, with an
    unquenched intensity that changes linearly with temperature.

    Parameters
    ----------
    oxygen_and_temperature : np.ndarray
        O2 in umol/L (first row) and temperature relative to the irradiation start, in K (second row).
    unquenched_intensity : float or np.ndarray
        Intensity without O2 at the irradiation start temperature.
    quenchable_fraction : float
        Fraction of the intensity that O2 quenches.
    stern_volmer_constant : float
        Stern-Volmer constant, in L/umol.
    temperature_coefficient : float
        Relative change of the unquenched intensity per K.

    Returns
    -------
    np.ndarray
        Intensity.
    """

    oxygen, temperature_difference = oxygen_and_temperature

    return (unquenched_intensity * (1 + temperature_coefficient * temperature_difference)
            * (quenchable_fraction / (1 + stern_volmer_constant * oxygen) + 1 - quenchable_fraction))

def convert_intensity_to_oxygen(intensity, unquenched_intensity, quenchable_fraction, stern_volmer_constant):
    """
    Invert the intensity model at the irradiation start temperature.

    Parameters
    ----------
    intensity : np.ndarray
        Luminescence intensity.
    unquenched_intensity : float or np.ndarray
        Intensity without O2.
    quenchable_fraction, stern_volmer_constant : float
        Parameters of the intensity model.

    Returns
    -------
    np.ndarray
        O2 in umol/L.
    """

    intensity_ratio = intensity / unquenched_intensity

    return (quenchable_fraction / (intensity_ratio - 1 + quenchable_fraction) - 1) / stern_volmer_constant

def fit_intensity_calibration(oxygen, intensity, temperature):
    """
    Fit the intensity model to dark measurements with known O2.

    Parameters
    ----------
    oxygen : np.ndarray
        Phase-based O2 of the degassing and pre-reaction measurements, in umol/L.
    intensity : np.ndarray
        Luminescence intensity of the same measurements.
    temperature : np.ndarray
        Temperature of the same measurements, in degrees C; the last one is the irradiation start.

    Returns
    -------
    np.ndarray
        Unquenched intensity, quenchable fraction, Stern-Volmer constant and temperature coefficient.
    """

    oxygen_and_temperature = np.vstack([oxygen, temperature - temperature[-1]])
    initial_parameters = [intensity.max(), INITIAL_QUENCHABLE_FRACTION, INITIAL_STERN_VOLMER_CONSTANT, 0.]

    parameters, _ = curve_fit(evaluate_intensity_model, oxygen_and_temperature, intensity,
                              p0 = initial_parameters, maxfev = MAX_FIT_EVALUATIONS)

    return parameters

def calculate_intensity_drift(time, intensity, oxygen_from_phase, irradiation_end, parameters):
    """
    Change of the unquenched intensity between irradiation start and end, from
    the post-reaction measurements, where the phase-based O2 is reliable again.

    Parameters
    ----------
    time : np.ndarray
        Time, in s.
    intensity : np.ndarray
        Luminescence intensity.
    oxygen_from_phase : np.ndarray
        Phase-based O2, in umol/L.
    irradiation_end : float
        End of the irradiation, in s.
    parameters : np.ndarray
        Fitted intensity model.

    Returns
    -------
    float
        Unquenched intensity after irradiation relative to before.
    """

    settled = time >= irradiation_end + POST_IRRADIATION_SETTLING_S
    oxygen_and_temperature = np.vstack([oxygen_from_phase[settled], np.zeros(settled.sum())])

    return float(np.median(intensity[settled] / evaluate_intensity_model(oxygen_and_temperature, *parameters)))

def calculate_oxygen_from_intensity(raw_data_dict):
    """
    Convert the luminescence intensity of a robot run to O2.

    Parameters
    ----------
    raw_data_dict : dict
        Raw data, as returned by read_robot_log_file.

    Returns
    -------
    oxygen : np.ndarray
        O2 from the intensity, in umol/L.
    parameters : np.ndarray
        Fitted intensity model.
    intensity_drift : float
        Unquenched intensity after irradiation relative to before.
    """

    time = raw_data_dict['time_s']
    intensity = raw_data_dict['signal_intensity']
    irradiation_start = raw_data_dict['irradiation_start_s']
    irradiation_end = raw_data_dict['irradiation_end_s']

    parameters = fit_intensity_calibration(raw_data_dict['calibration_oxygen_umol_L'],
                                           raw_data_dict['calibration_intensity'],
                                           raw_data_dict['calibration_temperature_C'])

    # Lamp heating lowers the unquenched intensity during irradiation; the temperature reading is
    # disturbed there too, so the drift is interpolated linearly in time instead
    intensity_drift = calculate_intensity_drift(time, intensity, raw_data_dict['measurement_raw'],
                                                irradiation_end, parameters)
    irradiation_progress = np.clip((time - irradiation_start) / (irradiation_end - irradiation_start), 0, 1)
    unquenched_intensity = parameters[0] * (1 + (intensity_drift - 1) * irradiation_progress)

    oxygen = convert_intensity_to_oxygen(intensity, unquenched_intensity, parameters[1], parameters[2])

    return oxygen, parameters, intensity_drift

def test_function():

    # Synthetic run: degassing, pre-reaction baseline, 600 s irradiation with lamp heating, post-reaction baseline
    true_parameters = [165., 0.98, 0.034, -0.02]
    time_step = 3.5
    time = np.arange(0, 3000, time_step)
    irradiation_start, irradiation_end = 2100., 2700.

    oxygen = np.where(time < 1200, 250 * np.exp(-time / 120), 0.5)
    oxygen = oxygen + 100 * np.clip(1 - np.exp(-(time - irradiation_start) / 30), 0, None)
    temperature = (24 + 2 * np.exp(-time / 500)
                   + 6 * np.clip((time - irradiation_start) / (irradiation_end - irradiation_start), 0, 1))
    intensity = evaluate_intensity_model(np.vstack([oxygen, temperature - 24]), *true_parameters)

    # Pulsed light scatters the phase-based O2 during irradiation, but hardly the intensity
    rng = np.random.default_rng(0)
    irradiated = (time >= irradiation_start) & (time < irradiation_end)
    oxygen_from_phase = np.where(irradiated, oxygen * np.exp(rng.normal(0, 0.5, time.size)), oxygen)
    intensity = intensity * (1 + np.where(irradiated, 0.02, 0.001) * rng.standard_normal(time.size))

    measured = time >= 1200
    calibration = time <= irradiation_start - time_step
    raw_data_dict = {'time_s': time[measured],
                     'measurement_raw': oxygen_from_phase[measured],
                     'signal_intensity': intensity[measured],
                     'irradiation_start_s': irradiation_start,
                     'irradiation_end_s': irradiation_end,
                     'calibration_oxygen_umol_L': oxygen[calibration],
                     'calibration_intensity': intensity[calibration],
                     'calibration_temperature_C': temperature[calibration]}

    oxygen_from_intensity, parameters, intensity_drift = calculate_oxygen_from_intensity(raw_data_dict)

    window = irradiated[measured]
    print(f"Fitted parameters: {np.round(parameters, 4)}, true: {true_parameters}")
    print(f"Intensity drift: {intensity_drift:.3f}, true: {1 + true_parameters[3] * 6:.3f}")
    for label, estimate in [('phase', oxygen_from_phase[measured]), ('intensity', oxygen_from_intensity)]:
        error = estimate[window] - oxygen[measured][window]
        print(f"RMS error during irradiation, {label}: {np.sqrt(np.mean(error**2)):.2f} umol/L")

if __name__ == "__main__":
    test_function()
