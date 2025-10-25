% temperature_model.m - GNU Octave Temperature Simulation Model
% Copyright (c) 2025 Jorge Rodriguez Moreno
%
% This script generates temperature ramps and environmental noise patterns
% for the simtemp driver testing and validation.

function temperature_model()
    % Clear workspace
    clear all;
    close all;
    clc;
    
    fprintf('=== SimTemp Temperature Model Generator ===\n');
    fprintf('Generating temperature patterns for kernel driver testing\n\n');
    
    % === Configuration Parameters ===
    sampling_period_ms = 200;  % 200ms sampling period (5 Hz)
    simulation_time_s = 120;   % 2 minutes of simulation
    
    % Calculate number of samples
    dt = sampling_period_ms / 1000.0;  % Convert to seconds
    t = 0:dt:(simulation_time_s - dt);
    num_samples = length(t);
    
    fprintf('Simulation parameters:\n');
    fprintf('  Sampling period: %d ms\n', sampling_period_ms);
    fprintf('  Simulation time: %d seconds\n', simulation_time_s);
    fprintf('  Number of samples: %d\n', num_samples);
    fprintf('  Time vector: %.3f to %.3f seconds\n', t(1), t(end));
    
    % === Temperature Models ===
    
    % 1. Linear Ramp: 20°C to 80°C over simulation time
    temp_linear = generate_linear_ramp(t, 20, 80);
    
    % 2. Exponential Ramp: Heating curve simulation
    temp_exponential = generate_exponential_ramp(t, 25, 75, 30);
    
    % 3. Sinusoidal Pattern: Daily temperature variation
    temp_sinusoidal = generate_sinusoidal_pattern(t, 35, 15, 60);
    
    % 4. Step Response: Sudden temperature changes
    temp_step = generate_step_pattern(t, [25, 45, 65, 40, 30]);
    
    % 5. Environmental Noise Models
    noise_gaussian = generate_gaussian_noise(num_samples, 0, 1.5);
    noise_environmental = generate_environmental_noise(t, 0.8, 0.3);
    
    % === Combined Models with Noise ===
    temp_ramp_noisy = temp_linear + noise_gaussian;
    temp_realistic = temp_exponential + noise_environmental;
    
    % === Export Data for Kernel Driver ===
    export_temperature_data('linear_ramp', t, temp_linear, sampling_period_ms);
    export_temperature_data('exponential_ramp', t, temp_exponential, sampling_period_ms);
    export_temperature_data('sinusoidal', t, temp_sinusoidal, sampling_period_ms);
    export_temperature_data('step_response', t, temp_step, sampling_period_ms);
    export_temperature_data('noisy_ramp', t, temp_ramp_noisy, sampling_period_ms);
    export_temperature_data('realistic', t, temp_realistic, sampling_period_ms);
    
    % === Generate Plots ===
    generate_plots(t, temp_linear, temp_exponential, temp_sinusoidal, ...
                   temp_step, temp_ramp_noisy, temp_realistic);
    
    % === Generate C Header File ===
    generate_c_header(sampling_period_ms, num_samples);
    
    fprintf('\n=== Temperature Model Generation Complete ===\n');
    fprintf('Generated files:\n');
    fprintf('  - temperature_patterns/*.csv (data files)\n');
    fprintf('  - temperature_model.h (C header for kernel)\n');
    fprintf('  - temperature_plots.png (visualization)\n');
end

function temp = generate_linear_ramp(t, start_temp, end_temp)
    % Linear temperature ramp from start_temp to end_temp
    temp = start_temp + (end_temp - start_temp) * (t / max(t));
end

function temp = generate_exponential_ramp(t, start_temp, end_temp, time_constant)
    % Exponential heating curve: T(t) = T_start + (T_end - T_start) * (1 - exp(-t/tau))
    tau = time_constant;  % Time constant in seconds
    temp = start_temp + (end_temp - start_temp) * (1 - exp(-t / tau));
end

function temp = generate_sinusoidal_pattern(t, mean_temp, amplitude, period_s)
    % Sinusoidal temperature variation: T(t) = T_mean + A * sin(2*pi*t/T)
    temp = mean_temp + amplitude * sin(2 * pi * t / period_s);
end

function temp = generate_step_pattern(t, step_temps)
    % Step response pattern with multiple temperature levels
    temp = zeros(size(t));
    num_steps = length(step_temps);
    step_duration = max(t) / num_steps;
    
    for i = 1:length(t)
        step_index = min(floor(t(i) / step_duration) + 1, num_steps);
        temp(i) = step_temps(step_index);
    end
end

function noise = generate_gaussian_noise(num_samples, mean, std_dev)
    % Generate Gaussian white noise
    noise = mean + std_dev * randn(1, num_samples);
end

function noise = generate_environmental_noise(t, base_amplitude, frequency_hz)
    % Generate realistic environmental noise (combination of frequencies)
    % Simulates air conditioning cycles, thermal mass effects, etc.
    
    % Low frequency environmental variation (HVAC cycles)
    low_freq = base_amplitude * 0.6 * sin(2 * pi * frequency_hz * t);
    
    % Medium frequency fluctuations (air currents)
    med_freq = base_amplitude * 0.3 * sin(2 * pi * frequency_hz * 3 * t);
    
    % High frequency noise (sensor noise, vibrations)
    high_freq = base_amplitude * 0.1 * randn(size(t));
    
    noise = low_freq + med_freq + high_freq;
end

function export_temperature_data(pattern_name, time_vector, temperature, sampling_ms)
    % Export temperature data to CSV for kernel driver consumption
    
    % Create output directory
    output_dir = 'temperature_patterns';
    if ~exist(output_dir, 'dir')
        mkdir(output_dir);
    end
    
    % Convert temperature to milli-Celsius (integer)
    temp_mC = round(temperature * 1000);
    
    % Create filename
    filename = sprintf('%s/%s.csv', output_dir, pattern_name);
    
    % Write CSV file with header
    fid = fopen(filename, 'w');
    if fid == -1
        error('Cannot create file: %s', filename);
    end
    
    fprintf(fid, '# Temperature Pattern: %s\n', pattern_name);
    fprintf(fid, '# Sampling Period: %d ms\n', sampling_ms);
    fprintf(fid, '# Number of Samples: %d\n', length(temperature));
    fprintf(fid, '# Format: time_ms, temp_mC\n');
    fprintf(fid, 'time_ms,temp_mC\n');
    
    for i = 1:length(time_vector)
        time_ms = round(time_vector(i) * 1000);
        fprintf(fid, '%d,%d\n', time_ms, temp_mC(i));
    end
    
    fclose(fid);
    fprintf('Exported: %s (%d samples)\n', filename, length(temperature));
end

function generate_plots(t, linear, exponential, sinusoidal, step, noisy, realistic)
    % Generate comprehensive temperature pattern plots
    
    figure('Position', [100, 100, 1200, 800]);
    
    % Plot 1: Basic Patterns
    subplot(2, 3, 1);
    plot(t, linear, 'r-', 'LineWidth', 2);
    title('Linear Ramp');
    xlabel('Time (s)');
    ylabel('Temperature (°C)');
    grid on;
    
    subplot(2, 3, 2);
    plot(t, exponential, 'g-', 'LineWidth', 2);
    title('Exponential Heating');
    xlabel('Time (s)');
    ylabel('Temperature (°C)');
    grid on;
    
    subplot(2, 3, 3);
    plot(t, sinusoidal, 'b-', 'LineWidth', 2);
    title('Sinusoidal Variation');
    xlabel('Time (s)');
    ylabel('Temperature (°C)');
    grid on;
    
    subplot(2, 3, 4);
    plot(t, step, 'm-', 'LineWidth', 2);
    title('Step Response');
    xlabel('Time (s)');
    ylabel('Temperature (°C)');
    grid on;
    
    subplot(2, 3, 5);
    plot(t, noisy, 'c-', 'LineWidth', 1);
    title('Noisy Ramp');
    xlabel('Time (s)');
    ylabel('Temperature (°C)');
    grid on;
    
    subplot(2, 3, 6);
    plot(t, realistic, 'k-', 'LineWidth', 1);
    title('Realistic Environment');
    xlabel('Time (s)');
    ylabel('Temperature (°C)');
    grid on;
    
    sgtitle('SimTemp Temperature Patterns for Kernel Driver Testing');
    
    % Save plot
    print('temperature_plots.png', '-dpng', '-r300');
    fprintf('Generated: temperature_plots.png\n');
end

function generate_c_header(sampling_ms, num_samples)
    % Generate C header file for kernel driver integration
    
    filename = 'temperature_model.h';
    fid = fopen(filename, 'w');
    if fid == -1
        error('Cannot create header file: %s', filename);
    end
    
    fprintf(fid, '/* temperature_model.h - Generated by GNU Octave */\n');
    fprintf(fid, '/* Copyright (c) 2025 Jorge Rodriguez Moreno */\n\n');
    fprintf(fid, '#ifndef _TEMPERATURE_MODEL_H_\n');
    fprintf(fid, '#define _TEMPERATURE_MODEL_H_\n\n');
    fprintf(fid, '/* Model parameters */\n');
    fprintf(fid, '#define TEMP_MODEL_SAMPLING_MS    %d\n', sampling_ms);
    fprintf(fid, '#define TEMP_MODEL_NUM_SAMPLES    %d\n', num_samples);
    fprintf(fid, '#define TEMP_MODEL_DURATION_S     %d\n', round(num_samples * sampling_ms / 1000));
    fprintf(fid, '\n');
    fprintf(fid, '/* Temperature pattern types */\n');
    fprintf(fid, 'enum temp_pattern_type {\n');
    fprintf(fid, '    TEMP_PATTERN_LINEAR = 0,\n');
    fprintf(fid, '    TEMP_PATTERN_EXPONENTIAL,\n');
    fprintf(fid, '    TEMP_PATTERN_SINUSOIDAL,\n');
    fprintf(fid, '    TEMP_PATTERN_STEP,\n');
    fprintf(fid, '    TEMP_PATTERN_NOISY_RAMP,\n');
    fprintf(fid, '    TEMP_PATTERN_REALISTIC,\n');
    fprintf(fid, '    TEMP_PATTERN_MAX\n');
    fprintf(fid, '};\n\n');
    fprintf(fid, '/* Function prototypes */\n');
    fprintf(fid, 'int load_temperature_pattern(enum temp_pattern_type pattern);\n');
    fprintf(fid, 'int get_temperature_sample(unsigned int sample_index);\n');
    fprintf(fid, 'void set_temperature_pattern(enum temp_pattern_type pattern);\n\n');
    fprintf(fid, '#endif /* _TEMPERATURE_MODEL_H_ */\n');
    
    fclose(fid);
    fprintf('Generated: %s\n', filename);
end

% Run the main function
temperature_model();