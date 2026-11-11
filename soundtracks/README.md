# Music

**This repository contains no music.** The author's playlist consists of commercial songs that cannot be redistributed.
The game runs completely without them: it simply plays no background music and no song fades.

To get the full atmosphere, put your own tracks into this folder (`soundtracks/`). The extension can be `.flac`, `.mp3`,
`.ogg` or `.wav`; the file name (without the extension) decides where the track plays. Pick whatever fits the mood.
You need `mpv` (or `ffplay`) installed to hear anything.

| File name | Where it plays |
|---|---|
| `game-1`, `game-2` | default background music; the two alternate after each track ends |
| `town`, `forest`, `nook` | fallback tracks for the town, the forest and the Nook |
| `lunuen`, `wald` | music for the town (Lünen) and the forest |
| `strange`, `strange-tape` | the unsettling long track in the castle and the cellar, and the tape sound that leads into it |
| `schloss`, `keller` | castle / cellar tracks |
| `noa-main`, `noa-alt` | Noah's theme on the first meeting, and the alternative on the second and third |
| `noa-mood`, `noa-rip` | the moment Noah's mood turns (a transition sound, then the track) |
| `boss-noa` | the boss fight |
| `mika`, `mika-smoke` | Mika's scenes (and the sound that starts them) |
| `connor` | Connor's scenes |
| `noah-clair`, `traum` | two single scenes (a quiet one and the dream) |
| `ending-let-it-live`, `ending-slaughter-it`, `ending-3` | the three endings (the credits roll over the song, so a song as long as the credits works best) |
| `ending-special` | the hidden ending |
| `noah-burns-song` | one long song for a late scene; the lyric overlay needs word timings in `lyrics/noah-burns-song.words.json` and is skipped without them |

`tracks.json` is the table behind this (you can change the mapping there). If a file is missing, the game ignores it silently.
`SONGS.json` lists the songs the author used; the end credits only name songs whose file is really in this folder.

# Sound effects

`sfx/` holds 226 CC0 effects from freesound.org, every source is listed in `../docs/SFX-DOWNLOADED.md`. The author used 42
more effects (short stings, screams, fire and blood sounds) that are not redistributable; the game asks for them by name and
stays silent at those moments. You can add your own files with these names to `sfx/` (any of the four extensions):

`blade-block` `blade-shatter` `blood-boil` `blood-spurt` `bone-crack-1` `bone-crack-2` `bubbles-gurgle` `church-bell-toll`
`crowd-scream-distant` `electric-surge` `fall-wind` `fire-ignite` `fire-roar` `flesh-burn` `glass-crack` `glitch-burst`
`glow-hum-rising` `ground-rumble` `growl-demon` `gurgle-breath` `hell-roar` `impact-boom-huge` `iron-bar-hit` `knife-draw`
`lake-whispers` `riser-reverse` `scream-choir` `scream-distorted-1` `scream-distorted-2` `scream-falling-1`
`scream-falling-2` `scream-fire` `scream-reverse` `shield-hit` `sob-small` `stab-flesh` `static-burst` `stone-split` `sub-drop`
`system-error-beep` `tesseract-spin-up` `typing-fast`

`voices/` (the text blips) and `impact.wav` are synthesised sounds made for this game and are included.
