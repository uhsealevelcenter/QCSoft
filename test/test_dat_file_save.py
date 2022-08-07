import os
import unittest

from main import load_station_data, assemble_ts_text

dirname = os.path.dirname(__file__)
input_filename = os.path.join(dirname, 'test_data/monp/ssaba1810.dat')
tmp_dir = os.path.join(dirname, 'test_data/ts_file_tmp')
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
        pass

    def test_ts_file_assembly(self):
        # 1) Load the ground truth ts file (the one you get from Fee)
        # 2) Load the monp file for the same station and month
        # 3) Save the monp file to ts (without any cleaning)
        # TODO: 4) Compare the data for each sensor. This is not necessary anymore? Because I compare the strings
        # for the two files and they are completely equal. So this is essentially an end to end test (sort of)
        # 5) Somehow also compare that formatting is exactly the same, it's all strings after all
        
        # 6) Do similar steps for daily, and hourly

        text_data_input = assemble_ts_text(self.input_data)
        text_data_truth = assemble_ts_text(self.data_truth)
        self.assertEqual(text_data_input[0][1], text_data_truth[0][1])


if __name__ == '__main__':
    unittest.main()
