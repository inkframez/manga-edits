"""Behavior checks for the reusable layer compositor and shared preview timing."""
import unittest
import numpy as np
import layer_preview as preview
import music_layer_preview as music


class LayerPreviewTests(unittest.TestCase):
    def test_transparent_pixels_cannot_bleed_color_into_scaled_edges(self):
        canvas = np.zeros((16, 16, 3), np.float32)
        sprite = np.zeros((4, 4, 4), np.uint8)
        sprite[:, :, 2] = 255  # invisible blue must stay invisible
        sprite[1:3, 1:3] = [255, 0, 0, 255]
        preview.place_rgba(canvas, sprite, (3.25, 4.5), 1.8)
        self.assertGreater(canvas[:, :, 0].max(), .8)
        self.assertLess(canvas[:, :, 2].max(), .001)
        self.assertEqual(float(canvas[0, 0].sum()), 0.)

    def test_picture_and_audio_share_the_impact_time(self):
        self.assertEqual(preview.NFRAMES, 270)
        self.assertEqual(preview.event_frame('impact'), 180)
        self.assertEqual(music.event_sample('impact'), 288000)
        self.assertEqual(preview.scene_at_frame(89), 'opening')
        self.assertEqual(preview.scene_at_frame(90), 'reflection')
        self.assertEqual(preview.scene_at_frame(158), 'hold')
        self.assertEqual(preview.scene_at_frame(180), 'impact')

    def test_render_boundaries_and_determinism(self):
        for f in [0, 89, 90, 157, 158, 179, 180, 269]:
            image = preview.render_frame(f, width=180, height=320)
            self.assertEqual(image.shape, (320, 180, 3))
            self.assertEqual(image.dtype, np.uint8)
        np.testing.assert_array_equal(preview.render_frame(45, 180, 320),
                                      preview.render_frame(45, 180, 320))
        for f in [-1, 270]:
            with self.assertRaises(ValueError):
                preview.render_frame(f, 180, 320)

    def test_score_has_a_quiet_gap_and_exact_duration(self):
        sound = music.make_score()
        self.assertEqual(sound.shape, (432000, 2))
        quiet = sound[int(5.4*music.SR):int(5.9*music.SR)]
        drive = sound[int(1.*music.SR):int(2.5*music.SR)]
        self.assertLess(np.sqrt(np.mean(quiet**2)), np.sqrt(np.mean(drive**2))*.12)
        self.assertTrue(np.isfinite(sound).all())


if __name__ == '__main__':
    unittest.main()
