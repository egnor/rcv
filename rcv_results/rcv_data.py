"""Representation of the results of an RCV election"""

from typing import Dict, List

import attr

# Non-candidate ballot categories
BLANK_CHOICE = "*BLANKS*"
EXHAUSTED_CHOICE = "*EXHAUSTED*"
OVERVOTE_CHOICE = "*OVERVOTES*"
SPOILED_CHOICES = set([BLANK_CHOICE, EXHAUSTED_CHOICE, OVERVOTE_CHOICE])


@attr.define
class RoundChoice:
    incoming: float = 0
    action_text: str = ""
    elimination: Dict[str, float] = attr.Factory(dict)
    seated: bool = False


@attr.define
class Round:
    message: str = ""
    choices: Dict[str, RoundChoice] = attr.Factory(dict)


@attr.define
class Election:
    rounds: List[Round] = attr.Factory(list)
    title_text: str = ""
    rcv_text: str = ""
    status_text: str = ""
    time_text: str = ""
    precinct_text: str = ""
