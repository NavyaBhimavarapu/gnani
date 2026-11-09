"""
VoiceDose - Multi-Lingual Intent Matcher
========================================
This module matches patient voice transcripts against keyword lists
in Telugu, Hindi, Hinglish, and English for three primary intents:
1. 'taken'   : Dose has been consumed.
2. 'not_yet' : Dose has not been taken yet.
3. 'snooze'  : Patient asks to be reminded later.

Design Highlights:
- Negative-Aware Matching: Checks negation phrases (e.g. "nahi liya", "తీసుకోలేదు", "didn't take")
  BEFORE positive keywords to prevent false "taken" matches.
- Multi-Script Support: Handles native Telugu script, Devanagari Hindi,
  Romanized Hinglish, and standard English.
- Contextual Confirmation Speech: Generates polite, elder-friendly spoken
  responses in the selected language for Gnani Timbre TTS.
"""

import re
from typing import Dict, Any, Tuple


# Keyword dictionaries mapped by intent
KEYWORD_DICTIONARY = {
    "snooze": {
        "telugu": [
            "తర్వాత", "తరువాత", "కాసేపటి తర్వాత", "కొద్దిసేపటి తర్వాత",
            "మళ్ళీ చెప్పు", "మళ్ళీ గుర్తు చేయి", "పది నిమిషాలు", "ఆగు",
            "ఆగుము", "స్నూజ్", "కాసేపు ఆగు", "ఇప్పుడు కాదు తర్వాత"
        ],
        "hindi": [
            "बाद में", "थोड़ी देर बाद", "दस मिनट बाद", "फिर से याद दिलाना",
            "रुक जाओ", "बाद में लूंगा", "बाद में लूंगी", "स्नूज़",
            "थोड़ा रुको", "अभी नहीं बाद में", "कुछ देर में"
        ],
        "hinglish": [
            "baad mein", "baad me", "thodi der baad", "thoda ruko",
            "ruk jao", "fir yaad dilana", "phir yaad dilana", "phir se",
            "10 minute baad", "dus minute baad", "later", "snooze",
            "wait karo", "hold on"
        ],
        "english": [
            "snooze", "remind me later", "remind later", "after some time",
            "in 10 minutes", "in ten minutes", "wait", "hold on",
            "give me 5 minutes", "give me ten minutes", "later please",
            "call me later", "ask me later"
        ],
    },
    "not_yet": {
        "telugu": [
            "తీసుకోలేదు", "వేసుకోలేదు", "ఇంకా లేదు", "ఇంకా తీసుకోలేదు",
            "వేయలేదు", "లేదు", "మర్చిపోయాను", "తాగలేదు", "ఇంకా లేదు అండి",
            "తీసుకో లేదు", "వేసుకో లేదు"
        ],
        "hindi": [
            "नहीं ली", "नहीं लिया", "अभी नहीं", "नहीं खाई", "भूल गया",
            "भूल गई", "नहीं ली है", "अभी तक नहीं", "ना", "नहीं",
            "छूट गई", "लेना बाकी है"
        ],
        "hinglish": [
            "nahi liya", "nahi li", "nahi khaya", "nahi khai",
            "abhi nahi", "bhool gaya", "bhool gayi", "not yet",
            "abhi baki hai", "nahi hua", "na", "no"
        ],
        "english": [
            "not yet", "haven't taken", "have not taken", "didn't take",
            "did not take", "no", "not now", "forgot", "haven't",
            "not done", "skipped", "not taken", "still have to take"
        ],
    },
    "taken": {
        "telugu": [
            "వేసుకున్నాను", "వేసుకున్నా", "తీసుకున్నాను", "తీసుకున్నా",
            "తాగేశాను", "మందు వేసుకున్నాను", "అయిపోయింది", "మ్రింగాను",
            "తిన్నాను", "వేసుకున్నాం", "తీసుకున్నాము", "చేశాను", "అవును",
            "తీసుకున్న", "వేసుకున్న", "హా", "తీసుకున్నాను అండి"
        ],
        "hindi": [
            "ले ली", "ले लिया", "खा ली", "खा लिया", "पी ली", "पी लिया",
            "दवाई ले ली", "हां ले ली", "हो गया", "खा चुका", "ले चुका",
            "ले ली है", "खा ली है", "हां", "हाँ"
        ],
        "hinglish": [
            "le liya", "le li", "kha liya", "kha li", "pi liya",
            "ho gaya", "le liya hai", "kha liya hai", "haan le liya",
            "already le liya", "done ho gaya", "yes le liya", "le chuka"
        ],
        "english": [
            "taken", "took", "i took it", "i have taken", "already taken",
            "swallowed", "had it", "done", "yes", "finished", "i did",
            "took my medicine", "all done", "already had it"
        ],
    },
}

# Spoken confirmation templates for Timbre TTS
CONFIRMATION_TEMPLATES = {
    "taken": {
        "te-IN": "చాలా మంచిది అనసూయ గారు! మీరు మందు తీసుకున్నట్లు నేను నమోదు చేశాను. మంచి నీళ్ళు బాగా తాగండి, జాగ్రత్తగా ఉండండి!",
        "hi-IN": "बहुत बढ़िया अनसूया जी! मैंने दर्ज कर लिया है कि आपने दवाई ले ली है। खूब पानी पीजिए और अपना ख्याल रखिए!",
        "en-IN": "Wonderful Anasuya ji! I have recorded that you took your medicine. Stay hydrated and take care!",
    },
    "not_yet": {
        "te-IN": "సరేనండి అనసూయ గారు, దయచేసి ఆలస్యం చేయకుండా ఇప్పుడే మందు వేసుకోండి. ఆరోగ్యమే మహాభాగ్యం!",
        "hi-IN": "कोई बात नहीं अनसूया जी, कृपया इसे अभी पानी के साथ ले लें। आपकी सेहत सबसे पहले है!",
        "en-IN": "Understood Anasuya ji. Please take your medicine right away with some water. Your health is important!",
    },
    "snooze": {
        "te-IN": "సరేనండి అనసూయ గారు, నేను సరిగ్గా పది నిమిషాల తర్వాత మీకు మళ్ళీ గుర్తు చేస్తాను. కాసేపు విశ్రాంతి తీసుకోండి.",
        "hi-IN": "ठीक है अनసూया जी, मैं आपको 10 मिनट बाद फिर से याद दिलाऊंगा। थोड़ा आराम कर लीजिए।",
        "en-IN": "Got it Anasuya ji! I will snooze this reminder and ask you again in 10 minutes. Please relax.",
    },
    "unknown": {
        "te-IN": "నమస్కారం అనసూయ గారు, మీరు చెప్పింది స్పష్టంగా వినబడలేదు. మీరు మందు వేసుకున్నారా లేదా కాసేపటి తర్వాత గుర్తుచేయమంటారా?",
        "hi-IN": "माफ़ कीजिए अनसूया जी, मुझे आवाज़ साफ़ नहीं आई। क्या आपने दवाई ले ली है या बाद में याद दिलाऊं?",
        "en-IN": "I'm sorry Anasuya ji, I couldn't hear clearly. Did you take your medicine, or would you like a reminder later?",
    },
}

# Reminder speech prompts for Timbre TTS
REMINDER_PROMPTS = {
    "te-IN": "నమస్కారం {name} గారు! ఇది మీ {slot} {medicine} {dosage} మందు వేసుకునే సమయం. {instructions}. మీరు మందు తీసుకున్నారా?",
    "hi-IN": "नमस्ते {name} जी! यह आपकी {slot} की दवाई {medicine} {dosage} लेने का समय है। {instructions}। क्या आपने दवाई ले ली है?",
    "en-IN": "Hello {name} ji! It is time for your {slot} medication, {medicine} {dosage}. {instructions}. Have you taken your medicine?",
}

SLOT_TRANSLATIONS = {
    "te-IN": {"Morning": "ఉదయం", "Afternoon": "మధ్యాహ్నం", "Evening": "సాయంత్రం", "Night": "రాత్రి"},
    "hi-IN": {"Morning": "सुबह", "Afternoon": "दोपहर", "Evening": "शाम", "Night": "रात"},
    "en-IN": {"Morning": "Morning", "Afternoon": "Afternoon", "Evening": "Evening", "Night": "Night"},
}


def normalize_text(text: str) -> str:
    """Normalize text by lowering case and stripping extra punctuation."""
    if not text:
        return ""
    cleaned = text.lower().strip()
    # Strip common punctuation but keep letters/numbers across Indic and Latin scripts
    cleaned = re.sub(r"[?!.,;:\"'()\-_/]", " ", cleaned)
    return " ".join(cleaned.split())


def match_intent(transcript: str, language_code: str = "te-IN") -> Dict[str, Any]:
    """
    Match spoken transcript against keyword sets across Telugu, Hindi, Hinglish, and English.

    Precedence order:
    1. 'snooze'  - If user explicitly requests delay/snooze/later.
    2. 'not_yet' - If user explicitly says not yet / forgot / did not take (checks negations first).
    3. 'taken'   - If user confirms consumption.
    4. 'unknown' - If no matching keywords detected.

    Returns:
        Dict containing:
            - intent: 'taken' | 'not_yet' | 'snooze' | 'unknown'
            - matched_keyword: The matched phrase or None
            - confidence: float score (1.0 for exact/substring match)
            - explanation: Human-readable explanation of match
    """
    norm = normalize_text(transcript)
    if not norm:
        return {
            "intent": "unknown",
            "matched_keyword": None,
            "confidence": 0.0,
            "explanation": "Empty transcript received.",
        }

    # Helper function to check category against keywords
    def find_match_in_intent(intent_name: str) -> Tuple[bool, str]:
        categories = KEYWORD_DICTIONARY[intent_name]
        for lang_family, words in categories.items():
            for kw in words:
                norm_kw = normalize_text(kw)
                # Word boundary or substring check
                if norm_kw in norm:
                    return True, kw
        return False, ""

    # Step 1: Check Snooze first
    snooze_found, kw_snooze = find_match_in_intent("snooze")
    if snooze_found:
        return {
            "intent": "snooze",
            "matched_keyword": kw_snooze,
            "confidence": 0.95,
            "explanation": f"Matched snooze keyword: '{kw_snooze}'",
        }

    # Step 2: Check Not Yet (negations) BEFORE Taken
    not_yet_found, kw_not_yet = find_match_in_intent("not_yet")
    if not_yet_found:
        return {
            "intent": "not_yet",
            "matched_keyword": kw_not_yet,
            "confidence": 0.95,
            "explanation": f"Matched not-yet keyword: '{kw_not_yet}'",
        }

    # Step 3: Check Taken
    taken_found, kw_taken = find_match_in_intent("taken")
    if taken_found:
        return {
            "intent": "taken",
            "matched_keyword": kw_taken,
            "confidence": 0.95,
            "explanation": f"Matched confirmation keyword: '{kw_taken}'",
        }

    return {
        "intent": "unknown",
        "matched_keyword": None,
        "confidence": 0.3,
        "explanation": "No confident keyword match found in transcript.",
    }


def get_confirmation_text(intent: str, language_code: str = "te-IN") -> str:
    """Retrieve localized confirmation text to speak back using Timbre TTS."""
    lang_templates = CONFIRMATION_TEMPLATES.get(intent, CONFIRMATION_TEMPLATES["unknown"])
    return lang_templates.get(language_code, lang_templates.get("en-IN", ""))


def generate_reminder_text(
    patient_name: str,
    slot_name: str,
    medicine_name: str,
    dosage: str,
    instructions: str,
    language_code: str = "te-IN",
) -> str:
    """Format the reminder message spoken aloud to the elder."""
    tmpl = REMINDER_PROMPTS.get(language_code, REMINDER_PROMPTS["en-IN"])
    slot_map = SLOT_TRANSLATIONS.get(language_code, SLOT_TRANSLATIONS["en-IN"])
    translated_slot = slot_map.get(slot_name, slot_name)

    return tmpl.format(
        name=patient_name,
        slot=translated_slot,
        medicine=medicine_name,
        dosage=dosage,
        instructions=instructions,
    )
