"""Combine the answers of several methods into one suggestion (majority vote).

Each method (Crossref, embedded PDF metadata, page layout) proposes a Publication. Two proposals
*agree* when they name the same paper: same first author, same year and same title (compared
without case, punctuation or spacing). The journal and publisher are ignored for agreement
because the offline methods often cannot fill them.

The group with the most proposals wins. Two or more agreeing proposals are a *consensus*; with
no consensus (every method differs, or only one found anything) the proposal of the best-ranked
method wins, and the result says so. Ranking is the order the methods are given in
(Crossref first by default). The winner's journal / publisher are taken from the best-ranked
agreeing proposal that has a real value, so an offline "Unknown publication" never hides
a journal another method found.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from nameit.models.data_models import Publication

UNKNOWN_PREFIX = "Unknown "


@dataclass(frozen=True)
class Candidate:
    method: str
    publication: Publication


@dataclass(frozen=True)
class Decision:
    publication: Publication
    method: str                       # best-ranked method among those that agree with the winner
    agreeing: Sequence[str]           # methods whose proposals match the winner
    asked: int                        # how many methods produced a proposal
    consensus: bool                   # True when at least two methods agree

    @property
    def label(self) -> str:
        if self.consensus:
            return f"{len(self.agreeing)}/{self.asked} agree"
        return "no consensus" if self.asked > 1 else "single source"


def _squash(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.casefold())


def agreement_key(publication: Publication) -> str:
    """Identity of the paper: first author + year + title."""
    first_author = re.split(r"\s+and\s+|\s+et al", publication.authors, maxsplit=1)[0]
    return f"{_squash(first_author)}|{publication.year}|{_squash(publication.title)}"


def _is_real(value: str) -> bool:
    return bool(value) and not value.startswith(UNKNOWN_PREFIX)


def _merged(group: List[Candidate]) -> Publication:
    """Best-ranked proposal, with Unknown journal/publisher filled from agreeing ones."""
    best = group[0].publication
    fields: Dict[str, str] = {}
    for name in ("publication", "publisher"):
        if not _is_real(getattr(best, name)):
            for other in group[1:]:
                if _is_real(getattr(other.publication, name)):
                    fields[name] = getattr(other.publication, name)
                    break
    return Publication(best.authors, best.year, best.title,
                       fields.get("publication", best.publication), fields.get("publisher", best.publisher))


def decide(candidates: Sequence[Candidate]) -> Optional[Decision]:
    """Pick the winning proposal. `candidates` must be in rank order; empty input gives None."""
    if not candidates:
        return None
    groups: Dict[str, List[Candidate]] = {}
    for candidate in candidates:
        groups.setdefault(agreement_key(candidate.publication), []).append(candidate)
    # largest group wins; among equals the group holding the best-ranked proposal (dict keeps rank order)
    winner = max(groups.values(), key=len)
    return Decision(
        publication=_merged(winner),
        method=winner[0].method,
        agreeing=[c.method for c in winner],
        asked=len(candidates),
        consensus=len(winner) >= 2,
    )
