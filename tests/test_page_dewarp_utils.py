import unittest
import numpy as np
import sys
import os

# Add the parent directory to sys.path to allow importing page_dewarp
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from page_dewarp import round_nearest_multiple, pix2norm, norm2pix # Assuming these functions exist

class TestPageDewarpUtils(unittest.TestCase):

    def test_round_nearest_multiple(self):
        self.assertEqual(round_nearest_multiple(0, 16), 0)
        self.assertEqual(round_nearest_multiple(10, 16), 16)
        self.assertEqual(round_nearest_multiple(16, 16), 16)
        self.assertEqual(round_nearest_multiple(17, 16), 32)
        self.assertEqual(round_nearest_multiple(31, 16), 32)
        self.assertEqual(round_nearest_multiple(32, 16), 32)
        self.assertEqual(round_nearest_multiple(10, 1), 10)
        self.assertEqual(round_nearest_multiple(10.0, 16), 16) # Test with float input
        self.assertEqual(round_nearest_multiple(10.5, 16), 16) # Test with float input

    def test_pix2norm_and_norm2pix(self):
        shape = (480, 640) # height, width

        # Test case 1: Center point
        pts_pix1 = np.array([[[320, 240]]], dtype=np.float32) # center of 640x480
        pts_norm1 = pix2norm(shape, pts_pix1)
        self.assertTrue(np.allclose(pts_norm1, np.array([[[0, 0]]]), atol=1e-6), msg=f"pix2norm center: {pts_norm1}")
        pts_pix1_reverted = norm2pix(shape, pts_norm1, as_integer=False)
        self.assertTrue(np.allclose(pts_pix1_reverted, pts_pix1, atol=1e-6), msg=f"norm2pix center: {pts_pix1_reverted}")

        # Test case 2: Top-left corner
        pts_pix2 = np.array([[[0, 0]]], dtype=np.float32)
        # Expected norm: (0 - 320)*(2/640) = -1, (0 - 240)*(2/640) = -0.75
        # Max dim is 640. scl = 2.0/640
        # offset = [320, 240]
        # (pts - offset) * scl
        # ([0,0] - [320,240]) * (2/640) = [-320, -240] * (1/320) = [-1, -240/320] = [-1, -0.75]
        expected_norm2 = np.array([[[-1.0, -0.75]]])
        pts_norm2 = pix2norm(shape, pts_pix2)
        self.assertTrue(np.allclose(pts_norm2, expected_norm2, atol=1e-6), msg=f"pix2norm top-left: {pts_norm2}")
        pts_pix2_reverted = norm2pix(shape, pts_norm2, as_integer=False)
        self.assertTrue(np.allclose(pts_pix2_reverted, pts_pix2, atol=1e-6), msg=f"norm2pix top-left: {pts_pix2_reverted}")

        # Test case 3: Bottom-right corner
        pts_pix3 = np.array([[[640, 480]]], dtype=np.float32) # width, height
        # ([640,480] - [320,240]) * (1/320) = [320, 240] * (1/320) = [1, 0.75]
        expected_norm3 = np.array([[[1.0, 0.75]]])
        pts_norm3 = pix2norm(shape, pts_pix3)
        self.assertTrue(np.allclose(pts_norm3, expected_norm3, atol=1e-6), msg=f"pix2norm bottom-right: {pts_norm3}")
        pts_pix3_reverted = norm2pix(shape, pts_norm3, as_integer=False)
        self.assertTrue(np.allclose(pts_pix3_reverted, pts_pix3, atol=1e-6), msg=f"norm2pix bottom-right: {pts_pix3_reverted}")

        # Test with as_integer = True for norm2pix
        pts_pix3_reverted_int = norm2pix(shape, pts_norm3, as_integer=True)
        self.assertTrue(np.allclose(pts_pix3_reverted_int, np.array([[[640, 480]]])), msg=f"norm2pix bottom-right int: {pts_pix3_reverted_int}")


    # Add more tests here if other utility functions are identified

if __name__ == '__main__':
    unittest.main()
