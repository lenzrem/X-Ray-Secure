# X-Ray-Secure

X-Ray-Secure is a web application designed for analyzing and managing security data. It provides a user-friendly interface for uploading, processing, and managing security-related documents while ensuring data privacy and confidentiality.

## Installation

  1. Clone the repository:
  git clone https://github.com/yourusername/x-ray-secure.git
  cd x-ray-secure
  
  2. Create a virtual environment and activate it:
  python -m venv venv
  source venv/bin/activate  # On Windows, use venv\Scripts\activate
  
  3. Install the required dependencies:
  pip install -r requirements.txt
  
  4. Set up environment variables:
  Create a `.env` file in the project root and add necessary variables.
  
  5. Initialize the database:
  python init_db.py

## Usage

1. Start the FastAPI server:
uvicorn main:app --reload

2. Open your web browser and navigate to `http://localhost:8000`.

3. Use the interface to:
- Upload security documents (PDF, EML, MSG)
- Process documents for anonymization
- Manage and preview anonymized files

## Technologies Used

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- PyPDF2
- HTML/CSS/JavaScript
- Tailwind CSS
- Axios
- SQLite (development) / PostgreSQL (production)
- Git
- Docker
