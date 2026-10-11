"""Deterministic checks on a drafted message, run by the harness before the draft is stored.

Every rule here is one the prompts already state. They are repeated in code because prompt rules
are followed *most* of the time, not always -- the dash ban, the no-repo rule and the
one-project-per-thread rule each regressed after being "fixed", and each was caught by eye rather
than by anything systematic. Only rules that can be decided from the text alone belong here;
judgement calls ("is the hook actually about them") are deliberately left to the reader.

A failure is a dict of `code` and `detail`. The code is a stable identifier so failures can be
counted across drafts ("which rule leaks most often?"); the detail is the sentence fed back to the
model on retry. Free text alone would not aggregate -- "Re-uses eCom Central" and "Re-uses Autohub"
are the same rule failing twice.
"""

import re

Failure = dict[str, str]

# Sentence-level dashes only. Hyphens inside compound words (full-stack, human-in-the-loop) are
# fine and must not be flagged, so U+2010/U+2011 are not in this set.
DASH_CHARS = ("—", "–")

BANNED_PHRASES = (
    "hope this finds you well",
    "just checking in",
    "quick question",
    "i noticed your company is growing",
    "i noticed you're doing great things",
    "would love to explore synergies",
    "worth a 15-min demo",
    "i saw you're active on linkedin",
    # The connection_note and outreach_message prompts both instruct against naming a lead detail
    # as a sentence's grammatical subject ("your post about X caught my attention") because it is
    # the clearest tell that a detail was picked off a profile and slotted in. That's a prompt rule,
    # and prompt rules leak, so its sharpest surface forms are enforced here too.
    "caught my attention",
    "caught my eye",
    "stood out to me",
)

MAX_MESSAGE_WORDS = 100
MAX_CONNECTION_NOTE_CHARS = 300

# Cold-email rules, from _internal/Client_Acquisition_Plan.md's Cold Outreach Playbook (Step 5):
# HubSpot's 40M-email study found 50-125 words outperforms both shorter and longer, and a subject
# under 50 characters lifts open rates. These are stricter/different from the LinkedIn message rules
# above on purpose -- email is a different medium with different norms, not the same check reused.
MIN_EMAIL_WORDS = 50
MAX_EMAIL_WORDS = 125
MAX_EMAIL_SUBJECT_CHARS = 50

# Banned phrases specific to cold email, from the same playbook. Checked in addition to the shared
# BANNED_PHRASES above, which still apply (a dash is still a dash, "just checking in" is still dead).
EMAIL_BANNED_PHRASES = (
    "i hope this email finds you well",
    "just following up",
    "please find attached",
    "we'd love to schedule a call",
    "my name is",  # the playbook: "don't introduce yourself, they don't know you and don't care yet"
)

_PROJECT_HEADING = re.compile(r"^## (.+)$", re.M)
_EMPLOYER_LINE = re.compile(r"^Employer: (.+)$", re.M)


def _fail(code: str, detail: str) -> Failure:
    return {"code": code, "detail": detail}


def parse_catalogue(projects_text: str) -> dict[str, str | None]:
    """Maps project name -> employer, or None where the catalogue says the employer isn't stated.

    Parsed rather than hardcoded so the catalogue stays the single source of truth: adding a
    project to projects.md is enough, no code change needed.
    """
    projects: dict[str, str | None] = {}
    for section in projects_text.split("\n## ")[1:]:
        name = section.split("\n", 1)[0].strip()
        employer_match = _EMPLOYER_LINE.search(section)
        employer = employer_match.group(1).strip() if employer_match else None
        if employer and employer.lower().startswith("not stated"):
            employer = None
        # "DeveloperTag (agentic AI workflows for client products)" must compare equal to the
        # "DeveloperTag" a message actually writes, so drop the parenthetical gloss.
        if employer:
            employer = employer.split("(")[0].strip()
        projects[name] = employer
    return projects


def _projects_mentioned(body: str, projects: dict[str, str | None]) -> list[str]:
    # Word boundaries, not substrings: "STL" is a real project name and a substring of "castle",
    # "hustle" and "nestled", which would otherwise produce confident nonsense.
    return [name for name in projects if re.search(rf"\b{re.escape(name)}\b", body, re.IGNORECASE)]


PORTFOLIO_URL = "hassanmehmood.online"


def check_message(
    body: str,
    *,
    projects_text: str = "",
    previous_me_messages: tuple[str, ...] = (),
    is_soft_close: bool = False,
    max_words: int = MAX_MESSAGE_WORDS,
    check_repeated_project: bool = True,
) -> list[Failure]:
    """Returns one failure per broken rule, empty when the draft is clean."""
    failures: list[Failure] = []
    lowered = body.lower()

    found_dashes = [d for d in DASH_CHARS if d in body]
    if found_dashes:
        failures.append(
            _fail(
                "dash",
                f"Contains {' and '.join(found_dashes)} used as punctuation. Rewrite with a comma, "
                "a full stop, or two shorter sentences. Hyphenated words are fine.",
            )
        )

    words = len(body.split())
    if words > max_words:
        failures.append(
            _fail("too_long", f"{words} words, over the {max_words}-word limit. Cut it back.")
        )

    if "github" in lowered:
        failures.append(
            _fail("repo_link", "Mentions GitHub or links a repository. Point at the portfolio instead.")
        )

    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            failures.append(_fail("banned_phrase", f'Uses the banned phrase "{phrase}".'))

    # They already have the link. Re-sending it every message is the clearest sign nobody read the
    # conversation, and it is what makes a thread feel like a loop rather than an exchange.
    if PORTFOLIO_URL in lowered and any(PORTFOLIO_URL in prior.lower() for prior in previous_me_messages):
        failures.append(
            _fail(
                "repeated_portfolio",
                "Sends the portfolio link again, but it is already earlier in this conversation. "
                "Drop it.",
            )
        )

    projects = parse_catalogue(projects_text) if projects_text else {}
    mentioned = _projects_mentioned(body, projects)

    if is_soft_close:
        # The close is the one message that sells nothing and asks nothing.
        if "?" in body:
            failures.append(
                _fail("soft_close_question", "This is the soft close, so it must not ask a question.")
            )
        if mentioned:
            failures.append(
                _fail(
                    "soft_close_project",
                    f"This is the soft close, so it must not name a project (found: {', '.join(mentioned)}).",
                )
            )
    elif check_repeated_project:
        # Off for replies: if they asked about a project by name, naming it back is the correct
        # answer, not a repetition. It stays on for staged messages, where recycling material is
        # exactly what makes a follow-up feel like a resend.
        already_used = [
            name
            for name in mentioned
            if any(name.lower() in prior.lower() for prior in previous_me_messages)
        ]
        if already_used:
            failures.append(
                _fail(
                    "repeated_project",
                    f"Re-uses {', '.join(already_used)}, already mentioned earlier in this thread. "
                    "Pick a different project.",
                )
            )

    # Attribution: only decidable when exactly one project and one employer are named, which is
    # the shape every real mis-attribution took ("At DeveloperTag I built Guard XP").
    employers = {e for e in projects.values() if e}
    named_employers = [e for e in employers if e.lower() in lowered]
    if len(mentioned) == 1 and len(named_employers) == 1:
        project, claimed = mentioned[0], named_employers[0]
        actual = projects[project]
        if actual is None:
            failures.append(
                _fail(
                    "invented_employer",
                    f"Attributes {project} to {claimed}, but the catalogue lists no employer for it. "
                    "Name the project on its own.",
                )
            )
        elif actual.lower() != claimed.lower():
            failures.append(
                _fail(
                    "wrong_employer",
                    f"Attributes {project} to {claimed}, but the catalogue says {actual}.",
                )
            )

    return failures


def check_connection_note(body: str) -> list[Failure]:
    failures: list[Failure] = []
    if any(d in body for d in DASH_CHARS):
        failures.append(
            _fail("dash", "Contains a dash used as punctuation. Use a comma or a full stop.")
        )
    if len(body) > MAX_CONNECTION_NOTE_CHARS:
        failures.append(
            _fail(
                "note_too_long",
                f"{len(body)} characters, over LinkedIn's ~{MAX_CONNECTION_NOTE_CHARS}-character "
                "limit for connection notes.",
            )
        )
    lowered = body.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            failures.append(_fail("banned_phrase", f'Uses the banned phrase "{phrase}".'))
    if "github" in lowered:
        failures.append(_fail("repo_link", "Mentions GitHub. A connection note carries no links."))
    return failures


def check_email(subject: str, body: str) -> list[Failure]:
    """Checks a cold email against _internal/Client_Acquisition_Plan.md's Cold Outreach Playbook.

    A different word-count band and a different banned-phrase list from the LinkedIn checks above,
    deliberately: email is a different medium with its own norms (a subject line, a longer body,
    its own set of phrases that read as mass-sent), not the same rules reused for a second channel.
    """
    failures: list[Failure] = []
    combined_lower = f"{subject}\n{body}".lower()

    if any(d in subject or d in body for d in DASH_CHARS):
        failures.append(
            _fail("dash", "Contains a dash used as punctuation. Use a comma or a full stop.")
        )

    if len(subject) > MAX_EMAIL_SUBJECT_CHARS:
        failures.append(
            _fail(
                "subject_too_long",
                f"Subject is {len(subject)} characters, over the {MAX_EMAIL_SUBJECT_CHARS}-character "
                "limit. Shorten it.",
            )
        )

    words = len(body.split())
    if words < MIN_EMAIL_WORDS:
        failures.append(
            _fail("too_short", f"Body is {words} words, under the {MIN_EMAIL_WORDS}-word floor. Say more.")
        )
    elif words > MAX_EMAIL_WORDS:
        failures.append(
            _fail("too_long", f"Body is {words} words, over the {MAX_EMAIL_WORDS}-word limit. Cut it back.")
        )

    for phrase in (*BANNED_PHRASES, *EMAIL_BANNED_PHRASES):
        if phrase in combined_lower:
            failures.append(_fail("banned_phrase", f'Uses the banned phrase "{phrase}".'))

    if "github" in combined_lower:
        failures.append(_fail("repo_link", "Mentions GitHub. Point at the portfolio instead."))

    # The real signature (name, positioning, portfolio, LinkedIn) is appended in code after this
    # check runs -- see _format_email in app/services/outreach.py. A stray sign-off here would
    # duplicate the name right before that block. Backstop for the same reason every other banned
    # phrase here is: the prompt already says not to, and prompt rules leak.
    last_line = next((line.strip() for line in reversed(body.splitlines()) if line.strip()), "")
    if re.match(r"^(hassan( mehmood)?|best,?|regards,?|thanks,?|cheers,?)$", last_line, re.IGNORECASE):
        failures.append(
            _fail(
                "stray_signoff",
                f'Ends with "{last_line}", a sign-off the model shouldn\'t write -- the real signature '
                "is appended automatically. Remove that line.",
            )
        )

    return failures
