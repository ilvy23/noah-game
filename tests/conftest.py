"""The songs and 42 of the sound effects are not distributed (see soundtracks/README.md). A few tests check exactly those
files or the audio cues that need them: they are skipped when the files are missing, everything else runs."""
import os

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEEDS_AUDIO_FILES = {
    "test_all_sound_names_exist_or_are_known_missing", "test_effect_edges_are_faded_no_click_first_and_last_samples_near_zero",
    "test_sounds_in_time_and_present", "test_same_track_no_restart", "test_change_track_restarts", "test_unknown_location_keeps_current",
    "test_stop_kills_process_group", "test_stop_kills_group_not_just_child", "test_disable_stops", "test_the_sounds_of_each_scene",
    "test_full_playthrough_to_ending_with_credits_and_story_flags", "test_thirty_seconds_without_choice_gives_ending_three_with_warning_lines",
    "test_mikas_song_starts_with_the_scene_and_the_cigarette_adds_the_smoke_sound",
    "test_the_smoke_sound_starts_with_mikas_scene_even_if_you_refuse_the_cigarette",
    "test_the_clair_de_lune_scene_plays_its_song_sets_the_bond_and_changes_the_decision_text",
    "test_the_boss_song_fades_out_when_the_fight_is_over_before_the_choice",
}


def pytest_collection_modifyitems(config, items):
    if os.path.isfile(os.path.join(HERE, "soundtracks", "town.flac")) and os.path.isfile(
            os.path.join(HERE, "soundtracks", "sfx", "fire-ignite.mp3")):
        return
    skip = pytest.mark.skip(reason="needs songs / sound effects that are not part of the public repository")
    for item in items:
        if item.name in NEEDS_AUDIO_FILES:
            item.add_marker(skip)
