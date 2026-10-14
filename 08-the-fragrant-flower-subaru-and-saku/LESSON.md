# Romance edits: notes for GPT

`fragrant-flower-short.mp4` is built by `video/render_ff.py`, `video/analyze_song.py` and `video/timeline_ff.py`.
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

## 3. Cutting to a real song
The first version had an original score. The user replaced it with BEAUZ & JVNA – Crazy (NCS), which changes
the job from composing to listening:
- **Pick the excerpt by structure, not by time.** Map the song first (energy per second and a spectrogram):
  intro, verse, build, chorus, pre-drop riser, drop, break. The story's turning point ("...like you") belongs on
  the **drop**, and the edit ends in the piano break that follows it.
- **Build the beat grid from the drop.** Autocorrelation gave 136 BPM, but the phase disagreed from section to
  section (syncopated kicks, triplet hats). Anchoring the grid at the drop's downbeat and checking it against
  snares in the chorus and the drop gave one grid that fits everywhere. Start the excerpt on a downbeat
  (18 bars before the drop) so edit beat 0 is a downbeat.
- **Find the words.** Transcribe 2–5 s overlapping windows (Whisper small.en via sherpa-onnx) to locate each
  phrase to within about half a second, then snap the words to the eighth-note grid. Show short fragments,
  not the whole lyric: one accent word per line (rose, larger), timed to its syllable.
- **Put the story on the song's shape, but never reorder the story.** Verse: calm monologue. Chorus: the lyric
  fragments land on matching shots ("when I'm next to you" over her leaning on him). Pre-drop: snow, the
  umbrella, tears, a breath of dark. Drop: the apology in the manga's order, one cut per bar, and the confession
  **last**, on a bar downbeat with its own white bloom. A first cut put "...like you" on the drop and the
  apology after it. That reads well musically but tells the scene backwards, so the user rightly sent it back.
- **Pulse to the real hits.** `analyze_song.py` detects kick and snare onsets in the excerpt. The picture
  zoom-pulses on kicks (stronger in the drop) and flashes softly on drop snares.
- **Verify sync by measurement.** Cross-correlate the rendered video's audio with the source song: it should
  start exactly at the chosen offset, and the drop should land on the planned frame.
- **Credit.** NCS tracks need their credit block in the description; the end card carries it too. Don't commit
  the song itself to the repo.

## 4. Checklist
- [ ] Does each scene have its own grade, and does the change of grade mark a change of feeling?
- [ ] Is every typeset line on screen long enough to read twice, and on one baseline?
- [ ] Are the drawn balloons readable on a phone (crop in until they are)?
- [ ] Is there one moment of near silence before the line that matters?
- [ ] Does the story's turning point land on the song's drop (or its biggest change)?
- [ ] Is all text readable over bright art (plate behind it) and clear of the Shorts caption overlay?
