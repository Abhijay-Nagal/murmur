from murmur.engine.cleanup import basic_clean
from murmur.engine.text import apply_replacements, apply_voice_commands


def test_fillers_removed_without_stray_commas():
    assert basic_clean("Um, so I think we should, uh, meet on Tuesday.") == "So I think we should meet on Tuesday."
    assert basic_clean("umbrella under the hmm, tree") == "Umbrella under the tree"


def test_basic_clean_keeps_line_breaks():
    assert basic_clean("Hello\nworld") == "Hello\nworld"


def test_voice_commands():
    assert apply_voice_commands("Dear Sam, new line. Thanks for the notes.") == "Dear Sam,\nThanks for the notes."
    assert apply_voice_commands("First point. New paragraph. second point.") == "First point.\n\nSecond point."


def test_replacements_whole_word_case_insensitive():
    reps = [["my email", "me@example.com"], ["sig", "Best,\nAlex"]]
    assert apply_replacements("Send it to My Email please", reps) == "Send it to me@example.com please"
    assert apply_replacements("signal sig", reps) == "signal Best,\nAlex"


def test_replacement_text_with_backslashes_is_literal():
    assert apply_replacements("path", [["path", r"C:\new"]]) == r"C:\new"


def test_cleanup_guard_accepts_edits_and_rejects_answers():
    from murmur.engine.cleanup import looks_like_cleanup

    src = "I think the deadline is Friday. Actually, scratch that, it's Monday."
    assert looks_like_cleanup(src, "I think the deadline is Monday.")
    assert looks_like_cleanup("first eggs second milk", "1. Eggs\n2. Milk")
    assert not looks_like_cleanup("What is the capital of France?", "Paris.")
    assert not looks_like_cleanup("write a poem about cats", "Soft paws upon the windowsill, the moonlight glows")
