function prediction = alert_predictor(temp_data, timestamps, threshold, mode)
% ALERT_PREDICTOR Predicts temperature alert events for sensor system
%
% This function analyzes temperature trends and patterns to predict when
% temperature alerts might occur in the Challenge 2025 sensor system.
%
% Inputs:
%   temp_data  - Vector of temperature readings in milli-degrees Celsius
%   timestamps - Vector of timestamps in nanoseconds
%   threshold  - Alert threshold in milli-degrees Celsius
%   mode       - Sensor mode: 'normal', 'noisy', or 'ramp'
%
% Outputs:
%   prediction.will_alert     - Boolean: will an alert occur soon?
%   prediction.time_to_alert  - Estimated time to alert in milliseconds
%   prediction.confidence     - Confidence level (0-1)
%   prediction.alert_type     - 'rising', 'falling', or 'oscillating'
%   prediction.recommendations - Suggested actions

    % Validate inputs
    if nargin < 4
        error('alert_predictor: requires 4 input arguments');
    end
    
    if length(temp_data) ~= length(timestamps)
        error('alert_predictor: temp_data and timestamps must have same length');
    end
    
    if length(temp_data) < 3
        warning('alert_predictor: insufficient data for prediction');
        prediction = create_default_prediction();
        return;
    end
    
    % Convert to working units
    temp_celsius = temp_data / 1000.0;
    threshold_celsius = threshold / 1000.0;
    time_seconds = timestamps / 1e9;
    
    % Analyze current temperature trend
    trend_analysis = analyze_temperature_trend(temp_celsius, time_seconds);
    
    % Mode-specific prediction
    switch lower(mode)
        case 'normal'
            prediction = predict_normal_mode(temp_celsius, time_seconds, threshold_celsius, trend_analysis);
        case 'noisy'
            prediction = predict_noisy_mode(temp_celsius, time_seconds, threshold_celsius, trend_analysis);
        case 'ramp'
            prediction = predict_ramp_mode(temp_celsius, time_seconds, threshold_celsius, trend_analysis);
        otherwise
            warning('alert_predictor: unknown mode "%s", using normal mode', mode);
            prediction = predict_normal_mode(temp_celsius, time_seconds, threshold_celsius, trend_analysis);
    end
    
    % Add general recommendations
    prediction.recommendations = generate_recommendations(prediction, temp_celsius, threshold_celsius, mode);
    
    % Log prediction results
    log_prediction_results(prediction, temp_celsius(end), threshold_celsius, mode);
end

function trend = analyze_temperature_trend(temp_celsius, time_seconds)
% Analyze temperature trend characteristics
    trend = struct();
    
    % Current temperature
    trend.current_temp = temp_celsius(end);
    
    % Linear trend over entire dataset
    p = polyfit(time_seconds, temp_celsius, 1);
    trend.slope = p(1); % degrees per second
    trend.intercept = p(2);
    
    % Short-term trend (last 25% of data or minimum 3 points)
    short_term_points = max(3, floor(length(temp_celsius) * 0.25));
    if length(temp_celsius) >= short_term_points
        recent_time = time_seconds(end-short_term_points+1:end);
        recent_temp = temp_celsius(end-short_term_points+1:end);
        p_short = polyfit(recent_time, recent_temp, 1);
        trend.short_slope = p_short(1);
    else
        trend.short_slope = trend.slope;
    end
    
    % Temperature variability
    trend.std_dev = std(temp_celsius);
    trend.range = max(temp_celsius) - min(temp_celsius);
    
    % Rate of change
    if length(temp_celsius) > 1
        temp_changes = diff(temp_celsius) ./ diff(time_seconds);
        trend.avg_change_rate = mean(abs(temp_changes));
        trend.max_change_rate = max(abs(temp_changes));
    else
        trend.avg_change_rate = 0;
        trend.max_change_rate = 0;
    end
    
    % Oscillation detection
    if length(temp_celsius) > 5
        % Count zero crossings in detrended signal
        detrended = temp_celsius - polyval(p, time_seconds);
        zero_crossings = sum(diff(sign(detrended)) ~= 0);
        trend.oscillation_frequency = zero_crossings / (time_seconds(end) - time_seconds(1));
    else
        trend.oscillation_frequency = 0;
    end
end

function prediction = predict_normal_mode(temp_celsius, time_seconds, threshold_celsius, trend)
% Prediction for normal mode (steady behavior)
    prediction = struct();
    
    current_temp = trend.current_temp;
    
    % Simple linear extrapolation
    if abs(trend.short_slope) > 1e-6 % significant trend
        temp_diff = threshold_celsius - current_temp;
        time_to_threshold = temp_diff / trend.short_slope;
        
        if time_to_threshold > 0 && time_to_threshold < 300 % within 5 minutes
            prediction.will_alert = true;
            prediction.time_to_alert = time_to_threshold * 1000; % convert to ms
            prediction.confidence = calculate_confidence(trend, 'linear');
            
            if trend.short_slope > 0
                prediction.alert_type = 'rising';
            else
                prediction.alert_type = 'falling';
            end
        else
            prediction.will_alert = false;
            prediction.time_to_alert = -1;
            prediction.confidence = 0.5;
            prediction.alert_type = 'none';
        end
    else
        % No significant trend
        prediction.will_alert = false;
        prediction.time_to_alert = -1;
        prediction.confidence = 0.8;
        prediction.alert_type = 'stable';
    end
end

function prediction = predict_noisy_mode(temp_celsius, time_seconds, threshold_celsius, trend)
% Prediction for noisy mode (high variability)
    prediction = struct();
    
    current_temp = trend.current_temp;
    
    % Account for noise in prediction
    noise_margin = 2 * trend.std_dev; % 2-sigma margin
    
    % Check if we're close to threshold considering noise
    distance_to_threshold = abs(current_temp - threshold_celsius);
    
    if distance_to_threshold <= noise_margin
        prediction.will_alert = true;
        prediction.alert_type = 'oscillating';
        
        % Estimate time based on noise characteristics
        if trend.avg_change_rate > 0
            prediction.time_to_alert = (distance_to_threshold / trend.avg_change_rate) * 1000;
        else
            prediction.time_to_alert = 5000; % 5 seconds default for noisy mode
        end
        
        prediction.confidence = calculate_confidence(trend, 'noisy');
    else
        % Use trend analysis but with lower confidence
        base_prediction = predict_normal_mode(temp_celsius, time_seconds, threshold_celsius, trend);
        prediction.will_alert = base_prediction.will_alert;
        prediction.time_to_alert = base_prediction.time_to_alert;
        prediction.alert_type = base_prediction.alert_type;
        prediction.confidence = base_prediction.confidence * 0.6; % reduce confidence due to noise
    end
end

function prediction = predict_ramp_mode(temp_celsius, time_seconds, threshold_celsius, trend)
% Prediction for ramp mode (predictable linear changes)
    prediction = struct();
    
    current_temp = trend.current_temp;
    
    % Ramp mode should have consistent slope
    if abs(trend.slope) > 1e-6
        temp_diff = threshold_celsius - current_temp;
        time_to_threshold = temp_diff / trend.slope;
        
        % Check consistency between short-term and long-term trends
        slope_consistency = abs(trend.slope - trend.short_slope) / max(abs(trend.slope), 1e-6);
        
        if time_to_threshold > 0 && time_to_threshold < 600 % within 10 minutes
            prediction.will_alert = true;
            prediction.time_to_alert = time_to_threshold * 1000;
            prediction.confidence = calculate_confidence(trend, 'ramp') * (1 - slope_consistency);
            
            if trend.slope > 0
                prediction.alert_type = 'rising';
            else
                prediction.alert_type = 'falling';
            end
        else
            prediction.will_alert = false;
            prediction.time_to_alert = -1;
            prediction.confidence = 0.3;
            prediction.alert_type = 'none';
        end
    else
        prediction.will_alert = false;
        prediction.time_to_alert = -1;
        prediction.confidence = 0.9;
        prediction.alert_type = 'stable';
    end
end

function confidence = calculate_confidence(trend, mode_type)
% Calculate confidence based on trend consistency and mode
    base_confidence = 0.5;
    
    switch mode_type
        case 'linear'
            % Higher confidence for consistent trends
            if trend.std_dev < 0.1 % low noise
                base_confidence = 0.9;
            elseif trend.std_dev < 0.5
                base_confidence = 0.7;
            else
                base_confidence = 0.5;
            end
            
        case 'noisy'
            % Lower confidence due to noise
            base_confidence = 0.4;
            
        case 'ramp'
            % High confidence for ramp mode if trend is consistent
            slope_ratio = abs(trend.short_slope) / max(abs(trend.slope), 1e-6);
            if slope_ratio > 0.8 && slope_ratio < 1.2
                base_confidence = 0.95;
            else
                base_confidence = 0.6;
            end
    end
    
    confidence = max(0, min(1, base_confidence));
end

function recommendations = generate_recommendations(prediction, temp_celsius, threshold_celsius, mode)
% Generate actionable recommendations
    recommendations = {};
    
    if prediction.will_alert
        recommendations{end+1} = sprintf('Alert expected in %.1f seconds', prediction.time_to_alert/1000);
        
        if strcmp(prediction.alert_type, 'rising')
            recommendations{end+1} = 'Consider increasing threshold or implementing cooling measures';
        elseif strcmp(prediction.alert_type, 'falling')
            recommendations{end+1} = 'Consider decreasing threshold or implementing warming measures';
        elseif strcmp(prediction.alert_type, 'oscillating')
            recommendations{end+1} = 'Temperature oscillating near threshold - consider noise filtering';
        end
        
        if prediction.confidence < 0.5
            recommendations{end+1} = 'Low confidence prediction - increase monitoring frequency';
        end
    else
        recommendations{end+1} = 'No immediate alert expected';
        
        current_temp = temp_celsius(end);
        temp_margin = abs(current_temp - threshold_celsius);
        
        if temp_margin < 1.0 % within 1 degree
            recommendations{end+1} = 'Temperature close to threshold - monitor closely';
        end
    end
    
    % Mode-specific recommendations
    switch lower(mode)
        case 'noisy'
            recommendations{end+1} = 'Noisy mode active - consider smoothing filters';
        case 'ramp'
            recommendations{end+1} = 'Ramp mode active - linear prediction applicable';
    end
end

function prediction = create_default_prediction()
% Create default prediction for insufficient data
    prediction = struct();
    prediction.will_alert = false;
    prediction.time_to_alert = -1;
    prediction.confidence = 0.0;
    prediction.alert_type = 'unknown';
    prediction.recommendations = {'Insufficient data for prediction'};
end

function log_prediction_results(prediction, current_temp, threshold_celsius, mode)
% Log prediction results
    fprintf('Alert Prediction Results (Mode: %s):\n', mode);
    fprintf('  Current temperature: %.2f°C\n', current_temp);
    fprintf('  Threshold: %.2f°C\n', threshold_celsius);
    fprintf('  Will alert: %s\n', char(prediction.will_alert + "false"));
    
    if prediction.will_alert
        fprintf('  Time to alert: %.1f seconds\n', prediction.time_to_alert/1000);
        fprintf('  Alert type: %s\n', prediction.alert_type);
    end
    
    fprintf('  Confidence: %.1f%%\n', prediction.confidence * 100);
    
    if ~isempty(prediction.recommendations)
        fprintf('  Recommendations:\n');
        for i = 1:length(prediction.recommendations)
            fprintf('    - %s\n', prediction.recommendations{i});
        end
    end
end