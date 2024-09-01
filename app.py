from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from query_suggestions import router as query_suggestions_router
from typing import List
import os
import logging
import json
import shutil
from anonymizer import anonymize_pdf, preview_anonymized_pdf
from ai_handler import process_security_questions, get_tinybert_progress
from users import get_users
import asyncio
import PyPDF2

# Global variables
analysis_results = None
analysis_error = None

# Logging setup
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI app initialisation
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(query_suggestions_router, prefix="/api/suggestions")
templates = Jinja2Templates(directory="templates")

# Ensure required directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("uploads/anonymized", exist_ok=True)

# Pydantic model for question processing
class ProcessQuestionsRequest(BaseModel):
    ai_model: str
    api_key: str
    questions: List[str]

# File handling functions
def load_uploaded_files():
    try:
        with open("uploads/uploaded_files.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"uploaded_pdfs": []}

def save_uploaded_files(data):
    with open("uploads/uploaded_files.json", "w") as f:
        json.dump(data, f)

def load_security_questions():
    with open("security_questions.txt", "r") as f:
        return [line.strip() for line in f if line.strip()]

# Route handlers
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/load_data", response_class=HTMLResponse)
async def load_data(request: Request):
    logger.info("Accessing /load_data endpoint")
    return templates.TemplateResponse("load_data.html", {"request": request})

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    logger.info(f"Uploading file: {file.filename}")
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    
    uploaded_files = load_uploaded_files()
    if file.filename not in uploaded_files["uploaded_pdfs"]:
        uploaded_files["uploaded_pdfs"].append(file.filename)
        save_uploaded_files(uploaded_files)
    
    return {"message": f"Successfully uploaded {file.filename}"}

@app.get("/get_uploaded_pdfs")
async def get_uploaded_pdfs():
    logger.info("Getting uploaded PDFs")
    uploaded_files = load_uploaded_files()
    return uploaded_files

@app.get("/get_anonymized_files")
async def get_anonymized_files():
    logger.info("Getting anonymised PDFs")
    anonymized_files = [f for f in os.listdir("uploads/anonymized") if f.endswith('.pdf')]
    return {"anonymized_files": anonymized_files}

@app.delete("/remove_pdf/{filename}")
async def remove_pdf(filename: str):
    logger.info(f"Removing file: {filename}")
    uploaded_files = load_uploaded_files()
    
    original_path = f"uploads/{filename}"
    if os.path.exists(original_path):
        os.remove(original_path)
        logger.info(f"Removed original file: {original_path}")
        if filename in uploaded_files["uploaded_pdfs"]:
            uploaded_files["uploaded_pdfs"].remove(filename)
            save_uploaded_files(uploaded_files)
    
    anonymized_path = f"uploads/anonymized/anonymized_{filename}"
    if os.path.exists(anonymized_path):
        os.remove(anonymized_path)
        logger.info(f"Removed anonymised file: {anonymized_path}")
    
    if not os.path.exists(original_path) and not os.path.exists(anonymized_path):
        return {"message": f"Successfully removed {filename}"}
    else:
        raise HTTPException(status_code=404, detail="File not found or could not be deleted")

@app.get("/preview_anonymized_pdf/{filename}")
async def preview_anonymized_pdf(filename: str):
    try:
        anonymized_path = f"uploads/anonymized/anonymized_{filename}"
        if not os.path.exists(anonymized_path):
            raise HTTPException(status_code=404, detail="Anonymised file not found")

        with open(anonymized_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            preview_text = ""
            for page in pdf_reader.pages:
                preview_text += page.extract_text() + "\n\n"

        return {"preview": preview_text}
    except Exception as e:
        logger.exception(f"Error previewing anonymised PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/check_anonymized/{filename}")
async def check_anonymized(filename: str):
    anonymized_path = f"uploads/anonymized/anonymized_{filename}"
    is_anonymized = os.path.exists(anonymized_path)
    return {"is_anonymized": is_anonymized}

@app.get("/anonymise_data", response_class=HTMLResponse)
async def anonymise_data(request: Request):
    uploaded_files = load_uploaded_files()
    return templates.TemplateResponse("anonymise_data.html", {"request": request, "uploaded_pdfs": uploaded_files["uploaded_pdfs"]})

@app.post("/anonymize_pdf")
async def anonymize_pdf_route(request: Request):
    logger.info("Anonymise PDF route called")
    try:
        json_body = await request.json()
        filename = json_body.get("filename")

        if not filename:
            logger.error("No filename provided in the request")
            raise HTTPException(status_code=400, detail="No filename provided")
        
        input_path = f"uploads/{filename}"
        output_filename = f"anonymized_{filename}"
        output_path = f"uploads/anonymized/{output_filename}"
        
        if not os.path.exists(input_path):
            logger.error(f"File not found: {input_path}")
            raise HTTPException(status_code=404, detail="File not found")
        
        success = anonymize_pdf(input_path, output_path)
        
        if success:
            logger.info(f"Successfully anonymised {filename}")
            anonymized_url = f"/view_pdf/{output_filename}"
            return JSONResponse(content={
                "message": f"Successfully anonymised {filename}",
                "anonymized_file": anonymized_url
            }, status_code=200)
        else:
            logger.error(f"Failed to anonymise {filename}")
            return JSONResponse(content={
                "message": f"Failed to anonymise {filename}. Please try again."
            }, status_code=500)
    
    except Exception as e:
        logger.exception(f"Error during anonymisation process: {str(e)}")
        return JSONResponse(content={
            "message": f"An error occurred during the anonymisation process: {str(e)}"
        }, status_code=500)

@app.post("/preview_anonymized_pdf")
async def preview_anonymized_pdf_route(request: Request):
    logger.info("Preview anonymised PDF route called")
    try:
        json_body = await request.json()
        filename = json_body.get("filename")

        if not filename:
            logger.error("No filename provided in the request")
            raise HTTPException(status_code=400, detail="No filename provided")

        input_path = f"uploads/{filename}"

        if not os.path.exists(input_path):
            logger.error(f"File not found: {input_path}")
            raise HTTPException(status_code=404, detail="File not found")

        preview_text = preview_anonymized_pdf(input_path)

        return JSONResponse(content={
            "preview": preview_text
        }, status_code=200)

    except Exception as e:
        logger.exception(f"Error during preview process: {str(e)}")
        return JSONResponse(content={
            "message": f"An error occurred during the preview process: {str(e)}"
        }, status_code=500)

@app.get("/view_pdf/{filename}")
async def view_pdf(filename: str):
    file_path = f"uploads/anonymized/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/pdf", filename=filename)
    else:
        raise HTTPException(status_code=404, detail="PDF not found")

@app.get("/security_questions", response_class=HTMLResponse)
async def security_questions(request: Request):
    questions = load_security_questions()
    return templates.TemplateResponse("security_questions.html", {"request": request, "questions": questions})

@app.post("/process_questions")
async def process_questions(request: ProcessQuestionsRequest, background_tasks: BackgroundTasks):
    logger.info("Processing security questions")
    global analysis_results, analysis_error
    try:
        async def process_in_background():
            global analysis_results, analysis_error
            try:
                results = process_security_questions(
                    request.ai_model,
                    request.api_key,
                    request.questions,
                    "uploads/anonymized"
                )
                analysis_results = results
                analysis_error = None
            except Exception as e:
                logger.exception(f"Error in background task: {str(e)}")
                analysis_error = str(e)
                analysis_results = None

        analysis_results = None
        analysis_error = None

        background_tasks.add_task(process_in_background)

        return JSONResponse(content={"message": "Processing started in the background"}, status_code=202)
    except Exception as e:
        logger.exception(f"Error setting up background task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/process_status")
async def process_status():
    global analysis_results, analysis_error
    if analysis_error:
        return JSONResponse(content={"status": "error", "message": analysis_error}, status_code=500)
    elif analysis_results:
        return JSONResponse(content={"status": "complete", "results": analysis_results}, status_code=200)
    else:
        return JSONResponse(content={"status": "processing"}, status_code=202)

@app.get("/result", response_class=HTMLResponse)
async def result(request: Request):
    global analysis_results
    return templates.TemplateResponse("result.html", {"request": request, "results": analysis_results})

@app.get("/get_users")
async def get_users_list():
    users = get_users()
    return {"users": users}

@app.get("/get_tinybert_progress")
async def tinybert_progress():
    progress = get_tinybert_progress()
    return {"progress": progress}

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)