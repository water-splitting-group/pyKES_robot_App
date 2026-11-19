# O2 under pulsed irradiation

Pulsed lamp light disturbs the FireSting's usual phase reading, but hardly its **luminescence intensity**. The app therefore processes every experiment twice: once with the phase reading throughout, and once with O2 from the intensity during irradiation (outside the irradiation window the phase reading is kept). The code is in [`oxygen_from_intensity.py`](../src/pykes_robot_app/data_parsing/oxygen_from_intensity.py); [`processing_function_O2_liquid`](../src/pykes_robot_app/data_parsing/processing_functions_O2_liquid.py) applies it before the baseline correction and the max rate ([max_rate_settings.md](max_rate_settings.md)).

## The problem

The FireSting measures O2 with a luminescent dye that O2 quenches. It excites the dye with modulated red light and reads two numbers from the returned luminescence:

- the **phase angle** (`dphi_1`), which the firmware converts to O2 (`uM_1`). The conversion is temperature-compensated with the optical temperature sensor on channel 2 (`optical_temperature_2`);
- the **intensity** (`signal_intensity_1`), which O2 lowers in the same way, but which the firmware does not use.

Under continuous light (AE-917 BA-14 and BA-15) both are clean. The sensor reports a constant ambient light of about 55, which its measurement rejects.

Under pulsed light (AE-917 BA-16 to BA-29: 50 % duty cycle, 1000 W/m², 1 to 100 Hz) the phase reading breaks down:

- The ambient light jumps between about 0 and 100–540 from one sample to the next, because the lamp switches during a measurement.
- During irradiation the phase-based O2 scatters from less than half to several times its true value (e.g. 615 µmol/L where the run is at about 90 µmol/L). After lamp-off it is clean again.
- The intensity of the same measurements hardly moves. Plotted against tan(phase), the clean measurements lie on one curve; the pulsed ones form a horizontal band: the phase scatters, the intensity does not.

A plausible reason: at the high O2 levels of a running reaction the phase angle is only about 10°. A disturbance of a given size then changes tan(phase), and with it the phase-based O2, about five times more than it changes the intensity.

The temperature channel is disturbed in the same way. After lamp-off its reading needs up to about 50 s to settle. Because the firmware compensates the phase-based O2 with it, the phase-based O2 is off during that time as well: on BA-23 and BA-27 it drops by about 20 µmol/L right after lamp-off, while the intensity stays smooth.

With the phase reading, pyKES's smoothing cannot find a curve in the scatter. On AE-917 the max rates of the pulsed runs came out between 0 and 0.045 µmol/s with random peak times. The continuous runs gave 0.032 and 0.041 µmol/s.

## Method

### 1. Calibrate the intensity on the dark phases

Per run, the intensity is fitted to the phase-based O2 of the measurements without light: the **degassing** (O2 falls from air saturation, about 250 µmol/L, to almost 0, so the whole range is covered) and the **pre-reaction baseline**. The model is the two-site Stern–Volmer model with a temperature-dependent unquenched intensity:

I = I₀ · (1 + a·ΔT) · ( f / (1 + K·c) + 1 − f )

- c: O2 in µmol/L, I: intensity;
- I₀: intensity without O2 at the irradiation start;
- f: fraction of the luminescence that O2 can quench, K: Stern–Volmer constant;
- a: relative change of I₀ per K, ΔT: temperature relative to the last pre-reaction sample (the irradiation start).

The temperature term is needed because the sample cools by 2–3 K during degassing while O2 falls. Without it the fit attributes part of the cooling to O2, and the intensity-based rates of continuous runs came out 4–5 % low.

### 2. Convert intensity to O2

The model is inverted at the irradiation start temperature (ΔT = 0).

### 3. Correct the drift from lamp heating

The lamp heats the sample (continuous light: 24 → 32 °C in 10 min; pulsed: to about 30 °C), which lowers I₀. The temperature reading cannot be used for this during pulsing. The drift is therefore measured after lamp-off: in the post-reaction baseline, skipping its first 60 s, the measured intensity is divided by the intensity the model expects for the phase-based O2. The median of this ratio is the **intensity drift** (stored as `intensity_drift`). I₀ is interpolated linearly in time from its value at lamp-on to this ratio at lamp-off, since the temperature rises linearly under constant lamp power.

Typical values on AE-917: 0.83–0.89 for continuous runs and 0.87–0.95 for pulsed runs. A value far outside 0.8–1 points to a problem with the run.

The drift acts on I₀, not on O2. A run without O2 evolution (blank) therefore stays at zero, instead of showing a few µmol/L of fake O2 from the heating.

### 4. Replace the irradiation window

For the intensity results, the phase-based O2 inside the irradiation window is replaced by the intensity-based O2. The baseline is fitted outside the irradiation window only, where both signals are the phase reading, so both results share it. The max-rate method then runs once per signal.

## Both results in the app

| Key in `processed_data` | Meaning |
|---|---|
| `intensity/...` | Results with intensity-based O2 during irradiation (same keys as in [max_rate_settings.md](max_rate_settings.md)) |
| `phase/...` | Results with the phase reading throughout |
| `oxygen_from_intensity_umol_L` | Intensity-based O2 of the whole run (Time Series: "O2 from intensity") |
| `intensity_drift`, `intensity_model_parameters` | Drift and fitted intensity model (I₀, f, K, a) |
| `baseline_umol_L`, `lbc_fit_umol_L` | Baseline shared by both results |

The results table, the Analysis Results page and the Time Series page show every result with "(intensity)" or "(phase)". Overlaying "O2 from intensity" on "Raw" shows the calibration outside irradiation and the replaced window.

Which one to use:

- **Pulsed experiments, and everything compared with them:** intensity. Experiments that are compared must use the same signal, continuous references included.
- **Experiments that are all under continuous light:** phase. It is the reading the manufacturer calibrates, and slightly more accurate there (see the BC-13 bursts below).

On continuous runs the two should agree within a few percent; a larger difference points to a problem with the run or the calibration. Processing takes about twice as long as with one signal.

## Validation

### Clean runs: intensity vs phase

On runs under continuous light the phase-based O2 is reliable during irradiation and serves as the truth. The table shows the result with intensity-based O2 divided by the result with phase-based O2:

| Runs | Max rate | Max O2 |
|---|---|---|
| MRG-059 BA-06 to BA-09 (continuous) | 1.00–1.03 | 0.98–1.00 |
| AE-917 BA-14, BA-15 (continuous) | 0.99, 0.99 | 1.02, 1.01 |
| MRG-059 BC bursts (8 runs) | 0.93–1.02 (median 0.98) | 0.93–1.02 |

Median over all 14 runs: 0.99 for the max rate and 0.98 for max O2. The two lowest values are the brightest bursts (BC-13, 140 µmol/L within 30 s; see Limits).

### Pulsed runs

There is no truth during pulsed irradiation, so the following checks were made:

- **Lamp-off.** If pulsing biased the intensity, the intensity would jump when the lamp switches off. Straight lines through the last 90 s of irradiation and the first 90 s after it meet within ±1.6 % on most runs, and within 2.5–3.8 % on the 1 Hz and 10 Hz runs. The sign varies from run to run, so there is no frequency-dependent bias.
- **Noise.** The relative intensity noise under pulsed light is 1.5–6 % (continuous: about 0.1 %), roughly uncorrelated from sample to sample. That is 2–8 % of the O2 level, less than the 7–19 % scatter the max-rate method was benchmarked for.
- **Earlier pulsed runs.** On MRG-059 BA-10 to BA-13, whose phase reading was only moderately disturbed, the max rate changed by −6 % to +16 %.

### Synthetic runs

[`tests/test_oxygen_from_intensity.py`](../tests/test_oxygen_from_intensity.py) simulates runs with a known sensor model, cooling during degassing, 6 K lamp heating, phase scatter of a factor e^±0.5 and 2 % intensity noise during irradiation. Checks:

- the fit recovers the sensor model;
- the drift equals the simulated heating effect within 0.5 %;
- without noise, the intensity-based O2 is within 1 % of the truth everywhere during irradiation (measured: 0.4 %);
- with noise it is unbiased (mean error −0.1 % of the plateau, RMS 2.4 %);
- the full processing recovers the max rate (measured: 97–100 % over 5 noise realizations).

## AE-917 results

Max rate in µmol/s (pyKES quality flags in brackets):

| Frequency | First replicate (BA-14, 16, …) | Second replicate (BA-15, 17, …) |
|---|---|---|
| continuous | 0.0317 | 0.0409 |
| 1 Hz | 0.0283 | 0.0277 |
| 2 Hz | 0.0285 | 0.0342 |
| 5 Hz | 0.0255 | 0.0302 |
| 10 Hz | 0.0260 | 0.0293 (lengthscale at lower bound) |
| 20 Hz | 0.0215 | 0.0258 |
| 50 Hz | 0.0205 | 0.0275 (lengthscale at lower bound) |
| 100 Hz | 0.0218 | 0.0249 |

Two observations that are not caused by pulsing:

- **The second replicate reads 13–34 % higher** at every condition except 1 Hz (−2 %). This includes BA-29, whose baseline is clean.
- **Several pre-reaction baselines are not at zero.** In BA-15 to BA-21 the pre-reaction baseline rises from 24–37 to 43–56 µmol/L, as if O2 were leaking in; in BA-23 to BA-27 it falls from 17–29 to 13–18 µmol/L, as if degassing were incomplete; in BA-28 it rises from 1 to 14 µmol/L. In BA-17, 23, 25 and 27 the baseline polynomial bends inside the irradiation window, so their max O2 is found at the end of the window. This affects max O2 (not the max rate) and also occurs under continuous light (BA-15).

## Limits

- **Bright bursts read a few percent low.** On the BC-13 bursts the intensity-based O2 falls up to 7 % below the phase-based O2 within the first 40 s of irradiation, although the calibration before irradiation is accurate. So the lamp itself changes the intensity a little. On the other clean runs the effect is −4 % to +3 %.
- **Aliasing at some frequencies.** At 1 and 10 Hz the intensity-based O2 alternates from sample to sample by up to about ±10 µmol/L, likely because the pulse frequency and the 3.5 s sampling interval beat. The smoothing averages it out, but those runs are noisier (5–6 % intensity noise instead of 1.5–3 %).
- **Linear drift.** The drift correction assumes that the sample heats linearly during irradiation, as it does under constant (average) lamp power.
- **Inputs.** The method needs the degassing measurements (for the O2 range of the calibration), the intensity and the temperature channel of the robot log. Datasets saved by an earlier version of the app lack them: re-upload the raw files instead of reprocessing the HDF5 file.
