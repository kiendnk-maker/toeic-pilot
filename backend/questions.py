# backend/questions.py
# 30 TOEIC Part 5 questions × 3 parallel sets (pretest / practice / posttest)
# Each question has: id, stem, options[4], correct_idx, explanation
# *keyword* markers in explanations get TTS-readable emphasis + UI highlight

from fastapi import APIRouter, Query

router = APIRouter()

# ── Practice Set (30 questions — daily sessions use Day 1–12 with 10 q/day cycling) ──
PRACTICE = [
    {
        "id": "D1Q01",
        "stem": "The manager asked that all reports ______ submitted by Friday.",
        "options": ["are", "be", "were", "will be"],
        "correct_idx": 1,
        "explanation": "After *asked that*, use *be* (base form, no -s). Pattern: *ask that* + subject + *base verb*. Say it: \"The manager asked that all reports *be* submitted by Friday.\"",
    },
    {
        "id": "D1Q02",
        "stem": "Neither the director nor the employees ______ aware of the change.",
        "options": ["was", "were", "are being", "have been"],
        "correct_idx": 1,
        "explanation": "*Neither...nor* matches the verb to the closer noun. \"Employees\" is plural → *were*. Say it: \"Neither the director nor the employees *were* aware.\"",
    },
    {
        "id": "D1Q03",
        "stem": "The conference, which ______ for three days, attracted over 500 participants.",
        "options": ["lasts", "lasted", "has lasted", "lasting"],
        "correct_idx": 1,
        "explanation": "\"Attracted\" is past tense, so the *which* clause also needs past. *Lasted*. Say it: \"The conference, which *lasted* for three days.\"",
    },
    {
        "id": "D1Q04",
        "stem": "Ms. Chen has been promoted to regional manager, ______ was expected by her colleagues.",
        "options": ["that", "which", "what", "who"],
        "correct_idx": 1,
        "explanation": "A comma before *which* means it refers to the whole sentence — a non-restrictive clause. Use *which*. Say it: \"...promoted to regional manager, *which* was expected.\"",
    },
    {
        "id": "D1Q05",
        "stem": "The shipment will arrive ______ Friday, so please prepare the warehouse.",
        "options": ["at", "on", "in", "by"],
        "correct_idx": 1,
        "explanation": "Use *on* with days of the week. *On Friday* is correct. Say it: \"The shipment will arrive *on* Friday.\"",
    },
    {
        "id": "D1Q06",
        "stem": "If the project ______ on schedule, we will receive a bonus.",
        "options": ["completes", "is completed", "will complete", "completed"],
        "correct_idx": 1,
        "explanation": "First conditional: *If* + present simple, *will* + base verb. The project gets the action → passive. Say it: \"If the project *is completed* on schedule.\"",
    },
    {
        "id": "D1Q07",
        "stem": "The report is due next Monday, so it must ______ by Friday at the latest.",
        "options": ["submit", "be submitted", "submitted", "submitting"],
        "correct_idx": 1,
        "explanation": "After modal *must*, use *be* + past participle. The report gets the action → passive. Say it: \"It must *be submitted* by Friday.\"",
    },
    {
        "id": "D1Q08",
        "stem": "She speaks three languages, ______ English, Mandarin, and Japanese.",
        "options": ["such as", "namely", "for example", "including"],
        "correct_idx": 1,
        "explanation": "*Namely* gives a complete list. *Such as* and *including* suggest there are more. All three are listed → *namely*. Say it: \"Three languages, *namely* English, Mandarin, and Japanese.\"",
    },
    {
        "id": "D1Q09",
        "stem": "The CEO, along with the board members, ______ attending the gala tonight.",
        "options": ["are", "is", "were", "have been"],
        "correct_idx": 1,
        "explanation": "*Along with* does not change the subject. The real subject is \"The CEO\" (singular) → *is*. Say it: \"The CEO, along with the board members, *is* attending.\"",
    },
    {
        "id": "D1Q10",
        "stem": "We recommend that the client ______ a second opinion before signing.",
        "options": ["seeks", "seek", "sought", "seeking"],
        "correct_idx": 1,
        "explanation": "After *recommend that*, use the *base verb* (no -s). Say it: \"We recommend that the client *seek* a second opinion.\"",
    },
    {
        "id": "D2Q01",
        "stem": "The factory has been operating ______ full capacity since last month.",
        "options": ["in", "on", "at", "with"],
        "correct_idx": 2,
        "explanation": "Fixed phrase: *at full capacity*. Use *at* for levels and rates. Say it: \"Operating *at* full capacity.\"",
    },
    {
        "id": "D2Q02",
        "stem": "______ the heavy rain, the outdoor concert will proceed as planned.",
        "options": ["Although", "Despite", "Because of", "In addition to"],
        "correct_idx": 1,
        "explanation": "*Despite* is followed by a noun (no subject-verb). *Although* needs a full clause. Say it: \"*Despite* the heavy rain, the concert will proceed.\"",
    },
    {
        "id": "D2Q03",
        "stem": "The new software is significantly ______ than the previous version.",
        "options": ["fast", "faster", "fastest", "more fast"],
        "correct_idx": 1,
        "explanation": "Short adjectives: add *-er* for comparison. *Fast* → *faster*. Use *more* for words with 3+ syllables. Say it: \"Significantly *faster* than.\"",
    },
    {
        "id": "D2Q04",
        "stem": "All staff members are required ______ the training by the end of the month.",
        "options": ["complete", "completing", "to complete", "completed"],
        "correct_idx": 2,
        "explanation": "*Required to* is always followed by *base verb*. Pattern: *required to* + *base verb*. Say it: \"Are required *to complete* the training.\"",
    },
    {
        "id": "D2Q05",
        "stem": "There ______ several issues that need to be addressed before the launch.",
        "options": ["is", "are", "has been", "seems to be"],
        "correct_idx": 1,
        "explanation": "*There* is not the subject. Match the verb to the noun after *there*. \"issues\" → plural → *are*. Say it: \"There *are* several issues.\"",
    },
    {
        "id": "D2Q06",
        "stem": "The invoice must be paid within 30 days ______ the date of issue.",
        "options": ["from", "of", "since", "after"],
        "correct_idx": 1,
        "explanation": "Fixed phrase: *within X days of*. *Of* marks the starting point. Say it: \"Within 30 days *of* the date of issue.\"",
    },
    {
        "id": "D2Q07",
        "stem": "Hardly ______ the meeting started when the fire alarm went off.",
        "options": ["has", "had", "did", "was"],
        "correct_idx": 1,
        "explanation": "*Hardly* inverts the verb order. Pattern: *Hardly had* + subject + past participle. Say it: \"*Hardly had* the meeting started.\"",
    },
    {
        "id": "D2Q08",
        "stem": "The marketing team suggested that the campaign ______ to a younger demographic.",
        "options": ["targets", "target", "targeted", "targeting"],
        "correct_idx": 1,
        "explanation": "After *suggest that*, use the *base verb* (no -s). Say it: \"The team suggested that the campaign *target* a younger demographic.\"",
    },
    {
        "id": "D2Q09",
        "stem": "Not only ______ the contract, but she also negotiated better terms.",
        "options": ["she signed", "did she sign", "she did sign", "had she signed"],
        "correct_idx": 1,
        "explanation": "*Not only* inverts the verb order. Put the auxiliary before the subject. Say it: \"*Did she sign* the contract.\"",
    },
    {
        "id": "D2Q10",
        "stem": "The building, ______ in 1920, has been designated a historical landmark.",
        "options": ["constructing", "constructed", "constructs", "was constructed"],
        "correct_idx": 1,
        "explanation": "Remove *which was* and keep the past participle. *which was constructed* → *constructed*. This is a reduced relative clause. Say it: \"The building, *constructed* in 1920.\"",
    },
    {
        "id": "D3Q01",
        "stem": "We would appreciate ______ you could send the documents by email.",
        "options": ["if", "it if", "whether", "that"],
        "correct_idx": 1,
        "explanation": "Fixed pattern: *appreciate it if*. You need *it* before *if*. Say it: \"Would appreciate *it if* you could send.\"",
    },
    {
        "id": "D3Q02",
        "stem": "The seminar has been postponed ______ further notice.",
        "options": ["until", "by", "from", "since"],
        "correct_idx": 0,
        "explanation": "Fixed phrase: *until further notice* means until someone gives new information. Say it: \"Postponed *until* further notice.\"",
    },
    {
        "id": "D3Q03",
        "stem": "It is essential that every employee ______ the new safety regulations.",
        "options": ["understands", "understand", "understood", "is understanding"],
        "correct_idx": 1,
        "explanation": "After *essential that*, use the *base verb* (no -s). Say it: \"Essential that every employee *understand* the regulations.\"",
    },
    {
        "id": "D3Q04",
        "stem": "The company's profits have increased by 15% ______ last year.",
        "options": ["comparing to", "compared to", "compare with", "compares to"],
        "correct_idx": 1,
        "explanation": "*Compared to* means \"like\". Use the past participle form. Say it: \"Increased by 15%, *compared to* last year.\"",
    },
    {
        "id": "D3Q05",
        "stem": "Please let me know ______ you need any additional information.",
        "options": ["unless", "if", "whereas", "although"],
        "correct_idx": 1,
        "explanation": "*If* here means \"in case\". \"Let me know *if* you need\" = tell me in case you need help. Say it: \"Let me know *if* you need additional information.\"",
    },
    {
        "id": "D3Q06",
        "stem": "The proposal, along with the budget estimates, ______ under review.",
        "options": ["are", "is", "were", "have been"],
        "correct_idx": 1,
        "explanation": "*Along with* does not make the subject plural. The subject is \"The proposal\" → singular → *is*. Say it: \"The proposal, along with the budget estimates, *is* under review.\"",
    },
    {
        "id": "D3Q07",
        "stem": "______ the error was detected early, the project was still delayed by two weeks.",
        "options": ["Because", "Although", "Since", "Unless"],
        "correct_idx": 1,
        "explanation": "*Although* = \"even though\". It shows contrast: found early BUT still delayed. *Because* gives a reason, not a contrast. Say it: \"*Although* the error was detected early.\"",
    },
    {
        "id": "D3Q08",
        "stem": "The presentation will begin promptly at 9 AM; ______, please arrive 15 minutes early.",
        "options": ["therefore", "however", "nevertheless", "accordingly"],
        "correct_idx": 0,
        "explanation": "*Therefore* = \"so\". It shows the result. \"Starts at 9, SO arrive early.\" *However* shows contrast, not result. Say it: \"...at 9 AM; *therefore*, please arrive early.\"",
    },
    {
        "id": "D3Q09",
        "stem": "Nobody in the department ______ willing to work overtime this weekend.",
        "options": ["are", "is", "were", "have been"],
        "correct_idx": 1,
        "explanation": "*Nobody* is always singular. It takes a singular verb. Say it: \"*Nobody* in the department *is* willing.\"",
    },
    {
        "id": "D3Q10",
        "stem": "The policy changes will take ______ starting next Monday.",
        "options": ["affect", "effect", "affective", "effective"],
        "correct_idx": 1,
        "explanation": "Fixed phrase: *take effect* = start working. *Effect* is the noun. *Affect* is a verb meaning \"to change\". Say it: \"Will take *effect* starting Monday.\"",
    },
]

# ── Pretest Set (30 items — parallel form to practice) ──
PRETEST = []
POSTTEST = []


def _generate_parallel_set():
    """
    Generate 30 parallel items by reusing the same grammar points
    with different vocabulary. For real pilot, these should be distinct.
    Here we create minimal variants.
    """
    parallel = []
    for i, q in enumerate(PRACTICE):
        pid = f"PRE{i+1:02d}" if len(parallel) < 30 else f"POST{i+1:02d}"
        p = {
            "id": pid,
            "stem": q["stem"].replace("manager", "supervisor")
            .replace("Friday", "Thursday the latest")
            .replace("500 participants", "450 attendees"),
            "options": q["options"][:],
            "correct_idx": q["correct_idx"],
            "explanation": q["explanation"],
        }
        parallel.append(p)
    return parallel


PRETEST = _generate_parallel_set()
POSTTEST = _generate_parallel_set()
# Rename POST ids
for i, q in enumerate(POSTTEST):
    q["id"] = f"PST{i+1:02d}"

QUESTIONS = {
    "practice": PRACTICE,
    "pretest": PRETEST,
    "posttest": POSTTEST,
}


@router.get("/api/questions")
def get_questions(day: int = Query(1), set: str = Query("practice")):
    """
    Returns 10 questions for a given day + set.
    Day 1–12: cycles through 30 questions, 10/day.
    Test sets (pretest/posttest): returns all 30.
    """
    qs = QUESTIONS.get(set, QUESTIONS["practice"])

    if set in ("pretest", "posttest"):
        # Return all 30 for tests
        return qs

    # Practice: Day 1 → Q1-10, Day 2 → Q11-20, Day 3 → Q21-30, Day 4 → Q1-10, ...
    start = ((day - 1) * 10) % len(qs)
    end = start + 10
    if end > len(qs):
        # Wrap around
        result = qs[start:] + qs[: end - len(qs)]
    else:
        result = qs[start:end]

    return result