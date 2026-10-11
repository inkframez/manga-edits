"""Shared editorial timing. One beat = 0.375 s; 96 beats = 36 s.

The narrative clock is dilated editorial time, not the export timecode.
Page IDs retain attachment order; shots correct 09:04 / 07:68 chronology.
"""
BPM = 160
BEAT = 60 / BPM
DURATION = 36.0
FPS = 30

# beat start/end, treatment, page, crop (original pixel coordinates), caption
SHOTS = [
    (0, 4, 'open', 1, (0, 150, 1005, 465), 'TWELVE SECONDS'),
    (4, 8, 'versus', 2, (430, 1050, 1700, 550), 'CHIHIRO'),
    (8, 12, 'hero', 1, (0, 780, 1067, 820), 'FIRST CONTACT'),
    (12, 16, 'hero', 2, (450, 0, 1000, 1060), ''),
    (16, 20, 'hero', 3, (0, 0, 1067, 974), ''),
    (20, 24, 'hero', 6, (0, 410, 1067, 920), 'CHANGE THE ANGLE'),
    (24, 26, 'wide', 5, (0, 160, 970, 473), 'THE PRICE'),
    (26, 28, 'strip', 5, (260, 681, 470, 236), ''),
    (28, 32, 'strip', 5, (230, 954, 560, 220), 'FASTER'),
    (32, 36, 'hero', 4, (670, 872, 310, 257), 'READ THE NEXT MOVE'),
    (36, 40, 'wide', 7, (0, 260, 975, 563), 'NO MORE TRICKS'),
    (40, 44, 'rush', 7, (160, 1135, 813, 465), 'ALL IN'),
    (44, 48, 'charge', 7, (160, 1135, 813, 465), 'SOJO  /  2x'),
    (48, 52, 'strip', 8, (1850, 0, 280, 720), 'CHIHIRO'),
    (52, 56, 'charge3', 8, (612, 210, 1230, 1000), 'NISHIKI  /  3x'),
    (56, 60, 'wide', 8, (0, 0, 605, 459), 'FROM ABOVE'),
    (60, 64, 'hero', 8, (612, 210, 1230, 1000), ''),
    (64, 68, 'hero', 9, (0, 0, 1067, 1230), 'HE CAN STILL REACT'),
    (68, 70, 'strip', 9, (0, 1275, 780, 325), ''),
    (70, 72, 'strip', 12, (0, 670, 975, 562), ''),
    (72, 76, 'release', 10, (242, 0, 825, 1200), 'RELEASE NISHIKI'),
    (76, 78, 'strip', 10, (570, 1220, 443, 380), 'THE TIMING SHIFTS'),
    (78, 80, 'kuro', 10, (242, 0, 825, 1200), 'KURO'),
    (80, 84, 'impact', 11, (466, 0, 1667, 1230), ''),
    (84, 88, 'final', 13, (0, 0, 1067, 1600), 'CLOUD GOUGER'),
    (88, 90, 'broken', 11, (0, 0, 453, 1600), 'BROKEN'),
    (90, 92, 'aftermath', 14, (360, 856, 440, 744), ''),
    (92, 96, 'end', 13, (0, 0, 1067, 1600), 'KAGURABACHI'),
]

# [export seconds, story seconds remaining]. Anchors match supplied clocks.
CLOCK = [(0,12), (1.5,12), (3,11.52), (9,9.04), (12,7.68), (15,6),
         (16.5,3), (19.5,1.47), (24,0.89), (25.5,0.89), (27,0.60),
         (29.25,0.18), (30,0), (36,0)]
SLASH_BEATS = [8, 12, 16, 20, 24, 28, 36, 40, 44, 52, 56, 60, 64, 68, 70]
EVENTS = {'arm': 9.0, 'sojo_2x': 16.5, 'chihiro_3x':19.5,
          'release':27.0, 'vacuum':29.25, 'strike':30.0,
          'blade_break':33.0, 'title':34.5}
