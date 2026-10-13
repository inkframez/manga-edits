# Canva layers — cloud editing handoff

This is an asset pack and a **9-second 2.5D demonstration**, not the full Sakamoto
Days Short. Manga: Yuto Suzuki / Shueisha. Preparation: 2026-10-13.

## What is ready

- **29 accepted Canva Magic Layers exports**, saved losslessly as RGBA PNGs in
  `cutouts/`, `backgrounds/`, and `details/`. `layer-contact-sheet.jpg` checks each
  against light and dark fields.
- `layers.json` maps every asset back to its source image. Ten source images were
  processed; processing did not produce usable independent fighters on every page.
- `sakamoto-layer-preview-short.mp4`: 1080 × 1920, 30 fps, 9 seconds, H.264 / AAC.
- `video/layer_preview.py`, `video/music_layer_preview.py`, and the shared
  `video/layer_preview_timeline.json` reproduce the preview and its original audio.
- `layer-preview-sheet.jpg` shows the camera, mirror, pause, impact, and final hold.
- `canva-layer-lab.jpg` records the working Canva design. The original design was
  preserved; the duplicate is [Sakamoto Days — Layer Lab](https://www.canva.com/design/DAHX5g2VC0g/ieO3DyRFQrEOJQ-hWJWbiA/edit).

The Canva duplicate is the processing workspace and retains unfiltered generation
results. The delivered PNG folders and `layers.json` identify the accepted set.
`layer-alignment-sheet.jpg` compares the selected sources with registered layers;
it is an alignment check, not a promise that every page has been fully rebuilt.

## Reassemble before animating

Coordinates are in **original source-image pixels**. `panel_crop` is
`[left, top, right, bottom]`; `origin` is the PNG's top-left in the source image.
`sprite_scale` maps PNG pixels to source pixels. `pivot` uses PNG pixels; `z` gives
the default stack order. Preserve those conventions when importing into another editor.

For a source-space camera centered at `(cx, cy)` with zoom `s`, place a layer at
`(output_width/2 + (origin_x-cx)*s, output_height/2 + (origin_y-cy)*s)` and resize it by
`sprite_scale*s`. The preview's `place_rgba` interpolates premultiplied color and
alpha, which prevents transparent pixels from producing colored fringes.

Registration uses Canva's visible canvas geometry, checked against feature
registration. The overlapping checks differ by less than 0.33 source pixels.
The opening character moved by the user is registered to its original manga
position, rather than its displaced position in the Canva demonstration.

The inputs were cropped at source resolution. Canva delivered some smaller raster
layers; their real sizes and required scales are recorded. No fabricated high
resolution or replacement face is supplied.

## Quality limits that matter

- **Page 007:** Canva returned flattened panel strips and speech balloons. Use the
  unchanged original image; no independent character layer is claimed.
- **Pages 010 and 017:** rejected backgrounds contain residual or reconstructed
  fighter silhouettes. Animate their accepted foregrounds on designed paper/ink
  fields, or use the original spread for a static hold.
- **Page 016 release hand:** rejected because white interior pixels became
  transparent. Keep the hand in the original panel if that beat is needed.
- `action_pair` means overlapping fighters remain joined. Do not rig the pair as
  two independent bodies. `detail` may be a partial head or a flat reflection panel.
- Reconstructed plates are suitable only for the modest movements in each asset's
  `max_translation_source_px`. Keep the matching foreground over the repaired area.
- The tiny passage figure and descent cutouts have limited detail or light edge
  fringes. Use them at modest scale; the preview avoids those weaker extractions.
- Canva's replacement OCR lettering, empty bases, and incidental border fragments
  were discarded. Preserve drawn lettering from the original sources. The opening
  preview explicitly restores the original top strip containing the drawn sound effect.

## Lessons applied from Kagurabachi

The artwork fills the vertical frame; the reflection uses full-width bands with a
large floating prop. There are no permanent HUD rails. The palette is paper, ink,
and amber, with amber reserved for metal and impact cues. Layer motion follows
the attack; the hammer crosses the image band. The 0.75-second pause precedes the
strike at 6 seconds. The final shot returns to the authentic source spread.

Picture and sound read the same timeline JSON. The illustration poses stay intact:
this demonstrates compositing and camera depth, not new limb animation or a new fight.

## Render and verify

Use the repository's Python requirements and run from `video/`:

```bash
python music_layer_preview.py
python layer_preview.py stills
python layer_preview.py video
python -m unittest test_layer_preview -v
python verify_layer_preview.py
```

Fonts use Windows Impact when present, then the repository's `fonts/impact.ttf`
stand-in, then Pillow's scalable default. Canva is unnecessary for rerendering.
Review frames are written to the gitignored `video/stills_layers/` folder.

Audio is synthesized from scratch: bass, percussion, swishes, metal tones, and an
impact. A fast peak compressor and lookahead limiter precede measured loudness
normalization, with extra headroom for resampling and AAC. The
final AAC loudness, true peak, frame count, duration, alpha checks, source hashes,
and quiet-gap ratio are recorded by `video/verification.json`.

For the full Short, build out the sequence from the source panels and stronger
accepted layers. Keep the hammer's reflection before the counter, and treat this
preview as a motion-language sample rather than the complete fight narrative.
