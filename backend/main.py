import os
import tempfile
from fastapi import FastAPI, File, UploadFile, Form
from pypdf import PdfReader
import docx
from PIL import Image
import easyocr
from bs4 import BeautifulSoup
import requests
import re
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


app = FastAPI()

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vector_db = None
all_uploaded_chunks = []  # store all chunks for keyword fallback
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# ---------- Extraction Functions ----------
def extract_text_from_pdf(file_path):
    text = ""
    reader = PdfReader(file_path)
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text_from_image(file_path):
    reader = easyocr.Reader(['en'], gpu=False)
    result = reader.readtext(file_path, detail=0)
    return " ".join(result)

def extract_text_from_url(url):
    response = requests.get(url)
    if response.status_code != 200:
        return ""
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return "\n".join([line.strip() for line in text.splitlines() if line.strip()])

# ---------- Upload Endpoint ----------
@app.post("/upload_files/")
async def upload_file(files: List[UploadFile] = File(...)):
    global vector_db, all_uploaded_chunks
    processed_files = []

    try:
        for file in files:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(await file.read())
                tmp_path = tmp.name

            # Extract text
            if file.filename.lower().endswith(".pdf"):
                text = extract_text_from_pdf(tmp_path)
            elif file.filename.lower().endswith(".docx"):
                text = extract_text_from_docx(tmp_path)
            elif file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                text = extract_text_from_image(tmp_path)
            else:
                continue  

            if not text.strip():
                continue

            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunks = splitter.split_text(text)

            all_uploaded_chunks.extend(chunks)

            if vector_db is None:
                vector_db = FAISS.from_texts(chunks, embeddings)
            else:
                vector_db.add_texts(chunks)

            processed_files.append(file.filename)

        if not processed_files:
            return {"error": "No supported files uploaded or no text extracted"}

        return {"status": "success", "message": f"Processed: {', '.join(processed_files)}"}

    except Exception as e:
        return {"error": str(e)}
    
@app.post("/upload_url/")
async def upload_url(url: str = Form(...)):
    global vector_db, all_uploaded_chunks
    try:
        text = extract_text_from_url(url)
        if not text.strip():
            return {"error": "Could not extract text from the provided URL."}

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_text(text)
        all_uploaded_chunks.extend(chunks)

        if vector_db is None:
            vector_db = FAISS.from_texts(chunks, embeddings)
        else:
            vector_db.add_texts(chunks)

        return {"status": "success", "message": f"Processed URL: {url}"}

    except Exception as e:
        return {"error": str(e)}

# ---------- Ask Endpoint ----------
@app.post("/ask/")
async def ask_question(query: str = Form(...)):
    try:
        global vector_db, all_uploaded_chunks
        if not all_uploaded_chunks:
            return {"error": "No data uploaded yet. Please upload a file or URL first."}

        docs = vector_db.similarity_search(query, k=8)  
        faiss_context = "\n".join([d.page_content for d in docs])

        stopwords = {"what", "is", "the", "a", "an", "of", "in", "and", "to", "for"}
        query_words = [w.lower() for w in re.findall(r"\w+", query) if w.lower() not in stopwords]
        keyword_matches = [chunk for chunk in all_uploaded_chunks if any(word in chunk.lower() for word in query_words)]
        keyword_context = "\n".join(keyword_matches)

        context = (faiss_context + "\n" + keyword_context).strip()

        if not context:
            return {"answer": "Not provided in the context"}

        max_length = 3500
        if len(context) > max_length:
            context = context[:max_length] + "\n...[truncated]"

        llm = ChatGroq(temperature=0, model="llama3-8b-8192")
        prompt = f"""
        You are a helpful assistant.
        Combine all relevant information from the context below to answer the question in a **clear and complete** way.
        Do NOT just copy one sentence — summarize everything relevant.
        If the answer is not in the context, reply exactly with "Not provided in the context".

        Context:
        {context}

        Question: {query}
        Answer:
        """
        response = llm.invoke(prompt)
        return {"answer": response.content.strip()}

    except Exception as e:
        return {"error": str(e)}
