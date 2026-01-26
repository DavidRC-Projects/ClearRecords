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

## Technology Stack

### AWS Cloud Infrastructure

ClearRecords is built on AWS cloud services, providing a scalable, secure, and cost-effective platform:

- **AWS Textract** - Document intelligence service for extracting text and structured data from photos of clinical notes
- **AWS S3** - Temporary storage for uploaded photos with automatic lifecycle policies for immediate deletion
- **AWS Lambda** - Serverless compute for backend processing (Python)
- **API Gateway** - RESTful API endpoints
- **AWS Cognito** - User authentication and authorisation
- **DynamoDB** - NoSQL database for storing anonymised feedback reports only

### Mobile Application

- **React Native** - Cross-platform mobile framework (iOS and Android)
- **JavaScript** - Frontend development language
- **AWS Amplify** - Mobile app deployment and integration with AWS services

### Backend

- **Python** - Backend development language
- **FastAPI** - Modern Python web framework for API development
- **Rules-based Audit Engine** - Deterministic, explainable documentation checks (no ML)

### Key AWS Services Integration

**AWS Textract:**
- Processes photos of clinical notes uploaded from mobile devices
- Extracts text and identifies tables/structured data
- Converts handwritten or typed notes into machine-readable format
- Integrated with S3 for temporary file storage during processing

**AWS S3:**
- Temporary storage bucket configured with lifecycle policies
- Automatic deletion of uploaded photos after processing
- Zero-retention policy enforced at infrastructure level

---

## AWS Architecture Overview

### Data Flow

1. **Photo Upload:**
   - User takes photo or selects from gallery in React Native mobile app
   - Photo uploaded to AWS S3 temporary bucket (with lifecycle policy for auto-deletion)

2. **Document Processing:**
   - AWS Lambda function triggers AWS Textract to analyse the document
   - AWS Textract extracts text, tables, and structured data from the photo
   - Extracted data returned to Lambda function

3. **Audit Processing:**
   - Lambda function processes extracted text through rules-based audit engine
   - Checks performed against HCPC standards (no ML, deterministic rules)
   - Audit results generated

4. **Feedback Generation:**
   - Feedback report created from audit results
   - Report contains only anonymised feedback (no medical information)
   - Original photo and extracted text deleted from S3 immediately

5. **Storage (Optional):**
   - User opts in to save anonymised feedback report
   - Report stored in DynamoDB (no medical information)
   - Original notes and extracted data never stored

### Security & Compliance

- **Encryption:** All data encrypted in transit (HTTPS) and at rest (S3, DynamoDB encryption)
- **IAM Roles:** Least-privilege access policies for Lambda functions
- **Zero Retention:** S3 lifecycle policies ensure automatic deletion
- **No Medical Data:** Only anonymised feedback reports stored (with user opt-in)

---

## AWS Setup & Configuration

### Prerequisites

1. **AWS Account** - Active AWS account with appropriate permissions
2. **AWS CLI** - Installed and configured
   ```bash
   brew install awscli  # macOS
   aws configure
   ```
3. **AWS SAM CLI** - For serverless application deployment
   ```bash
   brew install aws-sam-cli  # macOS
   ```
4. **Node.js & npm** - For React Native development
5. **Python 3.11+** - For Lambda functions
6. **React Native CLI** - For mobile app development

### Step 1: AWS S3 Bucket Setup

**Create S3 Bucket for Temporary Storage:**

```bash
# Create bucket with versioning disabled
aws s3 mb s3://clearrecords-temp-<your-account-id> --region eu west

# Configure lifecycle policy for automatic deletion (1 hour)
aws s3api put-bucket-lifecycle-configuration \
  --bucket clearrecords-temp-<your-account-id> \
  --lifecycle-configuration file://s3-lifecycle-policy.json
```

**S3 Lifecycle Policy (`s3-lifecycle-policy.json`):**
```json
{
  "Rules": [
    {
      "Id": "DeleteAfter1Hour",
      "Status": "Enabled",
      "ExpirationInDays": 0,
      "ExpiredObjectDeleteMarker": false,
      "NoncurrentVersionExpirationInDays": 0,
      "AbortIncompleteMultipartUpload": {
        "DaysAfterInitiation": 1
      }
    }
  ]
}
```

**Enable Encryption:**
```bash
aws s3api put-bucket-encryption \
  --bucket clearrecords-temp-<your-account-id> \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### Step 2: AWS Textract Setup

**Create IAM Role for Textract:**
- Navigate to IAM Console → Roles → Create Role
- Select "Textract" as service
- Attach policy: `AmazonTextractFullAccess`
- Add S3 read permissions for your bucket
- Note the Role ARN for Lambda configuration

**Enable Textract API:**
- Textract is enabled by default in most regions
- Verify access in AWS Console → Textract

### Step 3: AWS Cognito Setup

**Create User Pool:**

```bash
# Using AWS CLI
aws cognito-idp create-user-pool \
  --pool-name ClearRecordsUsers \
  --auto-verified-attributes email \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 8,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": true
    }
  }'
```

**Create User Pool Client:**
```bash
aws cognito-idp create-user-pool-client \
  --user-pool-id <your-pool-id> \
  --client-name ClearRecordsMobile \
  --generate-secret \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH
```

### Step 4: DynamoDB Table Setup

**Create Feedback Table:**

```bash
aws dynamodb create-table \
  --table-name ClearRecordsFeedback \
  --attribute-definitions \
    AttributeName=userId,AttributeType=S \
    AttributeName=feedbackId,AttributeType=S \
  --key-schema \
    AttributeName=userId,KeyType=HASH \
    AttributeName=feedbackId,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --time-to-live-specification Enabled=true,AttributeName=ttl
```

### Step 5: Environment Variables

Create `.env` files for configuration:

**Backend `.env`:**
```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=your-account-id

# S3 Configuration
S3_TEMP_BUCKET=clearrecords-temp-<your-account-id>
S3_LIFECYCLE_DELETE_HOURS=1

# Textract Configuration
TEXTRACT_ROLE_ARN=arn:aws:iam::<account-id>:role/TextractRole

# Cognito Configuration
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxx

# DynamoDB Configuration
DYNAMODB_FEEDBACK_TABLE=ClearRecordsFeedback

# API Configuration
API_STAGE=prod
```

---

## Project File Structure

```
ClearRecords/
├── README.md
├── .gitignore
│
├── mobile/                          # React Native Mobile App
│   ├── package.json
│   ├── App.js
│   ├── app.json
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Button.js
│   │   │   │   ├── Input.js
│   │   │   │   └── LoadingSpinner.js
│   │   │   ├── forms/
│   │   │   │   ├── LoginForm.js
│   │   │   │   ├── RegisterForm.js
│   │   │   │   └── NoteInputForm.js
│   │   │   └── feedback/
│   │   │       ├── FeedbackReport.js
│   │   │       └── FeedbackItem.js
│   │   ├── screens/
│   │   │   ├── Auth/
│   │   │   │   ├── LoginScreen.js
│   │   │   │   └── RegisterScreen.js
│   │   │   ├── Home/
│   │   │   │   └── HomeScreen.js
│   │   │   ├── Audit/
│   │   │   │   ├── InputScreen.js
│   │   │   │   ├── PhotoCaptureScreen.js
│   │   │   │   └── ReviewScreen.js
│   │   │   ├── Feedback/
│   │   │   │   └── FeedbackScreen.js
│   │   │   └── Profile/
│   │   │       └── ProfileScreen.js
│   │   ├── services/
│   │   │   ├── api.js              # API client with AWS Amplify
│   │   │   ├── auth.js             # Cognito authentication
│   │   │   ├── s3.js               # S3 upload/download
│   │   │   └── storage.js           # AsyncStorage utilities
│   │   ├── navigation/
│   │   │   └── AppNavigator.js
│   │   ├── utils/
│   │   │   ├── constants.js
│   │   │   └── helpers.js
│   │   └── aws-exports.js          # AWS Amplify configuration
│   ├── android/
│   └── ios/
│
├── backend/                         # Python Backend (Lambda Functions)
│   ├── requirements.txt
│   ├── template.yaml                # AWS SAM template
│   ├── samconfig.toml               # SAM deployment config
│   ├── functions/
│   │   ├── document-processing/
│   │   │   ├── app.py              # Lambda handler for Textract
│   │   │   ├── textract_processor.py
│   │   │   └── requirements.txt
│   │   ├── audit-engine/
│   │   │   ├── app.py              # Lambda handler for audit
│   │   │   ├── audit_rules.py      # Rules-based audit logic
│   │   │   ├── hcpc_standards.py   # HCPC standards definitions
│   │   │   └── requirements.txt
│   │   ├── feedback-generator/
│   │   │   ├── app.py              # Lambda handler for feedback
│   │   │   ├── feedback_builder.py
│   │   │   └── requirements.txt
│   │   └── auth/
│   │       ├── app.py              # Lambda handler for auth
│   │       └── requirements.txt
│   ├── shared/                     # Shared code across functions
│   │   ├── __init__.py
│   │   ├── models.py               # Data models
│   │   ├── utils.py                # Utility functions
│   │   └── constants.py            # Constants
│   └── tests/                       # Unit tests
│       ├── test_audit_engine.py
│       └── test_textract_processor.py
│
├── infrastructure/                  # Infrastructure as Code
│   ├── template.yaml               # Main SAM template
│   ├── s3-lifecycle-policy.json    # S3 lifecycle configuration
│   ├── iam-policies/               # IAM policy documents
│   │   ├── lambda-textract-policy.json
│   │   └── lambda-dynamodb-policy.json
│   └── deploy.sh                   # Deployment script
│
├── docs/                           # Documentation
│   ├── api/                        # API documentation
│   ├── architecture/               # Architecture diagrams
│   └── deployment/                 # Deployment guides
│
└── scripts/                        # Utility scripts
    ├── setup-aws.sh                # AWS resource setup
    └── deploy.sh                   # Deployment script
```

### Key Files Explained

**Mobile App (`mobile/`):**
- `src/services/api.js` - API client configured with AWS Amplify
- `src/services/auth.js` - Cognito authentication wrapper
- `src/services/s3.js` - S3 upload/download utilities
- `src/aws-exports.js` - Auto-generated by Amplify CLI

**Backend (`backend/`):**
- `template.yaml` - AWS SAM template defining all Lambda functions and resources
- `functions/document-processing/app.py` - Processes photos with AWS Textract
- `functions/audit-engine/audit_rules.py` - Rules-based audit logic (no ML)
- `functions/feedback-generator/feedback_builder.py` - Generates feedback reports

**Infrastructure (`infrastructure/`):**
- `template.yaml` - Complete infrastructure definition
- `s3-lifecycle-policy.json` - S3 auto-deletion configuration
- `deploy.sh` - Automated deployment script

---

## AWS Service Configuration Details

### Lambda Function Configuration

**Document Processing Function:**
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 30 seconds
- Environment Variables:
  - `S3_TEMP_BUCKET` - S3 bucket name
  - `TEXTRACT_ROLE_ARN` - IAM role for Textract
- IAM Permissions:
  - `textract:AnalyzeDocument`
  - `s3:GetObject`
  - `s3:DeleteObject`

**Audit Engine Function:**
- Runtime: Python 3.11
- Memory: 256 MB
- Timeout: 15 seconds
- Environment Variables:
  - `DYNAMODB_TABLE` - DynamoDB table name
- IAM Permissions:
  - `dynamodb:GetItem`
  - `dynamodb:PutItem` (for feedback storage)

### API Gateway Configuration

- **API Type:** REST API
- **Stage:** `prod`
- **CORS:** Enabled for mobile app origins
- **Authentication:** AWS Cognito (JWT tokens)
- **Rate Limiting:** 1000 requests/minute per user

### S3 Bucket Configuration

- **Bucket Name:** `clearrecords-temp-<account-id>`
- **Region:** `us-east-1` (or your preferred region)
- **Versioning:** Disabled
- **Encryption:** AES256 (SSE-S3)
- **Lifecycle Policy:** Delete objects after 1 hour
- **Public Access:** Blocked
- **CORS:** Configured for mobile app uploads

### DynamoDB Configuration

- **Table Name:** `ClearRecordsFeedback`
- **Partition Key:** `userId` (String)
- **Sort Key:** `feedbackId` (String)
- **Billing Mode:** Pay-per-request
- **TTL:** Enabled (attribute: `ttl`)
- **Encryption:** Enabled (AWS managed keys)

### Cognito Configuration

- **User Pool:** `ClearRecordsUsers`
- **Email Verification:** Required
- **Password Policy:** 
  - Minimum 8 characters
  - Requires uppercase, lowercase, numbers, symbols
- **MFA:** Optional
- **Token Expiration:** 1 hour (access), 30 days (refresh)

---

## Development Workflow

### Local Development Setup

1. **Backend (Lambda Functions):**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Test locally with SAM
   sam local start-api
   ```

2. **Mobile App:**
   ```bash
   cd mobile
   npm install
   
   # Configure Amplify
   amplify init
   amplify add auth
   amplify add api
   
   # Run on iOS
   npm run ios
   
   # Run on Android
   npm run android
   ```

### Deployment Process

1. **Deploy Backend:**
   ```bash
   cd backend
   sam build
   sam deploy --guided
   ```

2. **Deploy Mobile App:**
   ```bash
   cd mobile
   amplify push
   ```

3. **Update Environment Variables:**
   - Update `.env` files with deployed resource ARNs
   - Update `aws-exports.js` in mobile app

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
     - Mobile-optimised interface for both input methods

5. **US-2.2: Document Intelligence Processing**
   - As a physiotherapist, I want photos of my notes automatically converted to structured text, so that they can be audited
   - Acceptance Criteria:
     - AWS Textract processes photos to extract text and identify tables
     - Text is organised into structured format (tables, forms, raw text)
     - User can review and edit extracted text before audit
     - Handles various handwriting styles and note formats (where supported by AWS Textract)
     - Clear indication of extraction confidence/quality
     - Photos temporarily stored in AWS S3 with automatic deletion

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

- Photos are processed using **AWS Textract** to extract structured text and identify tables
- AWS Textract analyses document images and extracts:
  - Raw text content
  - Structured tables
  - Form fields
  - Handwritten text (where supported)
- Extracted text is organised into structured format for audit processing
- All extracted data is deleted immediately after audit completion
- No extracted text or structured data is retained
- Photos are temporarily stored in AWS S3 bucket with automatic deletion policies

### What We Never Store

- Patient names or identifiers
- Medical information or clinical details
- Original notes (text or photos)
- Extracted text from document intelligence
- Any patient-identifiable data

### What We Optionally Store (User Opt-in)

- Anonymised feedback reports (no medical information)
- User account information (email, professional registration number)
- Audit history metadata (dates, improvement trends - no clinical content)

---

## Non-Functional Requirements

- **Platform:** Mobile-first application (iOS and Android native apps built with React Native)
- **Performance:** Audit results generated within 30 seconds for typical SOAP notes
- **Security:** All data encrypted in transit and at rest using AWS security features
- **Availability:** 99% uptime target (AWS managed services)
- **Accessibility:** WCAG 2.1 AA compliance
- **Document Intelligence:** AWS Textract integration for photo-to-text conversion and table extraction
- **Cloud Infrastructure:** AWS serverless architecture (Lambda, API Gateway, S3, DynamoDB)
- **Data Retention:** Zero retention policy - all notes and extracted data deleted immediately after processing via S3 lifecycle policies
- **Storage:** Only anonymised feedback reports stored in DynamoDB (with user opt-in), no medical information ever stored

---

## Out of Scope (MVP)

The following are explicitly **not** included in the MVP:

- Machine learning or AI-based clinical analysis or judgment
- Practitioner comparison or ranking
- Integration with EPR systems
- Multi-profession support (physiotherapy only for MVP)
- Aggregate analytics dashboard
- Clinical decision support
- Patient risk assessment
- Fitness-to-practise indicators

**Note:** AWS Textract (document intelligence/OCR) for photo-to-text conversion is **in scope** as it is required for processing photo uploads. This is distinct from ML-based clinical analysis or judgment, which remains out of scope. AWS Textract is used solely for extracting and structuring text from images, not for making clinical assessments.

*"Better record keeping. Fewer fitness-to-practise cases. Clearer, defensible documentation. Consistent standards across registrants."*
