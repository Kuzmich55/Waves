"""The one-time FLAC signature notice (flacNoticeGate) and the dialog buttons.

FLAC files saved by earlier versions (the gap came from tidal-dl-ng) can lack
their audio signature. After the update a notice says so once, on Browse, and
offers the Settings check that fixes them.

WHAT THIS FENCES OFF
--------------------
1. It shows once per install, ever: keyed to its own persisted flag, not to
   a version, so a later update never brings it back; either button and a
   click-away all retire it.
2. A fresh install never sees it: the first terms acceptance marks it seen,
   since only files saved by an earlier version can need the fix.
3. It waits for the whole first-run chain and the update prompt, and only
   opens on Browse, never over Settings, an artist page or the library.
4. TAKE ME TO THE FIX lands on the FLAC card itself, not the top of Settings.
5. Every dialog button hugs its label (SpecBtn); the full-width stretched
   GateAction shape is gone, and a card is wide enough that its button row
   keeps the padding (the download-location nudge runs at 500).
6. It never stacks with a first-run prompt: it reads their eligibility, not
   their lagging visible, and steps aside while one comes due.
"""

from __future__ import annotations

import re
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "waves" / "waves_ui" / "qml"
MAIN = (QML / "Main.qml").read_text(encoding="utf-8")
SETTINGS = (QML / "SettingsPage.qml").read_text(encoding="utf-8")


def _gate() -> str:
    m = re.search(r"id: flacNoticeGate\b.*?\n    }\n", MAIN, re.S)
    assert m, "the FLAC notice must exist in Main.qml"
    return m.group(0)


def test_notice_shows_once_per_install_on_browse():
    gate = _gate()
    clear = re.search(r"promptsClear:(.*?)\n\s*readonly property bool shouldShow", gate, re.S).group(1)
    for clause in (
        "root.signedIn",
        "setupSettings.ffmpegSetupDone",
        "root.termsCurrentAccepted",
        "bootOverlay.done",
        "!ffmpegGate.wanted",
        "!updateOptInGate.shouldShow",
    ):
        assert clause in clear, f"notice visibility lost its {clause!r} clause"
    cond = re.search(r"shouldShow:(.*?)\n\s*// Latched", gate, re.S).group(1)
    for clause in (
        "promptsClear",
        "!setupSettings.flacNoticeSeen",
        "root.browseOpen && !root.settingsOpen && !root.artistOpen && !root.libraryOpen",
    ):
        assert clause in cond, f"notice visibility lost its {clause!r} clause"
    # Persisted in QSettings beside the other one-time prompts, never keyed
    # to a version string.
    assert "property bool flacNoticeSeen: false" in MAIN
    assert "flacNoticeVersion" not in MAIN
    # Both buttons and the click-away answer for good through one path.
    assert gate.count("flacNoticeGate.answer(") == 3
    answer = re.search(r"function answer\(toFix\) \{(.*?)\n        \}", gate, re.S).group(1)
    assert "setupSettings.flacNoticeSeen = true" in answer
    assert "if (toFix) root.openFlacSetting()" in answer
    assert 'label: "TAKE ME TO THE FIX"' in gate
    assert 'label: "GOT IT"' in gate
    assert "parent: Overlay.overlay" in gate


def test_notice_never_stacks_with_a_first_run_prompt():
    gate = _gate()
    clear = re.search(r"promptsClear:(.*?)\n\s*readonly property bool shouldShow", gate, re.S).group(1)
    # A gate's visible trails its fade-in (the update prompt) or the launch
    # reveal (FFmpeg): in the tick both become due it still reads false, and
    # the notice latched on top of the prompt. Eligibility never lags.
    assert "ffmpegGate.visible" not in clear and "updateOptInGate.visible" not in clear
    # Painted only while every prompt is clear and the update prompt has
    # faded out: one due while the notice is up takes the frame first.
    on_top = re.search(r"readonly property bool onTop:([^\n]*)", gate).group(1)
    for clause in ("shown", "promptsClear", "!updateOptInGate.visible"):
        assert clause in on_top, f"the notice's on-screen test lost {clause!r}"
    assert "opacity: onTop ? 1 : 0" in gate
    assert "anchors.verticalCenterOffset: flacNoticeGate.onTop ? 0" in gate
    assert "opacity: shown ? 1 : 0" not in gate
    # One flip (signedIn) can reach this binding before the update prompt's,
    # so the latch is taken a beat later and re-reads shouldShow then.
    assert "function latch() { if (shouldShow) shown = true }" in gate
    assert "onShouldShowChanged: if (shouldShow) Qt.callLater(latch)" in gate
    assert "Component.onCompleted: Qt.callLater(latch)" in gate
    assert "onShouldShowChanged: if (shouldShow) shown = true" not in gate


def test_notice_cannot_be_answered_while_stepping_aside():
    gate = _gate()
    # It stays painted through its fade-out when another prompt comes due; a
    # click in that window must not retire a notice the user never read.
    answer = re.search(r"function answer\(toFix\) \{(.*?)\n        \}", gate, re.S).group(1)
    assert answer.lstrip().startswith("if (!onTop) return")
    scrim = "MouseArea { anchors.fill: parent; enabled: flacNoticeGate.onTop; onClicked: flacNoticeGate.answer(false) }"
    assert scrim in gate


def test_fresh_install_never_sees_the_notice():
    m = re.search(r"if \(!legalSettings\.termsAccepted\) \{(.*?)\}", MAIN, re.S)
    assert m, "the first terms acceptance must mark the fresh-install flags"
    assert "setupSettings.flacNoticeSeen = true" in m.group(1)


def test_notice_wording():
    gate = _gate()
    assert 'text: "FLAC files from earlier versions"' in gate
    for phrase in (
        "tidal-dl-ng, which Waves grew from",
        '<b><font color=\\"" + root.textHi + "\\">The music in them is intact and plays normally</font></b>',
        "Waves now adds the signature to everything it saves",
        "without touching the audio",
        '<b><font color=\\"" + root.textHi + "\\">Fixing them is optional.</font></b>',
    ):
        assert phrase in gate
    assert "\u2014" not in gate, "no em dashes in UI copy"


def test_take_me_to_the_fix_lands_on_the_flac_card():
    assert 'settingsPage.jumpToCard("flac")' in re.search(
        r"function openFlacSetting\(\) \{.*?\n    \}", MAIN, re.S
    ).group(0)
    jump = re.search(r"function jumpToCard\(cardId\) \{.*?\n    \}", SETTINGS, re.S).group(0)
    assert 'if (cardId === "flac")' in jump
    assert "page.flacCardItem.mapToItem(settingsFlick.contentItem" in jump
    # Rides the section's open animation instead of clamping on the first frame.
    assert "page.pendingY =" in jump and "page._restoreScroll()" in jump
    assert "onItemChanged: if (item) page.flacCardItem = item" in SETTINGS


def test_dialog_buttons_hug_their_labels():
    assert "GateAction" not in MAIN, "dialog buttons are SpecBtn, never the full-width stretched shape"
    # No button row in a dialog stretches across the card.
    for m in re.finditer(r"RowLayout \{\n(\s+)([^\n]*)\n\s+SpecBtn", MAIN):
        assert "Layout.fillWidth: true" not in m.group(2), m.group(0)


def test_folder_nudge_card_keeps_its_padding():
    # CHOOSE A NEW LOCATION + KEEP THE DEFAULT LOCATION hug to about 439 px,
    # wider than a 460 card's 420 px padded column.
    m = re.search(r"id: folderNudge\b.*?anchors\.centerIn: parent; width: (\d+)\n", MAIN, re.S)
    assert m, "the download-location nudge card must exist"
    assert int(m.group(1)) >= 500
    assert "width: parent.width - 40" in MAIN[m.end() : m.end() + 600]
