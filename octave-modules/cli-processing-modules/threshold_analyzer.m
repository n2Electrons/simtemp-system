function result = threshold_analyzer(temp_data, current_threshold, sampling_period)
% THRESHOLD_ANALYZER Analyzes temperature threshold crossing patterns
%
% This function analyzes temperature data to determine optimal threshold
% settings and predict crossing events for the Challenge 2025 sensor system.
%
% Inputs:
%   temp_data       - Vector of temperature readings in milli-degrees Celsius
%   current_threshold - Current threshold value in milli-degrees Celsius
%   sampling_period - Sampling period in milliseconds
%
% Outputs:
%   result.optimal_threshold - Recommended threshold value
%   result.crossing_probability - Probability of threshold crossing
%   result.time_to_crossing - Estimated time to next crossing (ms)
%   result.analysis_stats - Statistical analysis of the data

    % Validate inputs
    if nargin < 3
        error('threshold_analyzer: requires 3 input arguments');
    end
    
    if isempty(temp_data) || length(temp_data) < 2
        error('threshold_analyzer: temp_data must contain at least 2 samples');
    end
    
    % Convert to Celsius for easier calculation
    temp_celsius = temp_data / 1000.0;
    threshold_celsius = current_threshold / 1000.0;
    
    % Basic statistics
    mean_temp = mean(temp_celsius);
    std_temp = std(temp_celsius);
    min_temp = min(temp_celsius);
    max_temp = max(temp_celsius);
    
    % Temperature trend analysis
    time_vector = (0:length(temp_celsius)-1) * sampling_period / 1000; % seconds
    trend_coeff = polyfit(time_vector, temp_celsius, 1);
    trend_slope = trend_coeff(1); % degrees/second
    
    % Crossing analysis
    crossings = find_threshold_crossings(temp_celsius, threshold_celsius);
    crossing_count = length(crossings);
    
    % Calculate optimal threshold based on statistics
    % Use mean + 2*std as a reasonable threshold that avoids noise
    optimal_threshold_celsius = mean_temp + 2 * std_temp;
    
    % Ensure threshold is within reasonable bounds
    optimal_threshold_celsius = max(optimal_threshold_celsius, mean_temp + std_temp);
    optimal_threshold_celsius = min(optimal_threshold_celsius, max_temp - std_temp);
    
    % Crossing probability estimation
    if std_temp > 0
        % Use normal distribution to estimate crossing probability
        z_score = (threshold_celsius - mean_temp) / std_temp;
        crossing_probability = 1 - normcdf(z_score);
    else
        crossing_probability = 0;
    end
    
    % Time to crossing estimation
    if trend_slope > 0 && threshold_celsius > mean_temp
        % Temperature rising, estimate time to reach threshold
        current_temp = temp_celsius(end);
        temp_diff = threshold_celsius - current_temp;
        time_to_crossing = (temp_diff / trend_slope) * 1000; % convert to ms
    elseif trend_slope < 0 && threshold_celsius < mean_temp
        % Temperature falling, estimate time to cross below threshold
        current_temp = temp_celsius(end);
        temp_diff = current_temp - threshold_celsius;
        time_to_crossing = (temp_diff / abs(trend_slope)) * 1000; % convert to ms
    else
        time_to_crossing = -1; % No crossing expected
    end
    
    % Compile results
    result.optimal_threshold = round(optimal_threshold_celsius * 1000); % convert back to milli-C
    result.crossing_probability = crossing_probability;
    result.time_to_crossing = max(0, time_to_crossing);
    result.analysis_stats = struct(...
        'mean_temp_mC', round(mean_temp * 1000), ...
        'std_temp_mC', round(std_temp * 1000), ...
        'min_temp_mC', round(min_temp * 1000), ...
        'max_temp_mC', round(max_temp * 1000), ...
        'trend_slope_C_per_sec', trend_slope, ...
        'crossing_count', crossing_count, ...
        'data_points', length(temp_data) ...
    );
    
    % Log analysis results
    fprintf('Threshold Analysis Results:\n');
    fprintf('  Current threshold: %.1f°C\n', threshold_celsius);
    fprintf('  Optimal threshold: %.1f°C\n', optimal_threshold_celsius);
    fprintf('  Crossing probability: %.2f%%\n', crossing_probability * 100);
    fprintf('  Temperature trend: %.3f°C/s\n', trend_slope);
    if time_to_crossing > 0
        fprintf('  Estimated time to crossing: %.1f ms\n', time_to_crossing);
    else
        fprintf('  No crossing expected with current trend\n');
    end
end

function crossings = find_threshold_crossings(temp_data, threshold)
% Find indices where temperature crosses the threshold
    crossings = [];
    for i = 2:length(temp_data)
        if (temp_data(i-1) <= threshold && temp_data(i) > threshold) || ...
           (temp_data(i-1) >= threshold && temp_data(i) < threshold)
            crossings = [crossings, i];
        end
    end
end