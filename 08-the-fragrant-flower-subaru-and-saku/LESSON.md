# Romance edits: notes for GPT

`fragrant-flower-short.mp4` is built by `video/render_ff.py`, `video/music_ff.py` and `video/timeline_ff.py`.
The fight edits (Kagurabachi, Sakamoto Days) are about impact. A romance edit is about **breath**: the
viewer has to feel time slow down. The same machinery gets used in nearly opposite ways.

## 1. What changes from a fight edit

| Fight edit | Romance edit |
|---|---|
| Expo-out snaps, hit-stops, shakes, impact frames | Slow eased cameras (`eio2`), long dissolves through a soft blur, no shake |
| Hard cuts on the beat | Cuts on the **bar** (every 4 beats), with dissolves and light leaks |
| High contrast, one loud accent | A duotone **grade per scene** that tells you where you are emotionally: warm café → dusk car → faded memory → blue snow → rose confession |
| Speed lines, sparks, ink | Snow in three depths, bokeh, dust in the light, light leaks, bloom |
| Beat pulse 3 %, every kick | Beat pulse 0.6 %: the picture breathes rather than punches |
| Big condensed type for names and SFX | Her **inner monologue** in an italic serif, word by word (rise, sharpen, fade in), on one baseline |
| Loudest moment after a silence | Same rule, quieter: near silence on "I...", then the swell on "...like you" |

## 2. Picture rules
- **Read the scene before you pick the shot.** The emotional spine here is her monologue (narration boxes)
  and two lines of dialogue. Typeset the monologue large; leave the drawn balloons exactly as lettered.
- **Wide panels become bands over their own blurred enlargement** (`band` + `backdrop`). Tall panels and
  faces run full-bleed (`full`) with a slow push toward the eyes.
- **Make the art feel alive without animating it.** `living()` applies a 1 px breathing displacement field; the
  final close-up adds a travelling wave on the left side so her hair moves in the wind. Snow in front of the art
  (soft, large) and behind it (small, sharp) gives depth to a flat page.
- **Grade with meaning.** The same grey page reads as memory (lifted blacks, warm, halation) or as the present
  in the snow (deep blue blacks, cold highlights). Bloom on the highlights is where the "glow" of romance
  edits comes from.
- **Typography:** one italic serif, centred, on a shared baseline (use the font's ascent, not each word's
  bounding box, or the words jump). It needs a soft dark glow for legibility over bright art.

## 3. Sound rules
- **The genre is the instrument.** A modelled felt piano (stretched partials, three detuned strings, felt
  hammer, pedal), a soft lofi beat (round kick, finger snap, swung shaker), strings for the swell, celesta
  once the snow starts, vinyl crackle and wind.
- **Harmony carries the story.** The J-pop "royal road" (IV–V–iii–vi) never lands on the tonic, so it sounds
  like longing. The tonic chord (D) is withheld until the title, so the confession feels resolved.
- **Arrange to the picture.** Piano alone for the fairy tale, the beat enters in the café, it thins when the
  snow begins, strings come in for the realisation, the drums drop out for "I...", and the full swell lands on
  "...like you". `timeline_ff.SECTIONS` drives the drum map, the chord voicings and the picture's beat pulse.
- **Measure the mix.** Check the band energies and a spectrogram: the first pass was 13 dB dark above
  2 kHz, and a low pan value produced NaNs. The fix was a brighter felt, a louder shaker, less bass, and a
  gentle tilt EQ. Finish with two-pass `loudnorm` to −14 LUFS.

## 4. Checklist
- [ ] Does each scene have its own grade, and does the change of grade mark a change of feeling?
- [ ] Is every typeset line on screen long enough to read twice, and on one baseline?
- [ ] Are the drawn balloons readable on a phone (crop in until they are)?
- [ ] Is there one moment of near silence before the line that matters?
- [ ] Does the harmony resolve only when the story does?
