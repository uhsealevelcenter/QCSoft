import datetime
import os
import unittest

import PyQt5
import matplotlib.pyplot as plt

from interactive_plot import PointBrowser
from main import load_station_data, find_outliers

dirname = os.path.dirname(__file__)
file1 = os.path.join(dirname, 'test_data/monp/ssaba1811.dat')
file2 = os.path.join(dirname, 'test_data/monp/ssaba1812.dat')
file3 = os.path.join(dirname, 'test_data/monp/ssaba1901.dat')


class TestInteractiveBrowser(unittest.TestCase):
    def setUp(self) -> None:
        self.station = load_station_data([file1])
        self.station_multi = load_station_data([file1, file2, file3]) # multi months loaded

    def test_inconsistent_sampling_rate(self):
        self.assertTrue(self.station_multi.is_sampling_inconsistent())
        self.assertFalse(self.station.is_sampling_inconsistent())

    def test_reference_level_change(self):
        date = PyQt5.QtCore.QDate(2015, 7, 22)

        self.assertEqual(self.station.month_collection[0].sensor_collection['PRS'].height, 783)
        # Change reference height
        months_updated, ref_diff, new_header = self.station.update_header_reference_level(date, 5555, 'PRS')

        self.assertEqual(months_updated, 1)
        self.assertEqual(ref_diff, 4772)
        self.assertEqual(new_header,'123sabPRS    PLAT=05 53.3N LONG=095 18.9E TMZONE=GMT    REF=5555  2 NOV 18  030 \n')
        self.assertEqual(self.station.month_collection[0].sensor_collection['PRS'].height, 5555)

    def test_something(self):
        data_prs = self.station.month_collection[0].sensor_collection['PRS'].get_flat_data()
        time_prs = self.station.month_collection[0].sensor_collection['PRS'].get_time_vector()
        outliers = find_outliers(self.station, time_prs, data_prs, 'PRS')

        fig, ax = plt.subplots()
        # ax.plot(time_prs, data_prs, "k")
        line, = ax.plot(time_prs, data_prs, '-', picker=5, lw=0.5, markersize=3)

        browser = PointBrowser(time_prs, data_prs, ax, line, fig,
                               outliers)

        # Todo:
        #  1) Refactor show_ref_dialog so that time formatting is its own function and write a test for it
        #  2) Crate a function that calculates new reference point based on the newly supplied one
        #  3) Write a function that constructs a new header (this and the one above could method of the Sensor object)
        #  4) Write test for all of those function above
        #  5) Offset the value using some arbitrary new offset at a certain date and write a test for it
        #  6) See Todo in show_ref_dialog on how to better handle multiple month reference level change and implement it
        #  7)  Write a test for the above implementation


if __name__ == '__main__':
    unittest.main()
