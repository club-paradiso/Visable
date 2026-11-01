"""Conservative Korean fact polarity; kept in parity with enforcement-language.js.

Negated and planned events are not completed violations. This module does not
select legal provisions or infer administrative outcomes.
"""
import re

NON_EVENT_PATTERNS = (
    r"[A-H]\s*-?\s*\d{1,2}(?:\s*-\s*\d{1,2})?\s*(?:가|이|는|은)?\s*(?:아니라|아닌|아니에요|아닙니다)",
    r"(?:불법체류|초과\s*체류|오버스테이)\s*(?:은|는|이|가)?\s*(?:아니\w*|아닙니다|안\s*했\w*|하지\s*않\w*)",
    r"체류기간(?:이|은)?\s*(?:아직\s*)?(?:안\s*지났\w*|지나지\s*않\w*|만료되지\s*않\w*)",
    r"(?:허가\s*없이|무허가로?)[^,.!?]{0,45}?(?:일한\s*적(?:은|이)?\s*없\w*|일하지\s*않\w*|근무하지\s*않\w*)",
    r"허가(?:를)?\s*안\s*받은\s*(?:건|것은)\s*아니\w*",
    r"(?:허가\s*없이|무허가로?)[^,.!?]{0,35}?(?:일할|근무할|취업할)\s*(?:예정|계획|생각)\w*",
    r"(?:허가\s*없이|무허가로?)[^,.!?]{0,35}?(?:일하면|근무하면|알바하면|취업하면|일할\s*경우|근무할\s*경우)",
    r"체류기간(?:이|은)?[^,.!?]{0,15}?(?:만료되면|만료될\s*경우)",
)


def factual_text(text: str) -> str:
    for pattern in NON_EVENT_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.I)
    return text


def event_value(text: str, event: str):
    """True for stated events, False for explicit denials, None for plans/unknown.

    Contradictory statements stay unknown rather than selecting the last match.
    """
    values = []
    for clause in re.split(r"[,;!?。！？\n]|(?<=[가-힣])\.|(?:았|었|했)고|지만|그러나", text):
        match = re.search(event, clause)
        if not match:
            continue
        clause = clause[match.end():]
        if re.search(r"안\s*(?:했|받|하|시작|됐)|하지\s*않|받지\s*않|시작되지\s*않|적(?:은|이)?\s*없|아직.*없", clause):
            values.append(False)
        elif re.search(r"예정|계획|생각|하려|할까|하면|되면|[할될]\s*경우|받을|했나요|했는지|여부", clause):
            continue
        else:
            values.append(True)
    return values[0] if values and all(v == values[0] for v in values) else None


def relevant_duration_text(text: str) -> str:
    # Residence history and age are not the duration of the reported violation.
    text = re.sub(r"\d+\s*년\s*(?:살았|살고|거주했|거주하|합법적으로\s*체류)[^,.!?]*?(?:고|며|습니다|어요)", " ", text)
    text = re.sub(r"(?:입국한\s*지|입국한지|거주한\s*지)\s*\d+\s*년", " ", text)
    return text
