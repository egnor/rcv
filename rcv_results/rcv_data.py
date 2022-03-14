"""Representation of the results of an RCV election"""

from typing import Dict, List

import attr

# Spoilage categories (pseudocandidates) for votes that can't be counted
BLANK_CHOICE = "*BLANKS*"
EXHAUSTED_CHOICE = "*EXHAUSTED*"
OVERVOTE_CHOICE = "*OVERVOTES*"
SPOILED_CHOICES = set([BLANK_CHOICE, EXHAUSTED_CHOICE, OVERVOTE_CHOICE])


@attr.define
class RoundChoice:
    """The status of one choice (candidate or spoilage category) in a round"""

    incoming: float = 0  # Votes at start of round
    status_text: str = ""  # Status of the candidate (readable text)
    action_text: str = ""  # Action taken as a result (readable text)
    elimination: Dict[str, float] = attr.Factory(dict)  # Vote reassignment
    seated: bool = False  # True if the candidate won


@attr.define
class Round:
    """The details of one round of RCV (IRV)"""

    message: str = ""  # Like "Round 3"
    choices: Dict[str, RoundChoice] = attr.Factory(dict)  # Participants


@attr.define
class Election:
    rounds: List[Round] = attr.Factory(list)  # RCV rounds, in order
    title_text: str = ""  # Readable title text
    rcv_text: str = ""  # Readable RCV-specific intro
    status_text: str = ""  # Readable overall status
    time_text: str = ""  # Readable timestamp
    precinct_text: str = ""  # Readable geo region
