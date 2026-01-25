# ClearRecords

**Documentation Quality Audit Tool for Physiotherapy Records**

---

## Introduction

ClearRecords is a mobile-first, voluntary, educational digital tool that helps physiotherapists improve their clinical documentation by auditing notes against HCPC record-keeping standards. The tool provides structured, non-punitive feedback to support registrants in meeting professional standards, reducing documentation-related fitness-to-practise concerns, and supporting continuous professional development.

**Core Principle:** ClearRecords audits *how things are written*, not *what was done*. It helps practitioners create clearer, more defensible documentation without making clinical judgments or assessing treatment appropriateness.

**Data Privacy Commitment:** ClearRecords never stores patient names or medical information. Original notes and extracted data are deleted immediately after processing. Only anonymised feedback reports are optionally saved, ensuring complete protection of sensitive clinical data.

---

## Product Vision

Better record keeping. Fewer fitness-to-practise cases. Clearer, defensible documentation. Consistent standards across registrants.

---

## Epics & User Stories

### Epic 1: User Authentication & Account Management

**As a** physiotherapist  
**I want** to securely access the ClearRecords platform  
**So that** my documentation can be audited confidentially and my feedback history is preserved

**User Stories:**

1. **US-1.1: User Registration**
   - As a physiotherapist, I want to create an account with my professional credentials, so that I can access the platform securely
   - Acceptance Criteria:
     - User can register with email and password
     - Professional registration number can be optionally provided
     - Email verification is required
     - Terms of service and privacy policy must be accepted

2. **US-1.2: User Login**
   - As a registered user, I want to log in securely, so that I can access my account and previous audit reports
   - Acceptance Criteria:
     - Secure login with email and password
     - Password reset functionality
     - Session management (auto-logout after inactivity)

3. **US-1.3: Profile Management**
   - As a user, I want to manage my profile information, so that my account details remain current
   - Acceptance Criteria:
     - Update email address
     - Change password
     - Update professional registration details

---

### Epic 2: Document Input & Pre-Processing

**As a** physiotherapist  
**I want** to input my clinical notes easily on my mobile device  
**So that** they can be audited against HCPC standards

**User Stories:**

4. **US-2.1: Document Input (Text or Photo)**
   - As a physiotherapist, I want to either type my notes or take a photo of them, so that I can get feedback on my documentation
   - Acceptance Criteria:
     - Option to type notes directly into text input field
     - Option to take a photo using device camera
     - Option to upload photo from device gallery
     - Clear instructions on anonymisation requirements
     - Maximum file size limit enforced for photos
     - Mobile-optimized interface for both input methods

5. **US-2.2: Document Intelligence Processing**
   - As a physiotherapist, I want photos of my notes automatically converted to structured text, so that they can be audited
   - Acceptance Criteria:
     - Document intelligence tool extracts text from photos
     - Text is organized into tables/structured format
     - User can review and edit extracted text before audit
     - Handles various handwriting styles and note formats
     - Clear indication of extraction confidence/quality

6. **US-2.3: Anonymisation Check**
   - As a physiotherapist, I want the system to help identify potential patient identifiers, so that I can ensure my notes are properly anonymised
   - Acceptance Criteria:
     - System flags potential identifiers (names, dates of birth, addresses)
     - User can review and confirm anonymisation
     - Clear warnings if identifiers are detected
     - Option to proceed only after confirmation

7. **US-2.4: Section Detection**
   - As a physiotherapist, I want the system to automatically identify SOAP sections in my notes, so that the audit can be performed accurately
   - Acceptance Criteria:
     - System detects Subjective, Objective, Assessment, and Plan sections
     - User can manually adjust section boundaries if needed
     - Visual indication of detected sections
     - Handles common variations (SOAP, SOAPE, etc.)

---

### Epic 3: Documentation Audit Engine

**As a** physiotherapist  
**I want** my notes audited against HCPC standards  
**So that** I can identify areas for improvement in my documentation

**User Stories:**

8. **US-3.1: Identification & Context Audit**
   - As a physiotherapist, I want feedback on whether my notes include required identification elements, so that I meet HCPC standards for record identification
   - Acceptance Criteria:
     - Checks for date and time of entry
     - Checks for practitioner identifier
     - Checks for patient identifier (anonymised)
     - Provides specific feedback on missing elements

9. **US-3.2: Structure & Organisation Audit**
   - As a physiotherapist, I want feedback on the structure and clarity of my notes, so that they are understandable and well-organised
   - Acceptance Criteria:
     - Validates SOAP structure is present and clear
     - Checks for logical flow between sections
     - Identifies sections that are difficult to distinguish
     - Provides feedback on structural improvements

10. **US-3.3: Objectivity & Professional Tone Audit**
   - As a physiotherapist, I want feedback on the objectivity and professional tone of my notes, so that they meet HCPC expectations for factual, non-judgmental documentation
   - Acceptance Criteria:
     - Identifies speculative language in objective sections
     - Flags emotive or judgmental language
     - Distinguishes between objective findings and opinions
     - Provides examples of more objective phrasing

11. **US-3.4: Clinical Reasoning Transparency Audit**
    - As a physiotherapist, I want feedback on whether my notes show clear reasoning, so that the rationale for my decisions is documented (without judging correctness)
    - Acceptance Criteria:
      - Checks for presence of assessment section
      - Identifies rationale language ("suggests", "consistent with")
      - Validates link between findings and plan
      - Does NOT assess whether reasoning is correct

12. **US-3.5: Plan & Follow-Up Audit**
    - As a physiotherapist, I want feedback on whether my treatment plan and follow-up are clearly documented, so that continuity of care is supported
    - Acceptance Criteria:
      - Checks for presence of treatment plan
      - Identifies home exercise/advice documentation
      - Validates follow-up or review plan is stated
      - Provides feedback on missing elements

13. **US-3.6: Timeliness Audit**
    - As a physiotherapist, I want feedback on the timeliness of my documentation, so that I meet HCPC expectations for contemporaneous record-keeping
    - Acceptance Criteria:
      - Checks for timestamp presence
      - Validates timestamp is within acceptable window
      - Identifies amendments that may not be clearly marked
      - Provides feedback on timeliness concerns

---

### Epic 4: Feedback Generation & Display

**As a** physiotherapist  
**I want** clear, actionable feedback on my documentation  
**So that** I can improve my record-keeping skills

**User Stories:**

14. **US-4.1: Feedback Report Generation**
    - As a physiotherapist, I want to receive a comprehensive feedback report after audit, so that I understand how my documentation aligns with HCPC standards
    - Acceptance Criteria:
      - Report shows identified strengths
      - Report highlights missing or unclear elements
      - Each feedback item references relevant HCPC guidance
      - No scores, grades, or rankings are displayed

15. **US-4.2: HCPC Standard References**
    - As a physiotherapist, I want feedback that references specific HCPC standards, so that I can understand the regulatory basis for the feedback
    - Acceptance Criteria:
      - Each feedback item links to relevant HCPC standard
      - Uses HCPC language verbatim where appropriate
      - Provides links to HCPC guidance documents
      - Clear explanation of why each point matters

16. **US-4.3: Reflective Prompts**
    - As a physiotherapist, I want reflective prompts with my feedback, so that I can engage in continuous professional development
    - Acceptance Criteria:
      - Each feedback area includes reflective questions
      - Prompts encourage self-assessment
      - Suggestions for improvement are provided
      - Links to CPD resources where relevant

17. **US-4.4: Feedback Export**
    - As a physiotherapist, I want to export my feedback report, so that I can save it for my records or CPD portfolio
    - Acceptance Criteria:
      - Export as PDF
      - Export as text file
      - Includes all feedback and HCPC references
      - Can be saved locally or printed

---

### Epic 5: Data Privacy & Security

**As a** physiotherapist  
**I want** assurance that my clinical notes are handled securely  
**So that** patient confidentiality and my professional obligations are maintained

**User Stories:**

18. **US-5.1: Transient Processing & Immediate Deletion**
    - As a physiotherapist, I want my notes and extracted data deleted immediately after processing, so that no patient names or medical information is ever stored
    - Acceptance Criteria:
      - Original notes (text or photos) are processed in memory only
      - Extracted text from document intelligence is processed transiently
      - All note content and extracted data are permanently deleted immediately after audit completes
      - No patient names or medical information is ever stored
      - Clear indication that notes are not saved
      - Automatic deletion confirmed to user after processing

19. **US-5.2: Opt-in Report Storage**
    - As a physiotherapist, I want the option to save only my anonymised feedback reports, so that I can track my improvement over time without storing any medical information
    - Acceptance Criteria:
      - Explicit opt-in required to save reports
      - Only anonymised feedback reports are saved (no original notes, no extracted text, no medical information)
      - Feedback reports contain no patient names or identifiable medical data
      - User can delete saved reports at any time
      - Clear privacy policy explanation that no medical information is stored

20. **US-5.3: Data Deletion**
    - As a physiotherapist, I want to delete my account and all associated data, so that I can exercise my data protection rights
    - Acceptance Criteria:
      - Account deletion functionality
      - All user data removed on deletion
      - Confirmation required before deletion
      - Clear explanation of what is deleted

---

### Epic 6: Educational Resources & Support

**As a** physiotherapist  
**I want** access to educational resources about documentation standards  
**So that** I can improve my understanding and practice

**User Stories:**

21. **US-6.1: HCPC Guidance Access**
    - As a physiotherapist, I want easy access to HCPC record-keeping guidance, so that I can reference the standards directly
    - Acceptance Criteria:
      - Links to HCPC Standards of Conduct, Performance and Ethics
      - Links to HCPC record-keeping guidance
      - Contextual links within feedback reports
      - Resources page with all relevant links

22. **US-6.2: Documentation Examples**
    - As a physiotherapist, I want to see examples of good documentation, so that I can learn from best practice
    - Acceptance Criteria:
      - Example SOAP notes (anonymised)
      - Examples aligned with HCPC standards
      - Clear explanations of why examples are good
      - Multiple examples covering different scenarios

23. **US-6.3: Help & FAQ**
    - As a physiotherapist, I want access to help documentation and FAQs, so that I can understand how to use the tool effectively
    - Acceptance Criteria:
      - FAQ section addressing common questions
      - User guide/tutorial
      - Clear explanation of what the tool does and doesn't do
      - Contact information for support

---

### Epic 7: Disclaimers & Boundaries

**As a** physiotherapist  
**I want** clear information about what the tool does and doesn't do  
**So that** I understand its limitations and appropriate use

**User Stories:**

24. **US-7.1: Tool Limitations Display**
    - As a physiotherapist, I want clear disclaimers about what the tool cannot assess, so that I understand its scope
    - Acceptance Criteria:
      - Prominent disclaimer on upload page
      - Clear statement that tool does NOT assess clinical safety
      - List of what is excluded (diagnosis, treatment correctness, etc.)
      - Reminder that tool is not a substitute for professional judgment

25. **US-7.2: Educational Purpose Statement**
    - As a physiotherapist, I want confirmation that this is an educational tool, so that I understand it is not punitive or regulatory
    - Acceptance Criteria:
      - Clear statement of educational purpose
      - Emphasis on voluntary, developmental use
      - No connection to fitness-to-practise processes
      - Reassurance about non-punitive nature

---

## Data Governance & Privacy

### Zero-Retention Policy

ClearRecords operates on a strict zero-retention policy for all clinical data:

- **Original Notes:** Text input or photos are processed in memory only and immediately deleted after audit completion
- **Extracted Data:** Text extracted from photos via document intelligence is processed transiently and permanently deleted
- **No Medical Information Stored:** Patient names, medical information, or clinical details are never stored
- **Feedback Only:** Only anonymised feedback reports are optionally saved (with explicit user opt-in)
- **Immediate Deletion:** All note content and extracted data are confirmed deleted immediately after processing

### Document Intelligence Processing

- Photos are processed using document intelligence/OCR services to extract structured text
- Extracted text is organized into tables for audit processing
- All extracted data is deleted immediately after audit completion
- No extracted text or structured data is retained

### What We Never Store

- ❌ Patient names or identifiers
- ❌ Medical information or clinical details
- ❌ Original notes (text or photos)
- ❌ Extracted text from document intelligence
- ❌ Any patient-identifiable data

### What We Optionally Store (User Opt-in)

- ✅ Anonymised feedback reports (no medical information)
- ✅ User account information (email, professional registration number)
- ✅ Audit history metadata (dates, improvement trends - no clinical content)

---

## Non-Functional Requirements

- **Platform:** Mobile-first application (iOS and Android native apps)
- **Performance:** Audit results generated within 30 seconds for typical SOAP notes
- **Security:** All data encrypted in transit and at rest
- **Availability:** 99% uptime target
- **Accessibility:** WCAG 2.1 AA compliance
- **Document Intelligence:** Integration with document intelligence/OCR service for photo-to-text conversion
- **Data Retention:** Zero retention policy - all notes and extracted data deleted immediately after processing
- **Storage:** Only anonymised feedback reports stored (with user opt-in), no medical information ever stored

---

## Out of Scope (MVP)

The following are explicitly **not** included in the MVP:

- ❌ Machine learning or AI-based clinical analysis or judgment
- ❌ Practitioner comparison or ranking
- ❌ Integration with EPR systems
- ❌ Multi-profession support (physiotherapy only for MVP)
- ❌ Aggregate analytics dashboard
- ❌ Clinical decision support
- ❌ Patient risk assessment
- ❌ Fitness-to-practise indicators

**Note:** Document intelligence/OCR for photo-to-text conversion is **in scope** as it is required for processing photo uploads. This is distinct from ML-based clinical analysis, which remains out of scope.

---

## Status

**Concept & Planning Stage** - User stories defined, ready for development prioritisation.

---

*"Better record keeping. Fewer fitness-to-practise cases. Clearer, defensible documentation. Consistent standards across registrants."*
