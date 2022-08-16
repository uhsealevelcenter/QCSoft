import io
import os
import tempfile
import unittest

import numpy as np
import scipy.io as sio

import filtering as filt
from main import load_station_data, assemble_ts_text, save_ts_files, save_mat_high_fq

dirname = os.path.dirname(__file__)
input_filename = os.path.join(dirname, 'test_data/monp/ssaba1810.dat')
# The ground truth output file. Produced by an earlier, better tested software version (0.6)
# Todo: Ask Fee to produce a ts, hourly, and daily file for an arbitrary station (without cleaning it) and use that output file as the ground truth
output_filename = os.path.join(dirname, 'test_data/ts_file_truth/t1231810.dat')


class TestDatFileSave(unittest.TestCase):
    input_data = None
    data_truth = None

    def setUp(self) -> None:
        self.input_data = load_station_data([input_filename])
        self.data_truth = load_station_data([output_filename])

    def tearDown(self) -> None:
        # delete all temp files here
        pass

    def test_ts_file_assembly_and_save(self):
        # 1) Load the ground truth ts file (the one you get from Fee)
        # 2) Load the monp file for the same station and month
        # 3) Save the monp file to ts (without any cleaning)
        # TODO: 4) Compare the data for each sensor. This is not necessary anymore? Because I compare the strings
        # for the two files and they are completely equal. So this is essentially an end to end test (sort of)
        # 5) Compare that formatting is exactly the same, it's all strings after all

        text_data_input = assemble_ts_text(self.input_data)
        text_data_truth = assemble_ts_text(self.data_truth)
        self.assertEqual(text_data_input[0][1], text_data_truth[0][1])

        # test ts file save
        # Compare the saved file to the ground truth file
        with tempfile.TemporaryDirectory() as tmp:
            success, failure = save_ts_files(text_data_input, tmp)
            self.assertEqual(len(success), 1)
            self.assertEqual(success[0]['message'], 'Success \nt1231810.dat Saved to ' + tmp + '\n')
            self.assertEqual(success[0]['title'], 'Success')
            self.assertEqual(len(failure), 0)
            with io.open(tmp + '/' + 't1231810.dat') as tst_f:
                with io.open(output_filename) as ref_f:
                    self.assertListEqual(list(tst_f), list(ref_f))

        # Repeating all of the above but this time processing multiple months
        file1 = os.path.join(dirname, 'test_data/monp/ssaba1809.dat')
        file2 = os.path.join(dirname, 'test_data/monp/ssaba1810.dat')
        file3 = os.path.join(dirname, 'test_data/monp/ssaba1811.dat')

        truth_file1 = os.path.join(dirname, 'test_data/ts_file_truth/t1231809.dat')
        truth_file2 = os.path.join(dirname, 'test_data/ts_file_truth/t1231810.dat')
        truth_file3 = os.path.join(dirname, 'test_data/ts_file_truth/t1231811.dat')

        station_data = load_station_data([file1, file2, file3])
        # station_data_truth = load_station_data([truth_file1, truth_file2, truth_file3])

        data_as_text = assemble_ts_text(station_data)
        # data_as_text_truth = assemble_ts_text(station_data_truth)

        # Compare the saved file to the ground truth file
        with tempfile.TemporaryDirectory() as tmp:
            success, failure = save_ts_files(data_as_text, tmp)
            self.assertEqual(len(success), 3)
            self.assertEqual(success[0]['message'], 'Success \nt1231809.dat Saved to ' + tmp + '\n')
            self.assertEqual(success[1]['message'], 'Success \nt1231810.dat Saved to ' + tmp + '\n')
            self.assertEqual(success[2]['message'], 'Success \nt1231811.dat Saved to ' + tmp + '\n')
            self.assertEqual(success[0]['title'], 'Success')
            self.assertEqual(len(failure), 0)
            with io.open(tmp + '/' + 't1231809.dat') as tst_f1:
                with io.open(truth_file1) as ref_f:
                    self.assertListEqual(list(tst_f1), list(ref_f))
            with io.open(tmp + '/' + 't1231810.dat') as tst_f2:
                with io.open(truth_file2) as ref_f:
                    self.assertListEqual(list(tst_f2), list(ref_f))
            with io.open(tmp + '/' + 't1231811.dat') as tst_f3:
                with io.open(truth_file3) as ref_f:
                    self.assertListEqual(list(tst_f3), list(ref_f))

    def test_mat_hq_files(self):
        # Test saving data to high frequency .mat format
        station = self.input_data

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_mat_high_fq(station, tmp_dir, callback=None)
            for month in station.month_collection:
                # Compare every sensor (one file per sensor)
                for key, sensor in month.sensor_collection.items():
                    if key == "ALL":
                        continue
                    file_name = month.get_mat_filename()[key]
                    data = sio.loadmat(os.path.join(tmp_dir, file_name))
                    data_trans = data[file_name.split('.')[0]].transpose((1, 0))
                    time_vector_mat = data_trans[0]
                    time_vector = filt.datenum2(sensor.get_time_vector())

                    sea_level = sensor.get_flat_data().copy()
                    # Add the reference height back to .mat data
                    sea_level_mat = data_trans[1] + int(sensor.height)
                    # Replace back nan data with 9999s
                    nan_ind = np.argwhere(np.isnan(sea_level_mat))
                    sea_level_mat[nan_ind] = 9999
                    # Compare sea level data
                    self.assertListEqual(sea_level_mat.tolist(), sea_level.tolist())
                    # Compare time vector
                    self.assertListEqual(time_vector_mat.tolist(), time_vector)


if __name__ == '__main__':
    unittest.main()
