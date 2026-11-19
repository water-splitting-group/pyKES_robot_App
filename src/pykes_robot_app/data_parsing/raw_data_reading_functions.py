from pathlib import Path

import pandas as pd

# Robot log rows that carry O2 measurements around the irradiation window
MEASUREMENT_STATUSES = ['PREREACTION-BASELINE', 'REACTION', 'POSTREACTION-BASELINE']
MEASUREMENT_COMMANDS = ['LAMP-ON', 'FIRESTING-START', 'LAMP-OFF']

# Dark measurements the intensity calibration is fitted on (O2 falls from air saturation during degassing)
CALIBRATION_STATUSES = ['DEGASSING', 'PREREACTION-BASELINE']
CALIBRATION_COMMAND = 'FIRESTING-START'

OXYGEN_COLUMN = 'uM_1'
INTENSITY_COLUMN = 'signal_intensity_1'
TEMPERATURE_COLUMN = 'optical_temperature_2'

def find_phase_start(time, status, phase, file_path):
    """
    Find the time of the first row of a robot program phase.

    Parameters
    ----------
    time : np.ndarray
        Time of each row.
    status : np.ndarray
        Program phase of each row.
    phase : str
        Phase to look for, e.g. 'REACTION'.
    file_path : Path
        Robot log the rows come from, named in the error message.

    Returns
    -------
    float
        Time of the first row of the phase.
    """

    phase_time = time[status == phase]

    if len(phase_time) == 0:
        raise ValueError(f"{Path(file_path).name} contains no '{phase}' rows, the run was probably aborted")

    return float(phase_time[0])

def read_robot_log_file(file_path):
    """
    Read O2 data from a photocat-hte robot log file.

    Time is re-zeroed at the start of degassing, and only the pre-reaction
    baseline, reaction and post-reaction baseline measurements are kept, plus
    the degassing and pre-reaction measurements for the intensity calibration.

    Parameters
    ----------
    file_path : Path
        Robot log CSV with the columns 'duration', 'status', 'command', 'uM_1',
        'signal_intensity_1' and 'optical_temperature_2'.

    Returns
    -------
    raw_data_dict : dict
        Time, O2 (umol/L) and luminescence intensity, start and end of the
        irradiation, and the calibration measurements.
    """

    log = pd.read_csv(file_path, low_memory = False)

    degassing_start = find_phase_start(log['duration'].to_numpy(float), log['status'].to_numpy(), 'DEGASSING', file_path)

    measurements = log[log['status'].isin(MEASUREMENT_STATUSES)
                       & log['command'].isin(MEASUREMENT_COMMANDS)]
    calibration = log[log['status'].isin(CALIBRATION_STATUSES)
                      & (log['command'] == CALIBRATION_COMMAND)]

    time_s = measurements['duration'].to_numpy(float) - degassing_start
    status = measurements['status'].to_numpy()

    # Without it the baseline fit only sees the post-reaction data
    find_phase_start(time_s, status, 'PREREACTION-BASELINE', file_path)

    raw_data_dict = {
        'time_s': time_s,
        'time_unit': 's',
        'measurement_raw': measurements[OXYGEN_COLUMN].to_numpy(float),
        'measurement_unit': 'umol/L',
        'signal_intensity': measurements[INTENSITY_COLUMN].to_numpy(float),
        # First sample of the reaction phase and first sample after it
        'irradiation_start_s': find_phase_start(time_s, status, 'REACTION', file_path),
        'irradiation_end_s': find_phase_start(time_s, status, 'POSTREACTION-BASELINE', file_path),
        'calibration_oxygen_umol_L': calibration[OXYGEN_COLUMN].to_numpy(float),
        'calibration_intensity': calibration[INTENSITY_COLUMN].to_numpy(float),
        'calibration_temperature_C': calibration[TEMPERATURE_COLUMN].to_numpy(float),
    }

    return raw_data_dict
