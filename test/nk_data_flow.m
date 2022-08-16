% This is a matlab script for comparing python produced data with the data produced in matlab
clear all
clc

% High frequency data for one station (one file per sensor) has to be all in the same folder in order to load it
data = upload_data();
% Process high frequency to hourly
datahr = hr_process_2(data, 2018, 2019);
% data.var just lists all the channels
% these should be somehow sorted in order of importance
% channel_params  = {'rad','prs',0};
% I am setting channel params manually to match the primary channel used for this particular data set in python
% So we are not actualy merging any channels, only using the primary one:
ch_par = {'rad',0};
% Load the hourly file produced by python to compare with the one produced by matlab
py_data_mr = load('my_data\hourly\th1231804.mat');
% Load the matlab version. The sealevel should be the same
rad = channel_merge(datahr, ch_par{:});
return
py_param = py_data_mr.ch_priority;
channel_params = {};
for i = 1:numel(py_param)
   fieldname = fieldnames(py_param{i});
   fieldname = fieldname{1};
   channel_params{end+1} = fieldname;
   fieldvalue = py_param{i}.(fieldname);
   if(i>1)
   channel_params{end+1} = fieldvalue;
   end
%    fieldvalue = getfield(py_param{i}, fieldname)
end

% channel_params  = {'rad'};
% channel_params = {py_data_mr.ch_priority};
% % data_mr= channel_merge(datahr, datahr.var);

% data_day = day_119filt(data_mr);
% 
% py_daily = load('py_daily.mat');

mean_hr_Python = nanmean(py_data_mr.sealevel)
mean_hr_Matlab = nanmean(data_mr.sealevel)

% mean_daily_Python = nanmean(py_daily.sealevel)
% mean_daily_Matlab = nanmean(data_day.sealevel)


return
% research quality data
d = dir(['\\ilikai.soest.hawaii.edu\KAIMOKU\AnnualReview\UHSLC_Processing_2018\UHSLC_Data_for_Pat\2018\Processed_RQD\h' data_mr.station '*.mat']);
rq = load(d.name);
t = datetime(datevec(rq.data_hr.time), 'InputFormat', 'yyyy-MMM-dd HH:mm:ss');
t1 = datetime(datevec(data_mr.time), 'InputFormat', 'yyyy-MMM-dd HH:mm:ss');

py_hr_t = datetime(datevec(py_data_mr.time), 'InputFormat', 'yyyy-MMM-dd HH:mm:ss');
mat_hr_t = datetime(datevec(data_mr.time), 'InputFormat', 'yyyy-MMM-dd HH:mm:ss');

figure
plot(t, rq.data_hr.sealevel)

% Find lower and upper date bounds based on the time vector
% produced by the python code because this vector is shorter
tlower = datetime(datevec(py_data_mr.time(1)));
tupper = datetime(datevec(py_data_mr.time(end)));
t_range = isbetween(t, tlower, tupper);

t_range1 = isbetween(t1, tlower, tupper);

t_new = t(t_range);
rq_hr = rq.data_hr.sealevel(t_range);

t_new1 = t1(t_range1);
ar_hr = data_mr.sealevel(t_range1);

figure
subplot(211)
hold on
plot(t_new, rq_hr,'b-*')
plot(t_new1, ar_hr,'r-d')

plot(t_new, py_data_mr.sealevel,'g-.')
hold off
legend('RQ', 'Ann Rev', 'Python')
title('Hourly')

subplot(212)
hold on
plot(t_new, rq_hr-py_data_mr.sealevel','b-')
% plot(t_new, ar_hr-py_data_mr.sealevel','r--')

hold off

title('Residual')
legend('RQ Mat - RQ Py', 'AR Mat - RQ Py')

figure
channel_vec = double(py_data_mr.channel);
channel_vec(channel_vec==-1) = NaN;
ychannels = ['enc';'enb';'adr';'sdr';'prs';'rad';'ra2';'ecs';'ec2';'bub';'en0';...
    'pwi';'pwl';'bwl';'pr2';'ana';'prb'];
tmp = unique(channel_vec);
[idx1,idx2] = find(~isnan(tmp));
chan = tmp(idx1);

plot(py_data_mr.time,channel_vec,'*')
ylabel('Channel','FontSize',14,'FontName','Helvetica')
xlim([py_data_mr.time(1) py_data_mr.time(end)])
% ylim([min(chan) max(chan)+1])
set(gca,'YTick',[0:16])
set(gca,'YTickLabel',ychannels)
datetick('x','ddmmmyy','keepticks','keeplimits')
% set(gca,'FontSize',14,'FontName','Helvetica')


