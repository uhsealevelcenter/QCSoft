import os
import numpy as np
import unittest

from PyQt5.QtCore import QDate as QDate
import matplotlib.pyplot as plt

from interactive_plot import PointBrowser
from station_tools.utils import find_outliers
from station_tools.extractor2 import load_station_data

dirname = os.path.dirname(__file__)
file1 = os.path.join(dirname, 'test_data/monp/ssaba1811.dat')
file2 = os.path.join(dirname, 'test_data/monp/ssaba1812.dat')
file3 = os.path.join(dirname, 'test_data/monp/ssaba1901.dat')


class TestInteractiveBrowser(unittest.TestCase):
    def setUp(self) -> None:
        self.station = load_station_data([file1])
        self.station_multi = load_station_data([file1, file2, file3])  # multi months loaded

    def test_inconsistent_sampling_rate(self):
        self.assertTrue(self.station_multi.is_sampling_inconsistent())
        self.assertFalse(self.station.is_sampling_inconsistent())

    def test_reference_level_change(self):
        qt_date = QDate(2015, 7, 22)

        self.assertEqual(self.station.month_collection[0].sensor_collection['PRS'].height, 783)
        # Change reference height
        months_updated, ref_diff, new_header = self.station.update_header_reference_level(qt_date, 5555, 'PRS')

        self.assertEqual(months_updated, 1)
        self.assertEqual(ref_diff, 4772)
        self.assertEqual(new_header,
                         '123sabPRS    PLAT=05 53.3N LONG=095 18.9E TMZONE=GMT    REF=5555  2 NOV 18  030 \n')
        self.assertEqual(self.station.month_collection[0].sensor_collection['PRS'].height, 5555)

    # @unittest.skipIf("CIRCLE_BUILD_NUM" in os.environ, "Matplotlib is tripping up")
    def test_plot_value_edit(self):
        data_prs = self.station.month_collection[0].sensor_collection['PRS'].get_flat_data()
        time_prs = self.station.month_collection[0].sensor_collection['PRS'].get_time_vector()
        rate_prs = self.station.month_collection[0].sensor_collection['PRS'].rate
        outliers = self.station.aggregate_months['outliers']

        fig, ax = plt.subplots()
        # ax.plot(time_prs, data_prs, "k")
        line, = ax.plot(time_prs, data_prs, '-', picker=5, lw=0.5, markersize=3)

        browser = PointBrowser(time_prs, data_prs, ax, line, fig,
                               (outliers['PRS'],))

        # These are just dumb assertion to make sure that the outliers are being detected
        # and that the data is modified and also that offset works
        self.assertEqual(len(browser.deleted), 0)
        self.assertEqual(np.sum(browser.data), 139694623)
        for idx in outliers['PRS']:
            browser.ondelete(idx)
            browser.ys[idx] = 9999
        # 265 is the true for the current testing file and the current outliers methodology
        self.assertEqual(len(browser.deleted), 265)
        self.assertEqual(np.sum(browser.data), 141643093)

        date_time = '2018-11-20T20:58'
        browser.offset_data(date_time, 1500)
        self.assertEqual(np.sum(browser.data), 155278093)

        # multi month outlier detection
        outliers_m = self.station_multi.aggregate_months['outliers']
        # Check if all there
        self.assertEqual(len(outliers_m['PRS']), 303)
        self.assertEqual(len(outliers_m['PRD']), 0)
        self.assertEqual(len(outliers_m['ENC']), 87)
        self.assertEqual(len(outliers_m['RAD']), 183)
        # Check if sorted and properly indexed
        self.assertEqual(outliers_m['ENC'][0], 1060)
        self.assertEqual(outliers_m['ENC'][-1], 21496)
        self.assertEqual(outliers_m['PRS'][0], 3087)
        self.assertEqual(outliers_m['PRS'][-1], 79996)

        multi_browser = PointBrowser(self.station_multi.aggregate_months['time']['ENC'], self.station_multi.aggregate_months['data']['ENC'], ax, line, fig,
                               (outliers_m['ENC'],))

        # Check if the outliers are being deleted
        # for i, idx in enumerate(outliers_m['ENC']):
        #     outl_ind = multi_browser.next_pointer(self.station_multi.aggregate_months['data']['ENC'], outliers_m['ENC'], i,
        #                                     +1)
            # browser.ondelete(idx)
        # Todo:
        #  6) See Todo in show_ref_dialog on how to better handle multiple month reference level change and implement it
        #  7)  Write a test for the above implementation


if __name__ == '__main__':
    unittest.main()
