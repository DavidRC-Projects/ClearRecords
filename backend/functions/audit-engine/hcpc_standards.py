"""
HCPC Record-Keeping Standards Definitions
This module defines the standards against which clinical notes are audited.
All checks are rules-based and deterministic (no ML/AI).
"""

# HCPC Standards Reference
HCPC_STANDARDS = {
    'identification': {
        'standard': 'HCPC Standard 10.1',
        'description': 'Records must include clear identification of the registrant, patient, and date/time',
        'required_elements': ['date', 'practitioner_identifier', 'patient_identifier'],
        'guidance': 'Records should clearly identify who made the entry, for whom, and when'
    },
    'structure': {
        'standard': 'HCPC Standard 10.2',
        'description': 'Records must be clear, well-organised, and structured',
        'required_sections': ['subjective', 'objective', 'assessment', 'plan'],
        'guidance': 'Records should be structured in a way that supports understanding and continuity of care'
    },
    'objectivity': {
        'standard': 'HCPC Standard 10.3',
        'description': 'Records must be factual, objective, and non-judgmental',
        'prohibited_language': ['judgmental', 'emotive', 'speculative_in_objective'],
        'guidance': 'Records should contain factual observations and avoid subjective judgments or emotive language'
    },
    'reasoning': {
        'standard': 'HCPC Standard 10.4',
        'description': 'Records must show clear clinical reasoning and rationale',
        'required_elements': ['assessment_section', 'rationale_language', 'findings_to_plan_link'],
        'guidance': 'Clinical reasoning should be transparent, showing how findings inform the treatment plan'
    },
    'plan': {
        'standard': 'HCPC Standard 10.5',
        'description': 'Records must include clear treatment plan and follow-up arrangements',
        'required_elements': ['treatment_plan', 'home_exercise_advice', 'follow_up'],
        'guidance': 'Treatment plans should be specific, actionable, and include arrangements for review or follow-up'
    },
    'timeliness': {
        'standard': 'HCPC Standard 10.6',
        'description': 'Records must be made contemporaneously or as soon as practicable',
        'required_elements': ['timestamp', 'contemporaneous_marking'],
        'guidance': 'Records should be made at the time of, or as soon as possible after, the event or intervention'
    },
    'completeness': {
        'standard': 'HCPC Standard 10.7',
        'description': 'Records must be complete and include all relevant information',
        'required_elements': ['relevant_findings', 'interventions_documented', 'outcomes_measured'],
        'guidance': 'Records should include all relevant clinical findings, interventions provided, and outcomes measured'
    },
    'amendments': {
        'standard': 'HCPC Standard 10.8',
        'description': 'Amendments must be clearly marked, dated, and signed',
        'required_elements': ['amendment_marked', 'amendment_dated', 'amendment_signed'],
        'guidance': 'Any amendments or corrections should be clearly marked with date, time, and signature'
    },
    'confidentiality': {
        'standard': 'HCPC Standard 2.5',
        'description': 'Records must maintain confidentiality and data protection standards',
        'required_elements': ['no_unauthorised_disclosure', 'appropriate_access_controls'],
        'guidance': 'Records should be kept securely and only accessible to authorised personnel'
    },
    'consent': {
        'standard': 'HCPC Standard 1.3',
        'description': 'Consent should be documented where relevant',
        'required_elements': ['consent_documented', 'capacity_assessed'],
        'guidance': 'Where consent is required, it should be clearly documented in the record'
    },
    'risk_assessment': {
        'standard': 'HCPC Standard 10.9',
        'description': 'Risk assessments and safety considerations should be documented',
        'required_elements': ['risks_identified', 'safety_measures_documented'],
        'guidance': 'Where risks are identified, appropriate safety measures and precautions should be documented'
    },
    'outcome_measures': {
        'standard': 'HCPC Standard 10.10',
        'description': 'Outcome measures and progress should be documented',
        'required_elements': ['baseline_measures', 'progress_documented', 'outcome_measures'],
        'guidance': 'Records should include baseline measures, progress tracking, and outcome measures where applicable'
    }
}

# Common SOAP section keywords
SOAP_KEYWORDS = {
    'subjective': [
        'subjective', 's:', 's -', 's.', 'history', 'patient reports', 'patient states',
        'patient says', 'complains of', 'chief complaint', 'presenting complaint'
    ],
    'objective': [
        'objective', 'o:', 'o -', 'o.', 'findings', 'examination', 'observed', 'measured',
        'clinical findings', 'physical examination', 'assessment findings', 'objective findings'
    ],
    'assessment': [
        'assessment', 'a:', 'a -', 'a.', 'impression', 'clinical reasoning', 'diagnosis',
        'clinical impression', 'analysis', 'interpretation', 'clinical opinion'
    ],
    'plan': [
        'plan', 'p:', 'p -', 'p.', 'treatment', 'intervention', 'follow-up', 'follow up',
        'treatment plan', 'management plan', 'action plan', 'next steps'
    ]
}

# Language patterns to flag
JUDGMENTAL_LANGUAGE = [
    'lazy', 'uncooperative', 'difficult', 'non-compliant', 'refuses',
    'stubborn', 'demanding', 'aggressive', 'rude', 'unwilling',
    'non-adherent', 'resistant', 'defensive', 'argumentative'
]

EMOTIVE_LANGUAGE = [
    'frustrating', 'annoying', 'disappointing', 'wonderful', 'amazing',
    'terrible', 'awful', 'horrible', 'fantastic', 'brilliant',
    'shocking', 'devastating', 'heartbreaking', 'incredible'
]

SPECULATIVE_PATTERNS = [
    'probably', 'maybe', 'might be', 'could be', 'possibly',
    'seems like', 'appears to be', 'looks like', 'perhaps',
    'presumably', 'likely', 'unlikely', 'may be', 'might have'
]

RATIONALE_INDICATORS = [
    'suggests', 'consistent with', 'indicates', 'supports',
    'rationale', 'reasoning', 'because', 'due to', 'therefore',
    'as a result', 'consequently', 'hence', 'thus', 'accordingly',
    'demonstrates', 'shows', 'evidence of', 'points to'
]

# Additional language patterns for enhanced auditing
CONSENT_INDICATORS = [
    'consent', 'agreed', 'informed', 'understood', 'explained',
    'permission', 'authorised', 'approved', 'accepted'
]

RISK_INDICATORS = [
    'risk', 'safety', 'precaution', 'contraindication', 'warning',
    'caution', 'hazard', 'concern', 'alert'
]

OUTCOME_MEASURE_INDICATORS = [
    'baseline', 'outcome', 'measure', 'score', 'assessment',
    'progress', 'improvement', 'change', 'result', 'finding',
    'range of motion', 'rom', 'strength', 'pain scale', 'functional',
    'mrc', 'power', 'tool'
]

AMENDMENT_INDICATORS = [
    'amended', 'corrected', 'updated', 'revised', 'changed',
    'alteration', 'modification', 'correction', 'addendum'
]
