"""Parse Dominion XML reports"""

from typing import List
from xml.etree import ElementTree

from rcv_results import rcv_data


def all_textboxes(elems: List[ElementTree.Element], prefix="Textbox") -> str:
    return "\n".join(
        v for e in elems for k, v in e.items() if k.startswith(prefix) and v
    )


def parse_detailed_report(root: ElementTree.Element) -> rcv_data.Election:
    ns = {"": "RcvDetailedReport"}

    election = rcv_data.Election()

    title_elems = root.findall(".//Report[@Name='Title']", ns)
    election.title_text = all_textboxes(title_elems)

    state_elems = root.findall(".//Report[@Name='RcvStaticData']/*[@state]", ns)
    election.status_text = "\n".join(s.get("state", "") for s in state_elems)
    election.time_text = "\n".join(s.get("timeStamp", "") for s in state_elems)
    election.rcv_text = all_textboxes(state_elems)

    precinct_elems = root.findall(".//precinctGroup", ns)
    election.precinct_text = all_textboxes(precinct_elems)
    if len(precinct_elems) != 1:
        raise ValueError(f"{len(precinct_elems)} <precinctGroup> tags")

    for round_elem in precinct_elems[0].findall(".//roundGroup", ns):
        round = rcv_data.Round()

        data_elems = round_elem.findall(".//*[@continuingVotes]", ns)
        if len(data_elems) != 1:
            err = f"{len(data_elems)} continuingVotes= in <roundGroup>"
            raise ValueError(err)

        round.message = all_textboxes(data_elems)
        unspoiled_total = float(data_elems[0].get("continuingVotes", 0))
        spoiled_total = float(data_elems[0].get("nonTransferableVotes", 0))

        unspoiled_check = spoiled_check = 0
        for choice_elem in round_elem.findall(".//choiceGroup", ns):
            choice = rcv_data.RoundChoice()
            choice.incoming = float(choice_elem.get("votes", 0))

            choice_name = all_textboxes([choice_elem], prefix="choiceName")
            if not choice_name:
                raise ValueError("<choiceGroup> without choiceName*=")

            if choice_name == "Remainder Points":
                if choice.incoming != 0:
                    raise ValueError("Nonzero 'Remainder Points'")
                continue

            choice_name = {
                "Blanks": rcv_data.BLANK_CHOICE,
                "Exhausted": rcv_data.EXHAUSTED_CHOICE,
                "Overvotes": rcv_data.OVERVOTE_CHOICE,
            }.get(choice_name, choice_name)

            if choice_name in round.choices:
                raise ValueError(f"Duplicate choiceName: {choice_name}")

            if choice_name in rcv_data.SPOILED_CHOICES:
                spoiled_check += choice.incoming
            else:
                unspoiled_check += choice.incoming

            round.choices[choice_name] = choice

        if (unspoiled_check, spoiled_check) != (unspoiled_total, spoiled_total):
            raise ValueError(
                "Vote totals mismatch: computed "
                f"({unspoiled_check}, {spoiled_check}) != declared "
                f"({unspoiled_total}, {spoiled_total})"
            )

        if election.rounds:
            if election.rounds[-1].choices.keys() != round.choices.keys():
                raise ValueError(
                    "Choices change between rounds: [" +
                    ", ".join(election.rounds[-1].choices.keys()) + "] => [" +
                    ", ".join(round.choices.keys()) + "]"
                )

        election.rounds.append(round)

    return election


def parse(text: str) -> rcv_data.Election:
    root = ElementTree.fromstring(text)
    if root.tag == "{RcvDetailedReport}Report":
        return parse_detailed_report(root)
    else:
        raise ValueError(f"Unrecognized XML root tag: {root.tag}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True)
    args = parser.parse_args()
    election = parse(open(args.xml).read())
    print(election)
