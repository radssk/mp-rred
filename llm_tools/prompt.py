from __future__ import annotations
from typing import Dict, Any

# ──────────────────────────
# Column names
# ──────────────────────────
COL_REPORT = "report"
COL_PREPROCESSED = "preprocessed_report"

COL_ACC1_JSON  = "accuracy_1"
COL_ACC1_SCORE = "accuracy_1_score"
COL_ACC2_JSON  = "accuracy_2"
COL_ACC2_SCORE = "accuracy_2_score"

# ──────────────────────────
# JSON Schemas
# ──────────────────────────
ERROR_SCHEMA: Dict[str, Any] = {
    "name": "error_report",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "error": {"type": "string"},
            "error_reason": {"type": "string"},
        },
        "required": ["error", "error_reason"],
        "additionalProperties": False,
    },
}

PREPROCESSING_SCHEMA: Dict[str, Any] = {
    "name": "preprocessing",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "findings":   {"type": "string"},
            "impression": {"type": "string"},
        },
        "required": ["findings", "impression"],
        "additionalProperties": False,
    },
}

# ──────────────────────────
# System Prompts
# ──────────────────────────
SYSTEM_PROMPT_PREPROCESS = """
**Tasks**
1. Extract only content belonging to the *Findings* section (detailed observations) and the *Impression* / *Conclusion* / *Opinion* section (diagnostic interpretation).
2. If there is an *Addendum* or *Correction* section:
   - Sentences that amend Findings ⇒ append to Findings.  
   - Sentences that amend the diagnostic interpretation ⇒ append to Impression.  
   - If ambiguous, append to Impression.
   - Also, clearly mark it as "Addendum".
3. Discard every other section (history, technique, timestamps, signatures, headers, billing codes, etc.).
4. Replace every explicit calendar date with the literal token **[DATE]**.
5. Replace PHI with the literal token **[PHI]**.

(Output must follow the JSON schema exactly.)
{"Findings":"~", "Impression":"~"}
If either the Findings or Impression section is missing, set the corresponding value to "N/A".
""".strip()

SYSTEM_PROMPT_ERROR_CHECK = """
**Tasks**
Identify clinically significant errors based on the content within the provided radiology report.

1. Please read through the entire radiology report and understand the clinical scenario.
2. Identify any clinically significant errors in the report.
3. Limit errors to parts identifiable without images:
- Internal factual inconsistencies: Directly conflicting statements within the same radiology reports (e.g., conflicting laterality, measurements).
- Objective misinterpretations: Interpretations clearly and objectively contradicted by  explicit statements in the Findings and Impression sections of the same radiology report.

(Output must follow the JSON schema exactly.)
If no error is found, return the JSON with
"error": "no error", "error_reason": "N/A".
If an error is found, return the JSON with 
"error": "(cite erroneous statement from the report)", "error_reason": "(concise explanation; utilize quotes if necessary)".
""".strip()

SYSTEM_PROMPT_FP_CHECK = """    
You will receive: 'radiology report JSON' and 'candidate error JSON'.

**Tasks**
Decide whether `candidate error JSON` is a TRUE clinically-significant internal error within `radiology report JSON` or a FALSE POSITIVE.

Guidelines to confirm an error:
- Objectivity: A true ERROR must be objectively incorrect, factually contradictory, or undeniably inaccurate.
- Clarity: The error must be so clear and obvious that ALL trained radiologists or medical professionals would unanimously agree it is incorrect.
- Clinical importance, differences in judgment, or disagreements about what should be included in the Impression or Findings DO NOT qualify as errors.
- Only contradictions or inaccuracies explicitly within the radiology report itself can qualify as errors. Differences between the report content and 
  provided clinical information, patient history, or external context must NEVER be considered errors. 

(Output must follow the JSON schema exactly.)
If determined to be a FALSE POSITIVE, return JSON with:
"error": "no error", "error_reason": "N/A".
""".strip()
# ──────────────────────────
# Other constants
# ──────────────────────────
MAX_WORKERS       = 8
REQUEST_TIMEOUT   = 100        # seconds
BATCH_TIMEOUT     = 600        # seconds
RETRY_LIMIT_FIRST = 3
RETRY_LIMIT_SECOND = 2
RETRY_SLEEP       = 1         # seconds

FAILED_CSV        = "failed_requests.csv"
