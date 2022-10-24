import io
import os
import tempfile
import unittest
from pathlib import Path

import settings as st

import numpy as np
import scipy.io as sio

from station_tools import filtering as filt
from station_tools.extractor2 import load_station_data
from my_widgets import find_outliers
from station_tools import utils

dirname = os.path.dirname(__file__)
input_filename = os.path.join(dirname, 'test_data/monp/ssaba1810.dat')
# The ground truth output file. Produced by an earlier, better tested software version (0.6)
# Todo: Ask Fee to produce a ts, hourly, and daily file for an arbitrary station (without cleaning it) and use that output file as the ground truth
output_filename = os.path.join(dirname, 'test_data/ts_file_truth/t1231810.dat')
HOURLY_PATH = os.path.join(dirname, 'test_data/hourly_truth/')
DAILY_PATH = os.path.join(dirname, 'test_data/daily_truth/')
SSABA1809 = os.path.join(dirname, 'test_data/monp/ssaba1809.dat')
DIN = os.path.join(dirname, 'test_data/din/tmp.din')


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

        text_data_input = self.input_data.assemble_ts_text()
        text_data_truth = self.input_data.assemble_ts_text()
        self.assertEqual(text_data_input[0][1], text_data_truth[0][1])

        # test ts file save
        # Compare the saved file to the ground truth file
        with tempfile.TemporaryDirectory() as tmp:
            success, failure = self.input_data.save_ts_files(text_data_input, tmp)
            self.assertEqual(len(success), 1)
            save_folder = "t123"
            save_path = utils.get_top_level_directory(parent_dir=tmp) / utils.HIGH_FREQUENCY_FOLDER / save_folder / str(
                2018)
            self.assertEqual(success[0]['message'], 'Success \nt1231810.dat Saved to ' + str(save_path) + '\n')
            self.assertEqual(success[0]['title'], 'Success')
            self.assertEqual(len(failure), 0)
            with io.open(Path(save_path / 't1231810.dat')) as tst_f:
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

        data_as_text = station_data.assemble_ts_text()
        # data_as_text_truth = assemble_ts_text(station_data_truth)

        # Compare the saved file to the ground truth file
        with tempfile.TemporaryDirectory() as tmp:
            save_folder = "t123"
            save_path = utils.get_top_level_directory(parent_dir=tmp) / utils.HIGH_FREQUENCY_FOLDER / save_folder / str(
                2018)
            success, failure = station_data.save_ts_files(data_as_text, tmp)
            self.assertEqual(len(success), 3)
            self.assertEqual(success[0]['message'], 'Success \nt1231809.dat Saved to ' + str(save_path) + '\n')
            self.assertEqual(success[1]['message'], 'Success \nt1231810.dat Saved to ' + str(save_path) + '\n')
            self.assertEqual(success[2]['message'], 'Success \nt1231811.dat Saved to ' + str(save_path) + '\n')
            self.assertEqual(success[0]['title'], 'Success')
            self.assertEqual(len(failure), 0)
            with io.open(Path(save_path / 't1231809.dat')) as tst_f1:
                with io.open(truth_file1) as ref_f:
                    self.assertListEqual(list(tst_f1), list(ref_f))
            with io.open(Path(save_path / 't1231810.dat')) as tst_f2:
                with io.open(truth_file2) as ref_f:
                    self.assertListEqual(list(tst_f2), list(ref_f))
            with io.open(Path(save_path / 't1231811.dat')) as tst_f3:
                with io.open(truth_file3) as ref_f:
                    self.assertListEqual(list(tst_f3), list(ref_f))

    def test_mat_hq_files(self):
        # Test saving data to high frequency .mat format
        station = self.input_data

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_folder = "t123"
            save_path = utils.get_top_level_directory(parent_dir=tmp_dir) / utils.HIGH_FREQUENCY_FOLDER / save_folder / str(
                2018)
            station.save_mat_high_fq(tmp_dir, callback=None)
            for month in station.month_collection:
                # Compare every sensor (one file per sensor)
                for key, sensor in month.sensor_collection.items():
                    if key == "ALL":
                        continue
                    file_name = month.get_mat_filename()[key]
                    data = sio.loadmat(os.path.join(save_path, file_name))
                    data_trans = data[file_name.split('.')[0]].transpose((1, 0))
                    time_vector_mat = data_trans[0]
                    time_vector = filt.datenum2(sensor.get_time_vector())

                    sea_level = sensor.get_flat_data().copy()
                    # Add the reference height back to .mat data
                    sea_level_mat = data_trans[1] + int(sensor.height)
                    # Make sure all 9999s are taken out from the final .mat file
                    self.assertNotIn(9999, sea_level_mat)
                    # Replace back nan data with 9999s
                    nan_ind = np.argwhere(np.isnan(sea_level_mat))
                    sea_level_mat[nan_ind] = 9999
                    # Compare sea level data
                    self.assertListEqual(sea_level_mat.tolist(), sea_level.tolist())
                    # Compare time vector
                    self.assertListEqual(time_vector_mat.tolist(), time_vector)

        # Now clean the data and then save it
        # Checks if cleaning is consistent between both .mat and ts files after cleaning
        # Does not really check if the cleaning is "correct" because there is really no perfect way to clean the data

        clean_station = load_station_data([input_filename])
        for month in clean_station.month_collection:
            # Clean every sensor
            for key, sensor in month.sensor_collection.items():
                if key == "ALL":
                    continue
                sea_level = sensor.get_flat_data().copy()
                if key != "PRD":
                    outliers_idx = find_outliers(clean_station, sensor.get_time_vector(), sea_level, key)
                    # Clean the data (change outliers to 9999)
                    clean_station.aggregate_months['data'][key][outliers_idx] = 9999

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_folder = "t123"
            save_path = utils.get_top_level_directory(parent_dir=tmp_dir) / utils.HIGH_FREQUENCY_FOLDER / save_folder / str(
                2018)
            clean_station.back_propagate_changes(clean_station.aggregate_months['data'])
            clean_station.save_mat_high_fq(tmp_dir, callback=None)
            for month in clean_station.month_collection:
                # Compare every sensor (one file per sensor)
                for key, sensor in month.sensor_collection.items():
                    if key == "ALL":
                        continue
                    file_name = month.get_mat_filename()[key]
                    data = sio.loadmat(os.path.join(save_path, file_name))
                    data_trans = data[file_name.split('.')[0]].transpose((1, 0))
                    time_vector_mat = data_trans[0]
                    time_vector = filt.datenum2(sensor.get_time_vector())

                    sea_level = sensor.get_flat_data().copy()
                    # Add the reference height back to .mat data
                    sea_level_mat = data_trans[1] + int(sensor.height)
                    # Make sure all 9999s are taken out from the final .mat file
                    self.assertNotIn(9999, sea_level_mat)
                    # Replace back nan data with 9999s
                    nan_ind = np.argwhere(np.isnan(sea_level_mat))
                    sea_level_mat[nan_ind] = 9999
                    # Compare sea level data
                    self.assertListEqual(sea_level_mat.tolist(), sea_level.tolist())
                    # Compare time vector
                    self.assertListEqual(time_vector_mat.tolist(), time_vector)
        # simple check to make sure the data got cleaned
        # Note that this is a really primitive step and checks this for only one month and for only one sensor
        clean_prs_sum = np.sum(clean_station.month_collection[0].sensor_collection['PRS'].get_flat_data())
        not_clean_prs_sum = np.sum(station.month_collection[0].sensor_collection['PRS'].get_flat_data())
        self.assertNotEqual(clean_prs_sum, not_clean_prs_sum)
        # Also leave sums so that if we ever make changes to the current outlier algorithm this test will fail
        self.assertEqual(clean_prs_sum, 48519306)
        self.assertEqual(not_clean_prs_sum, 48326678)

    def test_save_fast_delivery(self):
        """
        Loads a truth hourly matlab file for th1231809.mat produced by matlab
        and produces python version of the same file and compares the results
        """

        data_truth = sio.loadmat(os.path.join(HOURLY_PATH, 'th1231809.mat'))
        data_truth_trans = data_truth['rad'].transpose((1, 0))
        # time_vector_truth = data_truth_trans[0]
        sea_level_truth = data_truth_trans['sealevel'][0][0]
        # Need to remove NaNs because Nan is not equal Nan
        nan_ind = np.argwhere(np.isnan(sea_level_truth))
        sea_level_truth[nan_ind] = 9999
        sea_level_truth = np.concatenate(sea_level_truth, axis=0)

        station = load_station_data([SSABA1809])

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_folder = "t123"
            save_path = utils.get_top_level_directory(parent_dir=tmp_dir) / utils.FAST_DELIVERY_FOLDER / save_folder / str(
                2018)
            station.save_fast_delivery(path=tmp_dir, din_path=DIN, callback=None)
            # .mat files test
            # Hourly test
            data = sio.loadmat(os.path.join(save_path, 'th1231809.mat'))
            data_trans = data['rad'].transpose((1, 0))
            sea_level = data_trans['sealevel'][0][0]
            sea_level = np.concatenate(sea_level, axis=0)
            # Make sure all 9999s are taken out from the final .mat file
            self.assertNotIn(9999, sea_level)
            nan_ind = np.argwhere(np.isnan(sea_level))
            sea_level[nan_ind] = 9999

            # Check the difference to 6 decimal places (because the data was run in matlab and python we allow
            # for tiny differences

            # self.assertListEqual(sea_level_truth.round(decimals=6).tolist(), sea_level.round(6).tolist())
            np.testing.assert_almost_equal(sea_level_truth, sea_level, 6)

            # daily test
            data_truth = sio.loadmat(os.path.join(DAILY_PATH, 'da1231809.mat'))
            sea_level_truth = np.concatenate(data_truth['data_day']['sealevel'][0][0], axis=0)
            data = sio.loadmat(os.path.join(save_path, 'da1231809.mat'))
            sea_level = data['sealevel'][0]
            # Make sure all 9999s are taken out from the final .mat file
            self.assertNotIn(9999, sea_level)
            # Daily data involves calculation of tidal residuals and the calculation between matlab and python is
            # slightly different so we don't need the results to be exactly the same but witin 1 millimmiter
            np.testing.assert_almost_equal(sea_level_truth, sea_level, 6)


if __name__ == '__main__':
    unittest.main()
