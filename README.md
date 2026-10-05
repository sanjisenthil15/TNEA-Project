# TNEA Career Insight Navigator

A comprehensive student-focused career guidance and Tamil Nadu Engineering Admissions (TNEA) counselling navigation platform.

## Overview

**TNEA Career Insight Navigator** empowers engineering aspirants with data-driven college search, cutoff analysis, career interest assessments, personalized recommendations, automated choice list planning, and an AI Career Assistant powered by Retrieval-Augmented Generation (RAG).

## Key Features

- **Authentication & Security**: Secure student signup, login, session management, and profile customization.
- **Career Assessment & Profiling**: Interactive Holland-code & interest-based assessments to discover personalized engineering career tracks.
- **College Search & Cutoff Analysis**: Multi-year (2023, 2024, 2025) cutoff trends, branch filtering, community-based analysis, and seat matrix insights.
- **Intelligent College Recommendations**: Multi-tier recommendation engine categorized by Dream, Target, and Safe colleges.
- **College Comparison**: Side-by-side comparison of engineering institutions across infrastructure, cutoffs, placements, and ratings.
- **Interactive Choice List & Planner**: Choice filling strategy builder with priority reordering and export capabilities.
- **AI Career Assistant with RAG**: Semantic retrieval over TNEA guidelines, college database, and career roadmaps using persistent vector search and OpenAI LLM integration.
- **Counselling Journey & Document Vault**: Step-by-step counselling milestone tracker and secure certificate repository.
- **Premium Architecture**: Extended analytics, deep branch trends, and expert decision support.

## Tech Stack

- **Backend**: Python 3.10+, Flask, SQLite, SQLAlchemy
- **Frontend**: HTML5, Modern CSS (Glassmorphism / Design System), JavaScript (ES6+)
- **Data & Machine Learning**: Pandas, NumPy, Scikit-learn
- **AI & RAG Engine**: OpenAI API, Persistent ChromaDB / Dense TF-IDF Embeddings
- **Storage**: SQLite database (`database/tnea.db`) and document vault

## Project Structure

```
TNEA_career_navigator/
├── app.py                      # Main Flask application and API routes
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable configuration template
├── database/
│   └── tnea.db                 # SQLite database (colleges, branches, cutoffs, users)
├── datasets/                   # Verified TNEA dataset files (CSV)
├── models/                     # AI Assistant, RAG Engine, Career Engine, Database models
├── static/                     # CSS stylesheets, JavaScript files, and UI assets
├── templates/                  # Jinja2 HTML templates
├── scripts/
│   └── ingest_knowledge.py     # RAG vector database ingestion script
└── storage/
    └── vault/                  # Document storage directory
```

## Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/sanjisenthil15/TNEA-Project.git
cd TNEA-Project
```

### 3. Setup Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your configuration:
```bash
cp .env.example .env
```
*(Configure `OPENAI_API_KEY`, `SECRET_KEY`, etc. as needed)*

### 6. Ingest Knowledge Base (Optional / for RAG Vector Search)
```bash
python scripts/ingest_knowledge.py
```

### 7. Run the Application
```bash
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## License

This project is licensed under the MIT License.
