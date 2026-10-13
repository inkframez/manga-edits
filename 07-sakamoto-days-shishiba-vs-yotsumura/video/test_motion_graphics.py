"""Acceptance checks for the reference-informed motion graphics version."""
import importlib.util
import unittest
import numpy as np


class MotionGraphicsTests(unittest.TestCase):
    def test_shared_timing_and_true_anticipation_hold(self):
        self.assertIsNotNone(importlib.util.find_spec('motion_graphics'),
                             'The new renderer must exist independently of the old preview')
        import motion_graphics as edit
        import music_motion_graphics as music
        self.assertEqual(edit.TL, music.TL)
        self.assertEqual(edit.NFRAMES, 270)
        self.assertEqual(edit.TL['events']['impact']*edit.FPS, 180)
        np.testing.assert_array_equal(edit.render_frame(160, 180, 320),
                                      edit.render_frame(178, 180, 320))
        sound=music.make_score()
        self.assertEqual(sound.shape, (432000, 2))
        self.assertLess(np.max(np.abs(sound[260000:280000])), 1e-7)
        self.assertGreater(np.sqrt(np.mean(sound[288000:292000]**2)), .1)

    def test_camera_choreography_has_visible_motion_and_valid_boundaries(self):
        self.assertIsNotNone(importlib.util.find_spec('motion_graphics'))
        import motion_graphics as edit
        for f in [0, 11, 12, 44, 45, 78, 79, 101, 102, 123, 124, 157, 158, 179, 180, 182, 269]:
            im=edit.render_frame(f, 180, 320)
            self.assertEqual(im.shape, (320, 180, 3))
            self.assertEqual(im.dtype, np.uint8)
        first=edit.render_frame(18, 180, 320).astype(float)
        later=edit.render_frame(40, 180, 320).astype(float)
        self.assertGreater(np.abs(first-later).mean(), 8)
        # Flash clears quickly enough for the finishing pose to read.
        self.assertGreater(edit.render_frame(180, 180, 320).mean(), 220)
        self.assertLess(edit.render_frame(185, 180, 320).mean(), 210)
        for f in [-1, 270]:
            with self.assertRaises(ValueError): edit.render_frame(f, 180, 320)


if __name__=='__main__': unittest.main()
