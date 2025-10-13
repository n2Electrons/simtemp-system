function result = hello_driver(device_path, sysfs_path)
% HELLO_DRIVER Minimal communication test with simtemp driver
%
% Inputs:
%   device_path - Path to simtemp device (default: '/dev/simtemp')
%   sysfs_path  - Path to simtemp sysfs directory (default: '/sys/class/misc/simtemp')
%
% Outputs:
%   result.device_ok - Boolean: device accessible
%   result.sysfs_ok  - Boolean: sysfs accessible

    if nargin < 1 || isempty(device_path)
        device_path = '/dev/simtemp';
    end
    
    if nargin < 2 || isempty(sysfs_path)
        sysfs_path = '/sys/class/misc/simtemp';
    end
    
    result = struct();
    
    fprintf('Hello simtemp driver\n');
    
    % Check device
    [status, ~] = system(sprintf('test -c %s', device_path));
    result.device_ok = (status == 0);
    fprintf('Device %s: %s\n', device_path, result.device_ok ? 'OK' : 'FAIL');
    
    % Check sysfs
    [status, ~] = system(sprintf('test -d %s', sysfs_path));
    result.sysfs_ok = (status == 0);
    fprintf('Sysfs %s: %s\n', sysfs_path, result.sysfs_ok ? 'OK' : 'FAIL');
    
    % Overall status
    if result.device_ok && result.sysfs_ok
        fprintf('Driver communication: WORKING\n');
    else
        fprintf('Driver communication: FAILED\n');
    end
end

