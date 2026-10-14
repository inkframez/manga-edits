# Animating extracted manga characters: notes for GPT

The full Short is `sakamoto-days-short.mp4`, built by `video/render_short.py`, `video/music_short.py` and
`video/timeline_short.py`. These notes cover what was missing from `sakamoto-motion-graphics-short.mp4` and how
to use a layer pack like `layers.json` so the characters actually fight.

## 1. Why the 9-second version didn't work

| What it did | Why it falls flat | What the full Short does instead |
|---|---|---|
| Treated `max_translation_source_px` (5–24 px) as the motion budget, so fighters drift a few pixels. | A 20 px drift on a 1080 px frame reads as a still image. Extracting the characters and then not moving them wastes the extraction. | That limit applies only **while a fighter sits on its own reconstructed plate**. For real moves (300–900 px lunges, spins, recoils), the fighters go on **designed fields** or **break out of bands**, where there's no repaired background to expose. |
| Held one composition for 1.3 s ("REFLECT.", 4.63–5.97 s), frozen grain included. | A freeze only works if something just happened or is about to. Here nothing is moving and there's nothing to read. | The quiet beat before the blow is 0.7 s of **black with near-silence** (`s_breath`), and the contact itself gets a **hit-stop**. |
| Paper-coloured voids around small art; amber limited to a 1 px glint. | Low contrast and an accent nobody notices make the phone screen look empty and grey. | **Hazard yellow fields**, ink fields and full-bleed pages. One accent, used at full strength: names, rims, impact stars, sparks, afterimages. |
| 9 seconds of one rooftop hit, a reflection and an ending. | No story: the chapter's beats (descent, passage, spread, Noh stage, disguise, mirror, finish) never appear. | 32 s covering the chapter in order, with a VS card, 25 cuts, 17 contact hits and 3 lines of dialogue chosen for meaning. |
| Typography labels ("CLASH", "SHIFT", "REFLECT."). | Telling the viewer what they're seeing. | Our own type only names the fighters, frames the twist ("THE HAMMER IS A MIRROR.") and carries one line ("BUT I'VE HAD ENOUGH."). Yuto Suzuki's drawn SFX stay as lettered and are never duplicated. |
| Generic 160 BPM bed under 9 s of picture. | The music isn't about anything in particular. | 170 BPM phonk (cowbell hook, gliding 808, clap, trap hats) arranged to the story, with tsuzumi and flute for the Noh stage. The picture zoom-bumps on every kick the score plays. |

## 2. How to animate a cut-out (it's a puppet, not a sticker)

The poses are drawn, so we never bend limbs. We move, rotate and scale the whole layer, and that's enough when the
**timing** is right. Every contact in `render_short.py` follows the same five stages:

1. **Anticipation.** Before the hit, pull the fighter *away* from the target: offset back 200–900 px, rotate
   5–12° away, sometimes scale down (`s_rooftop`, `s_leap`, `s_impact`).
2. **Action.** Close the gap with an *ease-in* (`ein(u, 3)`), so it accelerates into the hit. Add a **smear**
   (directional blur along the velocity, `vel=`) and 1–3 yellow **afterimages** (`ghosts=`) only while moving fast.
3. **Contact + hit-stop.** On the beat, freeze the puppets for 0.05 / 0.10 / 0.17 s depending on strength
   (`timeline_short.HITSTOP`, applied through `held()` / `since_hit()`). The camera keeps shaking and the sparks
   keep flying, which is what makes a freeze feel like force instead of a dropped frame.
4. **Recoil.** A damped spring (`recoil(dt, amp)`) knocks the fighter back and lets it overshoot once.
5. **Settle.** A slow drift or push until the next cut, so the frame is never dead.

The clash spread (`s_clash`) chains this four times on beats 29, 31, 32 and 32.5. The fighters are kicked apart
after each freeze and slammed back on the next beat. The **camera breathes with the gap**: it pulls wide while
they're apart and goes tight on contact, so both faces stay in frame.

### Other rules
- **Parallax.** Background, fighters and particles move at different rates. In the shaft (`s_shaft`) the camera
  dives at one speed and the fighters fall faster, with debris flying up past them.
- **Secondary motion comes from particles, not warps.** Use ballistic ink droplets with gravity (`ink_drops`),
  sparks (`sparks`), tumbling debris (`shards`) and impact stars drawn *behind* the fighters (`burst`).
- **Joined layers move as one.** `action_pair` layers and the reveal head + cloth + motion trail move together
  (`s_reveal`), as the layer notes require.
- **Make cut-outs look deliberate.** On flat fields, draw a paper or yellow **sticker rim** under the sprite
  (`rim=`). It hides Canva's edge fringes and makes the cut-out a style choice.
- **Break the panel border.** Put the page as a band and let the fighter overlap its edges (`s_leap`). It's the
  quickest way to make a static page feel 3-D.
- **Firm up the alpha.** Canva left screentone semi-transparent (19 % soft pixels on `clash_yotsumura`), which
  shows through on colour. `layer()` remaps alpha for characters, props and details.
- **Props can spin.** `hammer_flying` rotates 720° and scales 3× toward the lens. The reflection embedded in the
  metal comes along, so the twist stays readable.

## 3. Sound: phonk, built from the picture's timeline

The first pass used jazz-funk and the user rejected it. It sounded busy and thin, and it isn't what manga or anime
edit audiences expect. The score is now **phonk**, the house sound of edits on Shorts and TikTok:

- **The hook is an 808 cowbell.** Two band-limited square waves about a fifth apart (the TR-808 recipe), playing
  an E-phrygian riff with lots of reverb. It's the most recognisable part, so it gets the most level.
- **The 808 slides.** A sine with a pitch punch, a glide into the next bar's root, hard saturation, and a short
  kick layered on top so each hit punches instead of droning. Keep it mono.
- **Clap on the backbeat, rolling hats.** 8ths with a trap roll every second bar in the half-time drops, and
  16ths in the double-time sections (the clash, the final blow).
- **Song form follows the story.** `timeline_short.SECTIONS` says intro, drop, break (dark passage), drop2
  (clash), noh (tsuzumi and flute), drop, build (mirror and hammer: filter opens, snare roll accelerates),
  silence (0.7 s), drop2 (the blow), soft (the last line), drop (title). The arrangement is written from that list.
- **Picture and sound share the drum map.** `drum_hits()` generates every kick and clap. The score plays them,
  and the renderer **zoom-bumps on every kick and jolts or flashes on every clap**, so the picture pulses with
  the music you hear. Contacts in `HITS` add a clang and a clap; the three biggest also get a two-frame
  inverted **impact frame** with yellow focus lines, the anime "sakuga" flash.
- **Mix for phones.** Measure it, don't guess. The first phonk mix had the sub 12 dB over the hook and the 808
  as a flat wall with no transients. Fix with per-band energy and a spectrogram: shorter 808 decay, a punch
  kick on top, the hook and reverb up, and the kick ducking the melodic buses. Finish with two-pass `loudnorm`
  to −14 LUFS / −1.5 dBTP.

## 4. Checklist before calling an edit done

- [ ] Do the extracted characters travel visibly (hundreds of pixels, not tens) at least once per shot that uses them?
- [ ] Does every contact have anticipation, a hit-stop, a recoil and a sound with three layers?
- [ ] Are smears and afterimages used only while something is moving fast?
- [ ] Is there a moment of silence, or near-silence, before the biggest hit?
- [ ] Does the camera react to the action (punch on contact, breathe with distance)?
- [ ] Is any frame held for more than half a second with nothing changing? If so, cut it or move it.
- [ ] Are the drawn SFX kept and never duplicated by our own type?
- [ ] Do picture and score import the same timeline, and does the picture pulse on the kicks?
- [ ] Is the hook the loudest melodic element, with the 808 punching instead of droning? Check a spectrogram.
