function optimal_period = sampling_optimizer(temp_data, timestamps, current_period)
% SAMPLING_OPTIMIZER Determines optimal sampling period for temperature sensor
%
% This function analyzes temperature data to determine the optimal sampling
% period that balances data quality with system resources for the Challenge 2025
% sensor system.
%
% Inputs:
%   temp_data      - Vector of temperature readings in milli-degrees Celsius
%   timestamps     - Vector of timestamps in nanoseconds
%   current_period - Current sampling period in milliseconds
%
% Outputs:
%   optimal_period - Recommended optimal sampling period in milliseconds

    % Validate inputs
    if nargin < 3
        error('sampling_optimizer: requires 3 input arguments');
    end
    
    if length(temp_data) ~= length(timestamps)
        error('sampling_optimizer: temp_data and timestamps must have same length');
    end
    
    if length(temp_data) < 10
        warning('sampling_optimizer: need more data points for accurate optimization');
        optimal_period = current_period;
        return;
    end
    
    % Convert timestamps to seconds and calculate actual sampling intervals
    time_seconds = timestamps / 1e9;
    actual_intervals = diff(time_seconds) * 1000; % convert to milliseconds
    mean_actual_period = mean(actual_intervals);
    
    % Convert temperature to Celsius
    temp_celsius = temp_data / 1000.0;
    
    % Analyze temperature characteristics
    temp_stats = analyze_temperature_characteristics(temp_celsius, time_seconds);
    
    % Determine optimal sampling based on different criteria
    nyquist_period = calculate_nyquist_period(temp_celsius, time_seconds);
    change_based_period = calculate_change_based_period(temp_celsius, actual_intervals);
    noise_based_period = calculate_noise_based_period(temp_celsius, actual_intervals);
    
    % Combine criteria to get optimal period
    candidate_periods = [nyquist_period, change_based_period, noise_based_period];
    
    % Remove invalid periods
    candidate_periods = candidate_periods(candidate_periods > 0);
    candidate_periods = candidate_periods(candidate_periods >= 10); % minimum 10ms
    candidate_periods = candidate_periods(candidate_periods <= 10000); % maximum 10s
    
    if isempty(candidate_periods)
        optimal_period = current_period;
        fprintf('Warning: Could not determine optimal period, keeping current: %d ms\n', current_period);
        return;
    end
    
    % Choose conservative approach - use median of candidates
    optimal_period = round(median(candidate_periods));
    
    % Ensure optimal period is reasonable compared to current
    % Don't suggest changes more than 4x faster or 4x slower
    max_change_factor = 4;
    if optimal_period < current_period / max_change_factor
        optimal_period = round(current_period / max_change_factor);
    elseif optimal_period > current_period * max_change_factor
        optimal_period = round(current_period * max_change_factor);
    end
    
    % Log optimization results
    fprintf('Sampling Period Optimization Results:\n');
    fprintf('  Current period: %d ms\n', current_period);
    fprintf('  Mean actual period: %.1f ms\n', mean_actual_period);
    fprintf('  Optimal period: %d ms\n', optimal_period);
    fprintf('  Temperature change rate: %.3f°C/s\n', temp_stats.change_rate);
    fprintf('  Temperature noise level: %.3f°C\n', temp_stats.noise_level);
    
    if optimal_period ~= current_period
        change_factor = current_period / optimal_period;
        if change_factor > 1
            fprintf('  Recommendation: Increase sampling rate by %.1fx\n', change_factor);
        else
            fprintf('  Recommendation: Decrease sampling rate by %.1fx\n', 1/change_factor);
        end
    else
        fprintf('  Recommendation: Current sampling period is optimal\n');
    end
end

function stats = analyze_temperature_characteristics(temp_celsius, time_seconds)
% Analyze basic temperature characteristics
    stats = struct();
    
    % Calculate temperature change rate
    temp_diff = diff(temp_celsius);
    time_diff = diff(time_seconds);
    change_rates = abs(temp_diff ./ time_diff);
    stats.change_rate = mean(change_rates);
    stats.max_change_rate = max(change_rates);
    
    % Calculate noise level (high frequency variations)
    if length(temp_celsius) > 5
        % Use moving average to separate trend from noise
        window_size = min(5, floor(length(temp_celsius)/3));
        trend = movmean(temp_celsius, window_size);
        noise = temp_celsius - trend;
        stats.noise_level = std(noise);
    else
        stats.noise_level = std(temp_celsius);
    end
    
    % Calculate frequency content
    if length(temp_celsius) > 10
        fs = 1 / mean(diff(time_seconds)); % sampling frequency
        [psd, freq] = periodogram(temp_celsius - mean(temp_celsius), [], [], fs);
        
        % Find dominant frequency
        [~, max_idx] = max(psd);
        stats.dominant_frequency = freq(max_idx);
        
        % Calculate bandwidth (frequency containing 90% of energy)
        cumulative_energy = cumsum(psd) / sum(psd);
        bandwidth_idx = find(cumulative_energy >= 0.9, 1);
        stats.bandwidth = freq(bandwidth_idx);
    else
        stats.dominant_frequency = 0;
        stats.bandwidth = 0;
    end
end

function period = calculate_nyquist_period(temp_celsius, time_seconds)
% Calculate period based on Nyquist criterion
    stats = analyze_temperature_characteristics(temp_celsius, time_seconds);
    
    if stats.bandwidth > 0
        % Nyquist frequency is 2x the bandwidth
        nyquist_freq = 2 * stats.bandwidth;
        period = 1000 / nyquist_freq; % convert to milliseconds
    else
        period = -1; % Invalid
    end
end

function period = calculate_change_based_period(temp_celsius, intervals)
% Calculate period based on temperature change characteristics
    if length(temp_celsius) < 3
        period = -1;
        return;
    end
    
    % Calculate temperature changes
    temp_changes = abs(diff(temp_celsius));
    
    % Find typical change magnitude
    typical_change = median(temp_changes);
    
    % If typical change is very small, we might be oversampling
    if typical_change < 0.01 % less than 0.01°C change between samples
        % Suggest slower sampling
        period = median(intervals) * 2;
    elseif typical_change > 0.5 % more than 0.5°C change between samples
        % Suggest faster sampling
        period = median(intervals) / 2;
    else
        % Current sampling seems appropriate
        period = median(intervals);
    end
end

function period = calculate_noise_based_period(temp_celsius, intervals)
% Calculate period based on noise characteristics
    if length(temp_celsius) < 5
        period = -1;
        return;
    end
    
    % Calculate signal-to-noise ratio
    signal_level = std(temp_celsius);
    
    % Estimate noise from high-frequency components
    if length(temp_celsius) > 10
        % Use difference between consecutive samples as noise estimate
        noise_estimate = std(diff(temp_celsius)) / sqrt(2);
    else
        noise_estimate = signal_level * 0.1; % assume 10% noise
    end
    
    if noise_estimate > 0
        snr = signal_level / noise_estimate;
        
        % If SNR is high, we can sample slower
        % If SNR is low, we might need faster sampling for averaging
        if snr > 10
            period = median(intervals) * 1.5;
        elseif snr < 3
            period = median(intervals) * 0.7;
        else
            period = median(intervals);
        end
    else
        period = median(intervals);
    end
end