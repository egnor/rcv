"""Parse Dominion XML reports"""

from typing import Dict, List
from xml.etree import ElementTree

from rcv_results import rcv_data


def _join_attrs(elems: List[ElementTree.Element], prefix="Textbox") -> str:
    """Joins the text from all attributes that start with a prefix"""
    return "\n".join(
        v for e in elems for k, v in e.items() if k.startswith(prefix) and v
    )


def parse_detailed_report(root: ElementTree.Element) -> rcv_data.Election:
    """Parses an XML detailed report from Dominon for an RCV election"""

    # Expected XML namespace assignment
    ns = {"": "RcvDetailedReport"}

    # Renames from Dominion spoilage categories to our standard ones
    choice_renames = {
        "Blanks": rcv_data.BLANK_CHOICE,
        "Exhausted": rcv_data.EXHAUSTED_CHOICE,
        "Overvotes": rcv_data.OVERVOTE_CHOICE,
        "Remainder Points": "",
    }

    election = rcv_data.Election()

    #
    # Parse <Report> elements that give overall metadata
    #

    title_elems = root.findall(".//Report[@Name='Title']", ns)
    election.title_text = _join_attrs(title_elems)

    state_elems = root.findall(".//Report[@Name='RcvStaticData']/*[@state]", ns)
    election.status_text = "\n".join(s.get("state", "") for s in state_elems)
    election.time_text = "\n".join(s.get("timeStamp", "") for s in state_elems)
    election.rcv_text = _join_attrs(state_elems)

    #
    # Parse <roundGroup> elements (within <precinctGroup> for individual rounds
    #

    pgroup_elems = root.findall(".//precinctGroup", ns)
    election.precinct_text = _join_attrs(pgroup_elems)
    if len(pgroup_elems) != 1:
        raise ValueError(f"{len(pgroup_elems)} <precinctGroup> tags")

    predicted: Dict[str, float] = {}
    for round_elem in pgroup_elems[0].findall(".//roundGroup", ns):
        round = rcv_data.Round()

        #
        # Parse <choiceGroup> elements with choice names & starting vote counts
        #

        # Find the containing <Tablix> with vote totals to cross-check
        data_elems = round_elem.findall(".//*[@continuingVotes]", ns)
        if len(data_elems) != 1:
            err = f"{len(data_elems)} continuingVotes= in <roundGroup>"
            raise ValueError(err)

        round.message = _join_attrs(data_elems)
        unspoiled_total = float(data_elems[0].get("continuingVotes", 0))
        spoiled_total = float(data_elems[0].get("nonTransferableVotes", 0))

        choice_order: List[str] = []
        unspoiled_check = spoiled_check = 0.0
        for choice_elem in round_elem.findall(".//choiceGroup", ns):
            choice = rcv_data.RoundChoice()
            choice.incoming = float(choice_elem.get("votes", 0))

            parsed_name = _join_attrs([choice_elem], prefix="choiceName")
            if not parsed_name:
                raise ValueError("<choiceGroup> without choiceName*=")

            choice_name = choice_renames.get(parsed_name, parsed_name)
            choice_order.append(choice_name)
            if not choice_name:
                if choice.incoming:
                    raise ValueError(
                        f'{choice.incoming} votes for "{parsed_name}"'
                    )
                continue

            if choice_name in round.choices:
                raise ValueError(f"Duplicate choiceName: {choice_name}")

            if choice_name in rcv_data.SPOILED_CHOICES:
                spoiled_check += choice.incoming
            else:
                unspoiled_check += choice.incoming

            if predicted and predicted.get(choice_name) != choice.incoming:
                raise ValueError(
                    f'{choice.incoming} votes for "choice_name" != '
                    f"predicted {predicted.get(choice_name)}"
                )

            round.choices[choice_name] = choice

        # Verify computed totals (for candidates & spoilage) against stored.
        if (unspoiled_check, spoiled_check) != (unspoiled_total, spoiled_total):
            raise ValueError(
                "Vote totals mismatch: computed "
                f"({unspoiled_check}, {spoiled_check}) != declared "
                f"({unspoiled_total}, {spoiled_total})"
            )

        #
        # Parse <choiceId> elements with elimination ballot transfers
        #

        # Stash the contents of <StatusGroup>, which are unfilled templates
        # except when actually relevant (which we must determine)
        status_elems = round_elem.findall(".//StatusGroup", ns)
        if len(status_elems) != len(choice_order):
            raise ValueError(
                f"Mismatch: <StatusGroup> ({len(status_elems)}) != "
                f"<choiceGroup> ({len(choice_order)})"
            )

        status_text = {
            choice_name: _join_attrs([status_elem])
            for choice_name, status_elem in zip(choice_order, status_elems)
            if choice_name
        }

        xfer_names = set()
        xfer_group_elems = round_elem.findall(".//sourceChoiceId", ns)
        for xfer_group_elem in xfer_group_elems:
            xfer_elems = xfer_group_elem.findall(".//choiceId", ns)
            for xfer_elem in xfer_elems:
                xfer_text = _join_attrs([xfer_elem], prefix="votes")
                xfers = float(xfer_text) if xfer_text else None
                source_name = xfer_elem.get("sourceChoiceName", "")
                parsed_name = xfer_elem.get("choiceName", "")
                name = choice_renames.get(parsed_name, parsed_name)
                if xfers is not None:
                    if not name:
                        raise ValueError(f'{xfers} xfers to "{parsed_name}"')
                    if not source_name:
                        raise ValueError(f'{xfers} no-source xfers to "{name}"')
                    elim = round.choices.get(source_name)
                    if not elim:
                        raise ValueError(f'unknown xfer source "{source_name}"')
                    elim.status_text = status_text[source_name]
                    elim.action_text = _join_attrs([xfer_group_elem])
                    elim.elimination[name] = xfers
                if name:
                    xfer_names.add(name)

        # Verify the choice names that showed up in <choiceId> vs earlier data.
        if xfer_names != set(round.choices.keys()):
            raise ValueError(
                "Mismatch: <choiceGroup> ["
                + ", ".join(sorted(round.choices.keys()))
                + "] != <choiceId> ["
                + ", ".join(sorted(xfer_names))
                + "]"
            )

        # Check for magic status text strings (the only indication of victory!)
        for name, text in status_text.items():
            choice = round.choices[name]
            if " is elected " in text:
                choice.status_text = text
                choice.seated = True
            elif " is eliminated " in text:
                choice.status_text = text

        # Make sure rounds are consistent with each other
        if election.rounds:
            if election.rounds[-1].choices.keys() != round.choices.keys():
                raise ValueError(
                    "Choices change between rounds: ["
                    + ", ".join(election.rounds[-1].choices.keys())
                    + "] => ["
                    + ", ".join(round.choices.keys())
                    + "]"
                )

        election.rounds.append(round)

        # Predict the starting values for the next round as a cross check
        predicted = {name: ch.incoming for name, ch in round.choices.items()}
        for choice in round.choices.values():
            for name, delta in choice.elimination.items():
                predicted[name] += delta

    return election


def parse(text: str) -> rcv_data.Election:
    """Parses an XML detailed report from Dominon for an RCV election"""

    root = ElementTree.fromstring(text)
    if root.tag == "{RcvDetailedReport}Report":
        return parse_detailed_report(root)  # The only format supported so far
    else:
        raise ValueError(f"Unrecognized XML root tag: {root.tag}")


#
# Test utility to run from the command line
#

if __name__ == "__main__":
    import argparse

    import prettyprinter  # type: ignore

    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True)
    args = parser.parse_args()
    election = parse(open(args.xml).read())

    prettyprinter.install_extras(["attrs"])
    prettyprinter.cpprint(election)
