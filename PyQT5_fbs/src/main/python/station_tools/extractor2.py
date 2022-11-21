import re

import numpy as np

from station_tools.sensor import SensorCollection, Sensor, Month, Station


class DataExtractor(Month):
    """
    Takes a path to the monp dat file
    """

    def __init__(self, filename):
        """

        :type filename: a path to a data file e.g. t1091803.dat. sgana1801.dat
        """
        self.in_file = open(filename, 'r')  # t1091803.dat. sgana1801.dat
        self.headers = []
        self.frequencies = []
        self.refs = []
        self.sensor_ids = []
        self.init_dates = []
        self.data_all = {}
        self.infos_time_col = {}
        self.prev_date = 0
        self.units = []
        self.loc = [0, 0]
        self.string_location = None

        self.sensors = SensorCollection()
        self.parse_file(filename)

        self.month_int = int(filename.split('.dat')[0][-2:])
        self.year = int("20"+filename.split('.dat')[0][-4:-2])
        Month.__init__(self, self.month_int, self.year, self.sensors, self.headers[0][:3])

    def is_header(self, arg):
        """
        Check if the line scanned is a header
        The checker is looking for word "LONG" in that line of text
        According to Fee, every header of every station has LONG in it
        """
        # if (line[0][0].isdigit() and not '99999' in line):
        return bool('LONG' in arg)

    def split_by_n(self, n, num):
        return [num[i:i + n] for i in range(0, len(num), n)]

    def missing_dates(self, L):
        start, end = L[0], L[-1]
        return sorted(set(range(start, end + 1)).difference(L))

    def extract_lat(self, header):
        NorS = header[25]  # Extract a character to see if it is North or South
        lat_deg = header[18:20]
        lat_min = header[21:23]
        lat_dec_deg = int(lat_deg) + int(lat_min) / 60

        return -lat_dec_deg if NorS == "S" else lat_dec_deg

    def extract_long(self, header):
        WorE = header[40]  # West or East (W or E)
        long_deg = header[32:35]
        long_min = header[36:38]
        long_dec_deg = int(long_deg) + int(long_min) / 60

        return -long_dec_deg if WorE == "W" else long_dec_deg

    def extract_string_location(self, header):
        return header[14:41]

    def parse_file(self, filename):
        list_of_lists = []
        a_list = []
        counter = 0

        for line in self.in_file:
            a_list.append(line)
            if line.startswith('99999'):  # should probably use 80*"9"
                # print "Channel End, append a new channel"
                a_list.remove(a_list[-1])
                list_of_lists.append((counter, list(a_list)))
                a_list = []
                counter += 1

            if self.is_header(line):
                self.headers.append(line)
                self.frequencies.append(line.split()[-4])
                self.refs.append(re.search('REF=([^ ]+) .*', line).group(1))

        for header in self.headers:
            # safeguarding against the case a station number ever becomes a 4 digit
            # search for digits in the first element of the header and put the together
            station_num = ''.join(map(str, [int(s) for s in header.split()[0][0:4] if s.isdigit()]))
            self.sensor_ids.append(station_num + header[6:9])

        self.loc = [self.extract_lat(self.headers[0]), self.extract_long(self.headers[0])]
        self.string_location = self.extract_string_location(self.headers[0])

        # because file ends with two lines of 9s there is an empty list that needs to be
        # deleted
        del list_of_lists[-1]

        for sensor in range(len(self.sensor_ids)):
            data = []  # only sea level measurements (no time)
            info_time_col = []

            if float(self.frequencies[sensor]) >= 5.0:
                lines_per_day = int(1440 / 12 / int((self.frequencies[sensor])))
            else:
                lines_per_day = int(1440 / 15 / int((self.frequencies[sensor])))

            pre_text = list_of_lists[sensor][1][1:][0][0:15]

            # 1) Figure out the missing date
            m_length = int(list_of_lists[sensor][1][0:][0][77:79])

            # print(m_length)

            month_ar = [0]  # need to initiate with 0 because we need to check if the first
            # day in a month is missing

            # go through every line of data
            for l in range(len(list_of_lists[sensor][1][1:])):
                # find first row of each month to get all dates in the file
                if l % lines_per_day == 0:
                    month_ar.append(int(list_of_lists[sensor][1][1:][l][15:17]))
            # add upper month range + 1 to check if there are any consecutive days
            # including the last date missing
            if month_ar[-1] != m_length:
                month_ar.append(m_length + 1)
            # Copy the list with all the data so that we can modify it
            lines_copy = list_of_lists[sensor][1][1:]
            # Check for missing date and reset the comparison array to default [0]
            missed_dates_ar = self.missing_dates(month_ar)
            if missed_dates_ar:
                print("Missing dates", missed_dates_ar)

            # There might be multiple days missing so need to loop through all of them
            for day in missed_dates_ar:
                missing_date = day
                missing_date_str = '{:>2}'.format(str(missing_date))

                # Create and format an array of lines with dates and missing data
                bad_data_ar = []
                # 2) Add lines_per_day lines with 9999 values and increase the line counter
                for l in range(lines_per_day):
                    if float(self.frequencies[sensor]) >= 5.0:
                        # print(pre_text+str(missing_date_str)+" "+'{:>2}'.format(str(l))+" 9999"*12)
                        bad_data_ar.append(
                            pre_text + str(missing_date_str) + " " + '{:>2}'.format(str(l)) + " 9999" * 12 + "\n")
                    else:
                        # print(pre_text+str(missing_date_str)+" "+'{:>2}'.format(str(l))+"9999"*15)
                        bad_data_ar.append(
                            pre_text + str(missing_date_str) + " " + '{:>2}'.format(str(l)) + "9999" * 15 + "\n")
                # 3) prepend the above print statement to the list_of_lists[sensor][1][1:]
                # insert the missing date with missing data
                for b in range(len(bad_data_ar)):
                    lines_copy.insert((missing_date - 1) * lines_per_day + b, bad_data_ar[b])

            init_date_lst = lines_copy[0][8:17].split()
            if len(init_date_lst) > 2:
                year = init_date_lst[0]
                month = init_date_lst[1]
                day = init_date_lst[2]
            else:
                month = init_date_lst[0][-2:]
                year = init_date_lst[0][:-2]
                day = init_date_lst[1]
                init_date_lst[1] = init_date_lst[0][4:]

            if len(day) == 1:
                day = "0" + day
            if len(month) == 1:
                month = "0" + month
            if len(year) == 2:
                year = "20" + year
            if len(year) == 1:
                year = "200" + year
            #

            init_date = np.datetime64("-".join([year, month, day]) + 'T00:00:00.000000')
            self.init_dates.append(init_date)

            for line in lines_copy:
                # Read each row of data into a list of floats
                # and also save the non-sensor data part (0:21) for the output file
                info_time_col.append(line[:20])
                if float(self.frequencies[sensor]) >= 5.0:
                    fields = self.split_by_n(5, line[20:].rstrip('\n'))  # for 5 digit data format
                else:
                    fields = self.split_by_n(4, line[20:].rstrip('\n'))  # for 4 digit data format
                for s in fields:
                    if s == '****' or s == ' ****' or s == '*****':
                        fields[fields.index(s)] = '9999'
                row_data = [float(x) for x in fields]

                # And add this row to the
                # entire data set.
                data.append(row_data)

            # Data prior to Spet 2015 was stored in Imperial units.
            if init_date < np.datetime64('2015-09-01'):
                self.units.append('Imperial')
            else:
                self.units.append('Metric')

            # # Finally, convert the "list of
            # # lists" into a 2D array.
            # self.infos_time_col.append(info_time_col)
            self.infos_time_col[self.sensor_ids[sensor][-3:]] = info_time_col
            # self.data_all.append(np.array(data))
            self.data_all[self.sensor_ids[sensor][-3:]] = np.array(data)
            sensor_type = self.sensor_ids[sensor][-3:]
            frequency = self.frequencies[sensor]
            ref_height = self.refs[sensor]
            header = self.headers[sensor]

            _sensor = Sensor(rate=frequency, height=int(ref_height), sensor_type=sensor_type,
                             date=self.init_dates[sensor],
                             data=np.array(data), time_info=info_time_col, header=header)
            self.sensors.add_sensor(_sensor)
        self.in_file.close()


def load_station_data(file_names):
    """

    :param file_names: An array of data files to be loaded
    :return: Station instance with all the data needed for further processing
    """

    # Create DataExtractor for each month that was loaded into program
    months = []
    for file_name in file_names:
        month = DataExtractor(file_name)
        # An empty sensor, used to create "ALL" radio button in the GUI
        all_sensor = Sensor(None, None, 'ALL', None, None, None, None)
        month.sensors.add_sensor(all_sensor)
        # month = Month(month=month_int, sensors=month.sensors)
        months.append(month)

    # # The reason months[0] is used is because the program only allows to load
    # # multiple months for the same station, so the station sensors should be the same
    # # But what if a sensor is ever added to a station??? Check with fee it this ever happens
    name = months[0].headers[0][3:6]
    location = months[0].loc

    station = Station(name=name, location=location, month=months)
    return station
