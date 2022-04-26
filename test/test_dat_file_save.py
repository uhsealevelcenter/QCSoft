import os
import unittest

import numpy as np

from extractor2 import DataExtractor
from sensor import Station, Sensor

dirname = os.path.dirname(__file__)
input_filename = os.path.join(dirname, 'test_data/ssaba1810.dat')
tmp_dir = os.path.join(dirname, 'test_data/ts_file_tmp')
# The ground truth output file. Produced by an earlier, better tested software version (0.6)
# Todo: Ask Fee to produce a ts, hourly, and daily file for an arbitrary station (without cleaning it) and use that output file as the ground truth
output_filename = os.path.join(dirname, 'test_data/ts_file_truth/t1231810.dat')


class TestDatFileSave(unittest.TestCase):
    input_data = {}
    output_data = {}

    def setUp(self) -> None:
        self.input_data = self.load_data(input_filename)
        self.output_data = self.load_data(output_filename)

    def tearDown(self) -> None:
        pass

    def test_ts_file_save(self):
        # Todo:
        # 1) Load the ground truth ts file (the one you get from Fee)
        # 2) Load the monp file for the same station and month
        # 3) Save the monp file to ts (without any cleaning)
        # 4) Compare the data for each sensor
        # 5) Somehow also compare that formatting is exactly the same, it's all strings after all
        # 6) Do similar steps for daily, and hourly

        # Check if PRS data is equal upon saving
        prs_data_in = self.input_data['PRS'].get_flat_data()
        prs_data_out = self.output_data['PRS'].get_flat_data()
        prs_data_is_equal = np.allclose(prs_data_in, prs_data_out)
        self.assertTrue(prs_data_is_equal)

    def load_data(self, path):
        data = {}
        de = DataExtractor(path)
        station_name = de.headers[0][:6]
        my_station = Station(station_name, de.loc)

        comb_data = np.ndarray(
            0)  # ndarray of concatonated data for all the months that were loaded for a particular station
        comb_time_col = []  # combined rows of all time columns for all the months that were loaded for a
        # particular station
        line_count = []  # array for the number of lines (excluding headers and 9999s)for each month that were
        # loaded for a particular station. Added as an attribute to respective sensor objects
        comb_headers = []

        for i, sensor in enumerate(de.sensor_ids):
            comb_data = de.data_all[sensor[-3:]]
            comb_time_col = comb_time_col + de.infos_time_col[sensor[-3:]]
            line_count = len(de.infos_time_col[sensor[-3:]])
            comb_headers = de.headers[i]
            data[sensor[-3:]] = Sensor(my_station, de.frequencies[i],
                                       de.refs[i], de.sensor_ids[i],
                                       de.init_dates[i], comb_data,
                                       comb_time_col, comb_headers)
            data[sensor[-3:]].line_num = []
            data[sensor[-3:]].line_num.append(line_count)
        return data


if __name__ == '__main__':
    unittest.main()
