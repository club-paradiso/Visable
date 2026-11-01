'use strict';
// Fact-polarity parity with backend/services/enforcement_language.py.
const NON_EVENT_PATTERNS = [
  /[A-H]\s*-?\s*\d{1,2}(?:\s*-\s*\d{1,2})?\s*(?:가|이|는|은)?\s*(?:아니라|아닌|아니에요|아닙니다)/gi,
  /(?:불법체류|초과\s*체류|오버스테이)\s*(?:은|는|이|가)?\s*(?:아니[가-힣]*|아닙니다|안\s*했[가-힣]*|하지\s*않[가-힣]*)/gi,
  /체류기간(?:이|은)?\s*(?:아직\s*)?(?:안\s*지났[가-힣]*|지나지\s*않[가-힣]*|만료되지\s*않[가-힣]*)/gi,
  /(?:허가\s*없이|무허가로?)[^,.!?]{0,45}?(?:일한\s*적(?:은|이)?\s*없[가-힣]*|일하지\s*않[가-힣]*|근무하지\s*않[가-힣]*)/gi,
  /허가(?:를)?\s*안\s*받은\s*(?:건|것은)\s*아니[가-힣]*/gi,
  /(?:허가\s*없이|무허가로?)[^,.!?]{0,35}?(?:일할|근무할|취업할)\s*(?:예정|계획|생각)[가-힣]*/gi,
  /(?:허가\s*없이|무허가로?)[^,.!?]{0,35}?(?:일하면|근무하면|알바하면|취업하면|일할\s*경우|근무할\s*경우)/gi,
  /체류기간(?:이|은)?[^,.!?]{0,15}?(?:만료되면|만료될\s*경우)/gi,
];
function factualText(text) {
  for (const pattern of NON_EVENT_PATTERNS) text = text.replace(pattern, ' ');
  return text;
}
function eventValue(text, event) {
  const values = [];
  for (let clause of text.split(/[,;!?。！？\n]|(?<=[가-힣])\.|(?:았|었|했)고|지만|그러나/)) {
    const match = clause.match(event);
    if (!match) continue;
    clause = clause.slice(match.index + match[0].length);
    if (/안\s*(?:했|받|하|시작|됐)|하지\s*않|받지\s*않|시작되지\s*않|적(?:은|이)?\s*없|아직.*없/.test(clause)) values.push(false);
    else if (!/예정|계획|생각|하려|할까|하면|되면|[할될]\s*경우|받을|했나요|했는지|여부/.test(clause)) values.push(true);
  }
  return values.length && values.every((v) => v === values[0]) ? values[0] : null;
}
function relevantDurationText(text) {
  return text.replace(/\d+\s*년\s*(?:살았|살고|거주했|거주하|합법적으로\s*체류)[^,.!?]*?(?:고|며|습니다|어요)/g, ' ')
    .replace(/(?:입국한\s*지|입국한지|거주한\s*지)\s*\d+\s*년/g, ' ');
}
module.exports = { factualText, eventValue, relevantDurationText };
