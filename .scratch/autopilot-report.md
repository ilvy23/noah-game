# autopilot report: partial (interrupted)

wall time: 0.20 h (718 s)   segments: 5   decisions: 5

## stages
- stage 1 [done] Implement context mechanism: 1 attempt(s), 787 s, context.py, dialogue.py, engine.py, locations.py, main.py, noah.py, story.py, tests/test_engine.py +2
- stage 2 [done] Rewrite cryptic texts: 1 attempt(s), 3065 s, locations.py, noah.py, story.py
- stage 3 [done] Add text validation tests: 2 attempt(s), 659 s, tests/test_engine.py, tests/test_text_quality.py
- stage 4 [done] Part 1/6: main.py: 1 attempt(s), 98 s, main.py
- stage 5 [done] Part 2/6: dialogue.py: 1 attempt(s), 407 s, no file changed
- stage 6 [done] Part 3/6: engine.py: 5 attempt(s), 5788 s, .scratch/check_engine.py, .scratch/verify_stage2_engine.py, engine.py, tests/test_scripted_playthroughs.py
- stage 7 [done] Part 4/6: noah.py: 1 attempt(s), 573 s, .scratch/scan_noah.py
- stage 8 [done] Part 5/6: story.py: 1 attempt(s), 598 s, story.py
- stage 9 [done] Part 6/6: PLAN-v2.md, PLAN.md, deaths.py, characters.py: 2 attempt(s), 754 s, .scratch/debug_noah_test.py, .scratch/verify_stage2_final.py, PLAN-v2.md, PLAN.md
- stage 10 [done] Audit achievements.py and verify 12+ achievements: 2 attempt(s), 610 s, achievements.py, tests/test_title_screen.py
- stage 11 [done] Verify level formula and status screen display: 1 attempt(s), 110 s, no file changed
- stage 12 [active] Part 1/2: achievements.py, engine.py, save.json, tests/fixtures/save_v1.json: 6 attempt(s), 1139 s, .scratch/debug_noah_tiers.py, engine.py, save.json
- stage 13 [done] Part 2/2: main.py: 1 attempt(s), 506 s, .scratch/verify_unlock2.py, main.py
- stage 14 [done] Achievements: save file persistence and migration: 1 attempt(s), 342 s, engine.py, tests/test_engine.py, tests/test_save_migration.py, tests/test_scripted_playthroughs.py
- stage 15 [done] Achievements: tests: 1 attempt(s), 294 s, tests/test_achievements.py
- stage 16 [done] Add field journal command: 1 attempt(s), 394 s, main.py, tests/test_journal.py
- stage 17 [done] Add Noah hint command: 1 attempt(s), 395 s, main.py, noah.py, tests/test_hint.py
- stage 18 [done] Add end-of-run summary screen: 1 attempt(s), 455 s, deaths.py, main.py, tests/test_summary.py
- stage 19 [blocked] Update help text and write final summary: 1 attempt(s), 1317 s, .scratch/find_help.py, .scratch/read_dialogue.py, .scratch/read_help.py, .scratch/read_help2.py, .scratch/read_noah.py, .scratch/read_noah2.py, .scratch/read_noah3.py, .scratch/read_noah4.py +3 - needs human: 4 segments in a row without progress, last stop: stage_cap (failing test tests/test_scripted_playthroughs.py::test_talk_noah_all_tiers)

## tests
TESTS: 230 passed, 2 failed (20s) - all 2 were already red before this stage; nothing new broke, they are not part of this stage

## speed (measured)
wall 74686.9 s   3504 steps (2.8 steps/min)   130 segments, 44 stages
  prefill       6312.9 s    8%
  generation    8622.5 s   12%
  tools         1584.0 s    2%   (test runs 1444.3 s)
  waiting        207.6 s    0%
  other        57959.8 s   78%
mean prompt 19k tokens   peak prompt 30k tokens
causes:
  - only 2.8 steps/min (3504 steps in 74687 s; a healthy staged run does 7-9)
  - 68% of the 2714 tool calls were read-only (look steps): the model reads more than it changes
  - thinking steps produced 30% of all generated tokens (106320 of 353502)

## NOT VERIFIED
- stage 12 Part 1/2: achievements.py, engine.py, save.json, tests/fixtures/save_v1.json: active
- stage 19 Update help text and write final summary: needs human: 4 segments in a row without progress, last stop: stage_cap (failing test tests/test_scripted_playthroughs.py::test_talk_noah_all_tiers)
- 230 passed, 2 failed (20s) - all 2 were already red before this stage; nothing new broke, they are not part of this stage tests/test_scripted_playthrough

## changed files
- .scratch/check_engine.py
- .scratch/debug_noah_test.py
- .scratch/debug_noah_tiers.py
- .scratch/find_help.py
- .scratch/read_dialogue.py
- .scratch/read_help.py
- .scratch/read_help2.py
- .scratch/read_noah.py
- .scratch/read_noah2.py
- .scratch/read_noah3.py
- .scratch/read_noah4.py
- .scratch/read_talk.py
- .scratch/read_tests.py
- .scratch/scan_noah.py
- .scratch/test_ach.py
- .scratch/verify_stage2_engine.py
- .scratch/verify_stage2_final.py
- .scratch/verify_stage3.py
- .scratch/verify_unlock.py
- .scratch/verify_unlock2.py
- PLAN-v2.md
- PLAN.md
- achievements.py
- context.py
- deaths.py
- dialogue.py
- engine.py
- locations.py
- main.py
- noah.py
- save.json
- story.py
- tests/fixtures/save_v1.json
- tests/test_achievements.py
- tests/test_engine.py
- tests/test_hint.py
- tests/test_journal.py
- tests/test_save_migration.py
- tests/test_scripted_playthroughs.py
- tests/test_summary.py
- tests/test_text_quality.py
- tests/test_title_screen.py

## scratch files (not part of the work, safe to delete)
- .scratch/characters.py
- .scratch/check_engine.py
- .scratch/counter_reset
- .scratch/deaths.py
- .scratch/debug_noah.py
- .scratch/debug_noah2.py
- .scratch/debug_noah3.py
- .scratch/debug_noah4.py
- .scratch/debug_noah5.py
- .scratch/debug_noah_talk.py
- .scratch/debug_noah_test.py
- .scratch/debug_noah_tiers.py
- .scratch/debug_talk_noah.py
- .scratch/debug_talk_noah2.py
- .scratch/debug_talk_noah4.py
- .scratch/debug_talk_noah5.py
- .scratch/debug_talk_noah6.py
- .scratch/debug_tiers.py
- .scratch/dialogue.py
- .scratch/engine.py
- .scratch/find_help.py
- .scratch/keepalive
- .scratch/last_run.txt
- .scratch/locations.py
- .scratch/main.py
- .scratch/noah_check.py
- .scratch/out.txt
- .scratch/play_all.py
- .scratch/read_dialogue.py
- .scratch/read_help.py
- .scratch/read_help2.py
- .scratch/read_noah.py
- .scratch/read_noah2.py
- .scratch/read_noah3.py
- .scratch/read_noah4.py
- .scratch/read_talk.py
- .scratch/read_tests.py
- .scratch/repro2.py
- .scratch/repro_noah.py
- .scratch/sanity_scan.txt
