"""
Rules-based Audit Engine
Deterministic checks against HCPC standards.
"""

import re
from hcpc_standards import (
    HCPC_STANDARDS, SOAP_KEYWORDS, JUDGMENTAL_LANGUAGE,
    EMOTIVE_LANGUAGE, SPECULATIVE_PATTERNS, RATIONALE_INDICATORS
)

# Security: Maximum text size to prevent memory exhaustion (10MB)
MAX_TEXT_SIZE = 10 * 1024 * 1024


class AuditEngine:
    """
    Rules-based audit engine for clinical documentation
    Audits how things are written, not what was done
    """
    
    def __init__(self):
        """Initialize the audit engine"""
        pass
    
    def audit_document(self, extracted_data):
        """
        Perform comprehensive audit of extracted document data
        
        Args:
            extracted_data: Dictionary containing:
                - text: Full extracted text
                - tables: List of extracted tables
                - forms: List of extracted key-value pairs
        
        Returns:
            Dictionary with audit results including:
                - overall_status: 'pass' | 'needs_improvement' | 'critical_issues'
                - findings: List of audit findings
                - strengths: List of identified strengths
                - recommendations: List of improvement recommendations
        """
        # Security: Validate input
        if not isinstance(extracted_data, dict):
            raise ValueError("extracted_data must be a dictionary")
        
        # Get and validate text
        text_raw = extracted_data.get('text', '')
        if not isinstance(text_raw, str):
            raise ValueError("text must be a string")
        
        # Security: Limit text size to prevent memory exhaustion
        if len(text_raw) > MAX_TEXT_SIZE:
            raise ValueError(f"Text size exceeds maximum allowed size of {MAX_TEXT_SIZE} bytes")
        
        # Convert to lowercase once (performance optimization)
        text = text_raw.lower()
        
        # Note: tables and forms are extracted but not currently used in audit checks
        # They are kept for potential future enhancements
        tables = extracted_data.get('tables', [])
        forms = extracted_data.get('forms', [])
        
        findings = []
        strengths = []
        
        # Run all audit checks
        findings.extend(self._check_identification(text, forms))
        findings.extend(self._check_structure(text))
        findings.extend(self._check_objectivity(text))
        findings.extend(self._check_reasoning(text))
        findings.extend(self._check_plan(text))
        findings.extend(self._check_timeliness(text, forms))
        
        # Identify strengths
        strengths = self._identify_strengths(text, findings)
        
        # Determine overall status
        critical_count = sum(1 for f in findings if f.get('severity') == 'critical')
        warning_count = sum(1 for f in findings if f.get('severity') == 'warning')
        
        if critical_count > 0:
            overall_status = 'critical_issues'
        elif warning_count > 2:
            overall_status = 'needs_improvement'
        else:
            overall_status = 'pass'
        
        # Generate recommendations
        recommendations = self._generate_recommendations(findings)
        
        return {
            'overall_status': overall_status,
            'findings': findings,
            'strengths': strengths,
            'recommendations': recommendations,
            'summary': {
                'total_findings': len(findings),
                'critical_issues': critical_count,
                'warnings': warning_count,
                'strengths_count': len(strengths)
            }
        }
    
    def _check_identification(self, text, forms):
        """
        Check for required identification elements
        
        Args:
            text: Lowercase text to check
            forms: List of extracted forms (currently unused, reserved for future use)
        """
        findings = []
        
        # Check for date
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # DD/MM/YYYY or DD-MM-YYYY
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',    # YYYY/MM/DD
            r'\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4}',  # DD Month YYYY
        ]
        has_date = any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
        
        if not has_date:
            findings.append({
                'category': 'identification',
                'severity': 'critical',
                'issue': 'Date not clearly identified',
                'hcpc_standard': HCPC_STANDARDS['identification']['standard'],
                'guidance': 'Records must include the date of entry. Consider adding date at the start of the note.',
                'example': 'Date: 15/01/2026'
            })
        
        # Check for time
        time_patterns = [
            r'\d{1,2}:\d{2}',  # HH:MM
            r'\d{1,2}:\d{2}\s*(am|pm)',  # HH:MM AM/PM
        ]
        has_time = any(re.search(pattern, text, re.IGNORECASE) for pattern in time_patterns)
        
        if not has_time:
            findings.append({
                'category': 'identification',
                'severity': 'warning',
                'issue': 'Time not clearly identified',
                'hcpc_standard': HCPC_STANDARDS['identification']['standard'],
                'guidance': 'Including time of entry helps establish contemporaneous record-keeping.',
                'example': 'Time: 14:30'
            })
        
        # Check for practitioner identifier (registration number, initials, etc.)
        practitioner_patterns = [
            r'reg[\.\s]*no[\.\s]*:?\s*\w+',
            r'practitioner[:\s]+\w+',
            r'signed[:\s]+\w+',
            r'by[:\s]+\w+',
        ]
        has_practitioner = any(re.search(pattern, text, re.IGNORECASE) for pattern in practitioner_patterns)
        
        if not has_practitioner:
            findings.append({
                'category': 'identification',
                'severity': 'warning',
                'issue': 'Practitioner identifier not clearly stated',
                'hcpc_standard': HCPC_STANDARDS['identification']['standard'],
                'guidance': 'Records should clearly identify the practitioner making the entry.',
                'example': 'Practitioner: J. Smith (Reg No: PH123456)'
            })
        
        return findings
    
    def _check_structure(self, text):
        """Check for SOAP structure and organisation"""
        findings = []
        
        # Check for SOAP sections
        sections_found = {}
        for section, keywords in SOAP_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    sections_found[section] = True
                    break
        
        # Check for each required section
        required_sections = ['subjective', 'objective', 'assessment', 'plan']
        missing_sections = [s for s in required_sections if s not in sections_found]
        
        if missing_sections:
            findings.append({
                'category': 'structure',
                'severity': 'critical' if len(missing_sections) > 2 else 'warning',
                'issue': f"Missing SOAP sections: {', '.join(missing_sections).title()}",
                'hcpc_standard': HCPC_STANDARDS['structure']['standard'],
                'guidance': 'SOAP structure helps ensure comprehensive documentation. Consider clearly marking each section.',
                'example': 'S: Patient reports...\nO: Examination findings...\nA: Clinical reasoning...\nP: Treatment plan...'
            })
        
        # Check for section clarity (multiple keywords suggest unclear structure)
        section_keyword_counts = {}
        for section, keywords in SOAP_KEYWORDS.items():
            count = sum(1 for keyword in keywords if keyword in text)
            if count > 0:
                section_keyword_counts[section] = count
        
        # Fix: Check if dictionary is not empty before calling max()
        if section_keyword_counts and max(section_keyword_counts.values()) > 3:
            findings.append({
                'category': 'structure',
                'severity': 'warning',
                'issue': 'SOAP sections may not be clearly distinguished',
                'hcpc_standard': HCPC_STANDARDS['structure']['standard'],
                'guidance': 'Consider using clear section headers (S:, O:, A:, P:) to improve structure.',
                'example': 'S: [Subjective content]\nO: [Objective content]'
            })
        
        return findings
    
    def _check_objectivity(self, text):
        """Check for objectivity and professional tone"""
        findings = []
        
        # Check for judgmental language
        judgmental_found = [word for word in JUDGMENTAL_LANGUAGE if word in text]
        if judgmental_found:
            findings.append({
                'category': 'objectivity',
                'severity': 'critical',
                'issue': f'Judgmental language detected: {", ".join(judgmental_found[:3])}',
                'hcpc_standard': HCPC_STANDARDS['objectivity']['standard'],
                'guidance': 'Records should be factual and non-judgmental. Use objective descriptions of behaviour or findings.',
                'example': 'Instead of "uncooperative", consider "patient declined to perform exercise"'
            })
        
        # Check for emotive language
        emotive_found = [word for word in EMOTIVE_LANGUAGE if word in text]
        if emotive_found:
            findings.append({
                'category': 'objectivity',
                'severity': 'warning',
                'issue': f'Emotive language detected: {", ".join(emotive_found[:3])}',
                'hcpc_standard': HCPC_STANDARDS['objectivity']['standard'],
                'guidance': 'Records should maintain professional, objective tone. Avoid emotive language.',
                'example': 'Instead of "frustrating", consider describing the specific challenge objectively'
            })
        
        # Check for speculative language in objective section
        # Look for objective section and check for speculation
        objective_section = self._extract_section(text, 'objective')
        if objective_section:
            speculative_found = [pattern for pattern in SPECULATIVE_PATTERNS if pattern in objective_section]
            if speculative_found:
                findings.append({
                    'category': 'objectivity',
                    'severity': 'warning',
                    'issue': 'Speculative language in objective section',
                    'hcpc_standard': HCPC_STANDARDS['objectivity']['standard'],
                    'guidance': 'Objective sections should contain factual observations only. Move speculation to assessment section.',
                    'example': 'O: "Reduced range of motion" (factual) vs "Probably reduced range" (speculative)'
                })
        
        return findings
    
    def _check_reasoning(self, text):
        """Check for clinical reasoning transparency"""
        findings = []
        
        # Check for assessment section
        has_assessment = any(keyword in text for keyword in SOAP_KEYWORDS['assessment'])
        if not has_assessment:
            findings.append({
                'category': 'reasoning',
                'severity': 'critical',
                'issue': 'Assessment section not clearly identified',
                'hcpc_standard': HCPC_STANDARDS['reasoning']['standard'],
                'guidance': 'Assessment section should document your clinical reasoning and interpretation of findings.',
                'example': 'A: Findings suggest... / Clinical reasoning indicates...'
            })
        else:
            # Check for rationale language in assessment
            assessment_section = self._extract_section(text, 'assessment')
            if assessment_section:
                has_rationale = any(indicator in assessment_section for indicator in RATIONALE_INDICATORS)
                if not has_rationale:
                    findings.append({
                        'category': 'reasoning',
                        'severity': 'warning',
                        'issue': 'Clinical reasoning rationale not clearly stated',
                        'hcpc_standard': HCPC_STANDARDS['reasoning']['standard'],
                        'guidance': 'Assessment should clearly link findings to reasoning. Use phrases like "suggests", "consistent with", "indicates".',
                        'example': 'A: Reduced ROM and pain on movement suggests joint restriction'
                    })
        
        # Check for link between findings and plan
        has_objective = any(keyword in text for keyword in SOAP_KEYWORDS['objective'])
        has_plan = any(keyword in text for keyword in SOAP_KEYWORDS['plan'])
        
        if has_objective and has_plan:
            # Check if plan references findings (basic check)
            objective_section = self._extract_section(text, 'objective')
            plan_section = self._extract_section(text, 'plan')
            
            if objective_section and plan_section:
                # Simple check: do plan and objective share any common clinical terms?
                clinical_terms = ['pain', 'range', 'movement', 'strength', 'function', 'exercise']
                objective_terms = [term for term in clinical_terms if term in objective_section]
                plan_terms = [term for term in clinical_terms if term in plan_section]
                
                if not (objective_terms and plan_terms):
                    findings.append({
                        'category': 'reasoning',
                        'severity': 'warning',
                        'issue': 'Plan may not clearly link to objective findings',
                        'hcpc_standard': HCPC_STANDARDS['reasoning']['standard'],
                        'guidance': 'Treatment plan should clearly relate to objective findings documented.',
                        'example': 'If O: notes "reduced ROM", P: should address ROM improvement'
                    })
        
        return findings
    
    def _check_plan(self, text):
        """Check for treatment plan and follow-up"""
        findings = []
        
        # Check for plan section
        has_plan = any(keyword in text for keyword in SOAP_KEYWORDS['plan'])
        if not has_plan:
            findings.append({
                'category': 'plan',
                'severity': 'critical',
                'issue': 'Treatment plan section not clearly identified',
                'hcpc_standard': HCPC_STANDARDS['plan']['standard'],
                'guidance': 'Records must include a clear treatment plan or intervention plan.',
                'example': 'P: Continue exercises, review in 2 weeks'
            })
        else:
            plan_section = self._extract_section(text, 'plan')
            if plan_section:
                # Check for home exercise/advice
                home_exercise_keywords = ['home exercise', 'home programme', 'advice', 'self-management', 'home care']
                has_home_exercise = any(keyword in plan_section for keyword in home_exercise_keywords)
                
                if not has_home_exercise:
                    findings.append({
                        'category': 'plan',
                        'severity': 'warning',
                        'issue': 'Home exercise or self-management advice not clearly documented',
                        'hcpc_standard': HCPC_STANDARDS['plan']['standard'],
                        'guidance': 'Consider documenting any advice or exercises given for patient self-management.',
                        'example': 'P: Home exercises: [specific exercises], Review in 2 weeks'
                    })
                
                # Check for follow-up
                follow_up_keywords = ['follow-up', 'follow up', 'review', 'next appointment', 'return']
                has_follow_up = any(keyword in plan_section for keyword in follow_up_keywords)
                
                if not has_follow_up:
                    findings.append({
                        'category': 'plan',
                        'severity': 'warning',
                        'issue': 'Follow-up or review plan not clearly stated',
                        'hcpc_standard': HCPC_STANDARDS['plan']['standard'],
                        'guidance': 'Records should indicate when review or follow-up is planned.',
                        'example': 'P: Review in 2 weeks / Follow-up: Next appointment scheduled'
                    })
        
        return findings
    
    def _check_timeliness(self, text, forms):
        """
        Check for timeliness indicators
        
        Args:
            text: Lowercase text to check
            forms: List of extracted forms (currently unused, reserved for future use)
        """
        findings = []
        
        # Check for timestamp (already checked in identification, but more detailed here)
        timestamp_patterns = [
            r'\d{1,2}:\d{2}',  # Time
            r'\d{1,2}:\d{2}\s*(am|pm)',
        ]
        has_timestamp = any(re.search(pattern, text, re.IGNORECASE) for pattern in timestamp_patterns)
        
        if not has_timestamp:
            findings.append({
                'category': 'timeliness',
                'severity': 'warning',
                'issue': 'Timestamp not clearly recorded',
                'hcpc_standard': HCPC_STANDARDS['timeliness']['standard'],
                'guidance': 'Including time helps demonstrate contemporaneous record-keeping.',
                'example': 'Date: 15/01/2024, Time: 14:30'
            })
        
        # Check for amendment markers (words suggesting later addition)
        amendment_keywords = ['amended', 'added later', 'correction', 'updated']
        has_amendment_markers = any(keyword in text for keyword in amendment_keywords)
        
        if has_amendment_markers:
            # Check if amendment is clearly marked
            # Fix: Store find result to avoid calling twice and handle -1 case
            # Check all occurrences of 'amended' (though typically there's only one)
            amended_idx = text.find('amended')
            if amended_idx != -1:
                # Check 50 characters after 'amended' for date indicator
                # Security: Prevent index out of bounds
                end_idx = min(amended_idx + 50, len(text))
                check_region = text[amended_idx:end_idx]
                if 'date' not in check_region:
                    # Also check for date patterns in the region
                    date_in_region = any(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', check_region) or
                                        re.search(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', check_region))
                    if not date_in_region:
                        findings.append({
                            'category': 'timeliness',
                            'severity': 'warning',
                            'issue': 'Amendment may not be clearly dated',
                            'hcpc_standard': HCPC_STANDARDS['timeliness']['standard'],
                            'guidance': 'Amendments should be clearly marked with date and time of amendment.',
                            'example': 'Amended 16/01/2024 10:00: [correction details]'
                        })
        
        return findings
    
    def _extract_section(self, text, section_name):
        """Extract a specific SOAP section from text"""
        keywords = SOAP_KEYWORDS.get(section_name, [])
        
        for keyword in keywords:
            if keyword in text:
                # Try to find section boundaries
                start_idx = text.find(keyword)
                if start_idx != -1:
                    # Look for next section or end of text
                    remaining_text = text[start_idx:]
                    
                    # Find next section marker
                    next_section_idx = len(remaining_text)
                    for other_section, other_keywords in SOAP_KEYWORDS.items():
                        if other_section != section_name:
                            for other_keyword in other_keywords:
                                idx = remaining_text.find(other_keyword, len(keyword))
                                if idx != -1 and idx < next_section_idx:
                                    next_section_idx = idx
                    
                    # Security: Limit section size to prevent memory issues
                    # If section is extremely long, truncate it
                    max_section_size = 50000  # 50KB max per section
                    section_text = remaining_text[:next_section_idx].strip()
                    if len(section_text) > max_section_size:
                        section_text = section_text[:max_section_size]
                    return section_text
        
        return None
    
    def _identify_strengths(self, text, findings):
        """Identify positive aspects of the documentation"""
        strengths = []
        
        # Check for comprehensive SOAP structure
        sections_found = sum(1 for section in SOAP_KEYWORDS.keys() 
                           if any(kw in text for kw in SOAP_KEYWORDS[section]))
        if sections_found == 4:
            strengths.append({
                'aspect': 'Structure',
                'description': 'Complete SOAP structure identified',
                'benefit': 'Clear organisation supports comprehensive documentation'
            })
        
        # Check for rationale language
        if any(indicator in text for indicator in RATIONALE_INDICATORS):
            strengths.append({
                'aspect': 'Clinical Reasoning',
                'description': 'Clear rationale language used',
                'benefit': 'Demonstrates transparent clinical reasoning'
            })
        
        # Check for professional tone (no judgmental/emotive language)
        has_judgmental = any(word in text for word in JUDGMENTAL_LANGUAGE)
        has_emotive = any(word in text for word in EMOTIVE_LANGUAGE)
        if not has_judgmental and not has_emotive:
            strengths.append({
                'aspect': 'Professional Tone',
                'description': 'Objective, professional language maintained',
                'benefit': 'Records maintain appropriate professional standards'
            })
        
        return strengths
    
    def _generate_recommendations(self, findings):
        """Generate actionable recommendations based on findings"""
        recommendations = []
        
        # Group findings by category
        by_category = {}
        for finding in findings:
            category = finding.get('category', 'other')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(finding)
        
        # Generate category-specific recommendations
        if 'identification' in by_category:
            recommendations.append({
                'priority': 'high',
                'category': 'Identification',
                'action': 'Ensure all notes include date, time, and practitioner identifier at minimum',
                'reference': HCPC_STANDARDS['identification']['standard']
            })
        
        if 'structure' in by_category:
            recommendations.append({
                'priority': 'high',
                'category': 'Structure',
                'action': 'Use clear SOAP section headers (S:, O:, A:, P:) to improve organisation',
                'reference': HCPC_STANDARDS['structure']['standard']
            })
        
        if 'objectivity' in by_category:
            recommendations.append({
                'priority': 'critical',
                'category': 'Objectivity',
                'action': 'Review language for judgmental or emotive terms. Use objective, factual descriptions.',
                'reference': HCPC_STANDARDS['objectivity']['standard']
            })
        
        return recommendations
