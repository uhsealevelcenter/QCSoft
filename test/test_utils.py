import unittest

from station_tools import utils
from station_tools.utils import get_missing_months

class TestUtils(unittest.TestCase):
    def test_consecutive(self):
        sensor_months = {'bub': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], 'prd': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                         'prs': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], 'rad': [1, 2, 3, 6, 7, 8, 9, 11, 12]}
        missing_bub = get_missing_months(sensor_months['bub'])
        missing_prd = get_missing_months(sensor_months['prd'])
        missing_prs = get_missing_months(sensor_months['prs'])
        missing_rad = get_missing_months(sensor_months['rad'])
        self.assertEqual(missing_bub, [])
        self.assertEqual(missing_prd, [1])
        self.assertEqual(missing_prs, [12])
        self.assertEqual(missing_rad, [4, 5, 10])

    def test_data_loading_validation(self):
        files1 = ['t1231811.dat', 't1231812.dat']
        files2 = ['t1231812.dat', 't1231901.dat']
        files3 = ['t1231904.dat', 't1231906.dat']

        self.assertTrue(utils.is_valid_files(files1))
        self.assertFalse(utils.is_valid_files(files2))
        self.assertFalse(utils.is_valid_files(files3))


if __name__ == '__main__':
    unittest.main()
