# InsureWise AI

AI-assisted insurance claim document verification and management.

**Live Application:** [insure-wise-ai.vercel.app](https://insure-wise-ai.vercel.app/)  
**Backend API:** [insurewise-ai.onrender.com](https://insurewise-ai.onrender.com)  
**API Documentation:** [View API Docs](https://insurewise-ai.onrender.com/docs)

## Overview

InsureWise AI is a web application designed to simplify insurance claim document verification. It combines document processing, OCR, AI-assisted analysis, and human review to help claim handlers organize claim evidence and identify missing information or potential inconsistencies.

The application follows a structured workflow in which claimants submit incident details and supporting documents, AI assists with document analysis, and authorized reviewers verify the documents online before proceeding to physical verification when required.

The goal is to reduce repetitive manual work, improve document traceability, and make the verification process easier to manage.

## Problem Statement

Insurance claim verification often involves reviewing multiple documents, checking policy details, identifying missing evidence, and comparing information across records. These activities can be time-consuming and may lead to delays when documents are incomplete or inconsistent.

InsureWise AI addresses these challenges by organizing the document verification process into a structured workflow supported by AI-assisted analysis and human supervision.

## Key Features

- **Claim Management:** Collect incident details and maintain claim-related information.
- **Document Checklist:** Generate a checklist of supporting documents required for a claim.
- **Individual Document Uploads:** Upload and track documents separately against their respective checklist items.
- **PDF Processing and OCR:** Extract information from supported documents for further analysis.
- **AI-Assisted Verification:** Analyze document content, identify missing information, and flag potential inconsistencies.
- **Human Review Workflow:** Route processed documents to authorized reviewers for online verification.
- **Correction Handling:** Support the review process when documents require additional information or replacement.
- **Physical Verification Tracking:** Manage physical-verification requests after the mandatory online document reviews are completed.
- **Claim Status Tracking:** Maintain visibility into document processing and verification progress.

## Workflow

1. **Claim Submission** — The claimant provides incident details and relevant policy information.
2. **Checklist Generation** — The application prepares a list of required supporting documents.
3. **Document Upload** — Each document is uploaded independently against its checklist item.
4. **AI Analysis** — The system processes documents, extracts information, and identifies potential issues.
5. **Online Human Review** — Processed documents are routed to authorized claim handlers for verification.
6. **Correction or Verification** — Reviewers verify documents or request corrections when necessary.
7. **Physical Verification** — Once mandatory online verification is complete, an authorized reviewer can initiate physical verification where required.
8. **Claim Review** — The verified evidence supports the insurer's subsequent claim decision.

AI analysis does not constitute final human verification or insurance claim approval.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React.js, Vite, JavaScript |
| Backend | Python, FastAPI |
| Document Processing | PyMuPDF |
| OCR | Tesseract OCR |
| Similarity Search | FAISS |
| Database | SQLite |
| Version Control | Git, GitHub |
| Frontend Hosting | Vercel |
| Backend Hosting | Render |

## Project Structure

```text
InsureWise-AI/
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/                 # API integration
│   │   ├── components/          # Reusable UI components
│   │   ├── context/             # Shared application state
│   │   └── pages/               # Application pages
│   ├── .env.production          # Production API configuration
│   ├── package.json
│   └── vite.config.js
│
├── backend/
│   ├── config/                  # Application configuration
│   ├── routers/                 # API route modules
│   ├── services/                # Business logic and processing
│   ├── sample_data/             # Sample data
│   ├── storage/
│   │   ├── indexes/             # Search indexes
│   │   ├── reports/              # Generated reports
│   │   └── uploads/              # Uploaded documents
│   ├── tests/                   # Backend tests
│   ├── main.py                  # FastAPI entry point
│   └── requirements.txt         # Python dependencies
│
├── render.yaml                  # Render deployment configuration
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

Make sure the following are installed:

- Git
- Node.js and npm
- Python compatible with the backend dependencies
- Tesseract OCR, if required by the configured document-processing pipeline
- Credentials for any external AI services used by the application

### Clone the Repository

```bash
git clone https://github.com/KoteshPusala/InsureWise-AI.git
cd InsureWise-AI
```

### Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

On Linux or macOS:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables for your AI provider, database, and other integrations. Use the variable names expected by the existing backend configuration.

Start the development server:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The backend should be available at:

- API: `http://127.0.0.1:8000`
- API documentation: `http://127.0.0.1:8000/docs`

### Frontend Setup

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
npm install
```

Create a `.env.local` file in `frontend/`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the development server:

```bash
npm run dev
```

Open the local URL displayed in the terminal.

Ensure the frontend API client uses `VITE_API_BASE_URL` and the backend permits requests from the local frontend origin.

## Environment Configuration

### Frontend

For production, configure the API base URL as follows:

```env
VITE_API_BASE_URL=https://insurewise-ai.onrender.com
```

The variable can be defined in `frontend/.env.production` or configured in Vercel's environment settings.

Variables prefixed with `VITE_` are included in the browser bundle. Do not store private API keys, database passwords, JWT secrets, or other confidential credentials in frontend environment variables.

### Backend

Backend configuration depends on the integrations enabled in the project. Configure any required AI provider credentials, CORS origins, storage settings, and database options through environment variables or the deployment platform's configuration.

Never commit real secrets to GitHub.

## API Documentation

The deployed backend is available at:

https://insurewise-ai.onrender.com

Interactive API documentation, when enabled, is available at:

https://insurewise-ai.onrender.com/docs

The documentation can be used to inspect available endpoints, request schemas, and response formats.

## Deployment

### Backend — Render

The backend is deployed on Render.

Typical service configuration:

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

Configure the required environment variables and system dependencies in Render. Ensure uploaded files, generated reports, databases, and search indexes are stored appropriately for the deployment environment.

### Frontend — Vercel

The frontend is deployed on Vercel.

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework | Vite |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| API Base URL | `https://insurewise-ai.onrender.com` |

After deployment, ensure the backend CORS configuration permits requests from the production frontend domain.

## Testing

The application should be tested across the complete claim verification workflow, including:

- Claim creation and checklist generation.
- Independent uploads for each required document.
- Valid, invalid, and unreadable PDF handling.
- AI processing success and failure.
- Automatic routing to human review.
- Reviewer decisions and correction requests.
- Physical-verification eligibility.
- API authentication and authorization.
- Data persistence and error handling.

Run the tests available in the repository before deploying changes.

## Security Considerations

- Validate uploaded files on both the frontend and backend.
- Restrict claim and document access to authorized users.
- Protect reviewer-only actions with backend authorization.
- Keep secrets out of source control.
- Handle AI-provider failures and processing timeouts safely.
- Avoid exposing sensitive document information in logs.
- Use persistent storage for files and records that must survive redeployments.

## Scope and Limitations

InsureWise AI focuses on document collection, AI-assisted analysis, and verification workflow management.

AI-generated findings may be incomplete or incorrect and require human assessment. Physical verification tracking does not imply that an external inspection has taken place. Final insurance claim approval, rejection, and settlement remain the responsibility of the insurer.

## Future Enhancements

- Improved document classification and information extraction.
- Enhanced policy-to-claim matching.
- Reviewer dashboards and detailed audit reporting.
- Notifications for missing documents and review updates.
- Persistent object storage for uploaded documents.
- Integration with external inspection and insurer systems.
- Expanded automated testing and deployment monitoring.

## License

No license has been added to this project yet.

---

**InsureWise AI** — Structured document verification for insurance claims.
