import os
import logging
from typing import List, Dict, Tuple
import torch
from transformers import AutoModelForQuestionAnswering, AutoTokenizer, BartForConditionalGeneration, T5ForConditionalGeneration
import PyPDF2
import re
import traceback
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import openai
import anthropic
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
import textwrap
import tiktoken

# Set up NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Check CUDA availability
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"Current device: {torch.cuda.current_device()}")
    print(f"Device name: {torch.cuda.get_device_name(0)}")
else:
    print("CUDA is not available. Using CPU.")

# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = []
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                text.append((page_text, page_num))
        return text
    except Exception as e:
        logging.error(f"Error extracting text from PDF {file_path}: {str(e)}")
        return []

# Function to preprocess text
def preprocess_text(text):
    text = re.sub(r'[^\w\s.,?!]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Function to load model and tokeniser
def load_model_and_tokenizer(model_name):
    try:
        logging.info(f"Loading {model_name} model and tokeniser")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if model_name == 'mpnet':
            model = AutoModelForQuestionAnswering.from_pretrained("microsoft/mpnet-base")
            tokenizer = AutoTokenizer.from_pretrained("microsoft/mpnet-base")
        elif model_name == 'bart':
            model = BartForConditionalGeneration.from_pretrained("facebook/bart-large-cnn")
            tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")
        elif model_name == 't5':
            model = T5ForConditionalGeneration.from_pretrained("t5-base")
            tokenizer = AutoTokenizer.from_pretrained("t5-base")
        else:
            raise ValueError(f"Unsupported model: {model_name}")
        
        model = model.to(device)
        logging.info(f"{model_name} model and tokeniser loaded. Using device: {device}")
        return model, tokenizer, device
    except Exception as e:
        logging.error(f"Error loading model and tokeniser: {str(e)}")
        raise

# Function to get answer from model
def get_answer(model, tokenizer, device, question, context, model_name):
    try:
        if model_name == 'mpnet':
            inputs = tokenizer.encode_plus(question, context, add_special_tokens=True, return_tensors="pt", max_length=512, truncation=True, padding='max_length')
            input_ids = inputs["input_ids"].to(device)
            attention_mask = inputs["attention_mask"].to(device)

            with torch.no_grad():
                outputs = model(input_ids, attention_mask=attention_mask)
                answer_start = torch.argmax(outputs.start_logits)
                answer_end = torch.argmax(outputs.end_logits) + 1

            answer = tokenizer.convert_tokens_to_string(tokenizer.convert_ids_to_tokens(input_ids[0][answer_start:answer_end]))
            return answer, answer_start.item(), answer_end.item()
        elif model_name in ['bart', 't5']:
            input_text = f"question: {question} context: {context}"
            inputs = tokenizer.encode(input_text, return_tensors="pt", max_length=1024, truncation=True)
            inputs = inputs.to(device)
            
            with torch.no_grad():
                outputs = model.generate(inputs, max_length=150, num_return_sequences=1, num_beams=4, early_stopping=True)
            
            answer = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return answer, 0, len(answer)  # Return dummy start and end positions
    except Exception as e:
        logging.error(f"Error getting answer: {str(e)}")
        return "", 0, 0

# Function to calculate relevance score
def calculate_relevance_score(answer, question):
    answer_words = set(answer.lower().split())
    question_words = set(question.lower().split())
    return len(answer_words.intersection(question_words))

# Function to post-process answer
def post_process_answer(answer, question):
    # Remove artifacts and question repetition
    answer = re.sub(r'^##\w*', '', answer).strip()
    answer = answer.lower().replace(question.lower(), "", 1).strip()

    # Tokenise the answer into sentences
    sentences = sent_tokenize(answer)

    # Remove sentences that are too short or don't contain relevant information
    filtered_sentences = [s for s in sentences if len(s.split()) > 5 and any(word in s.lower() for word in question.lower().split())]

    # If no relevant sentences found, return the original answer limited to 2 sentences
    if not filtered_sentences:
        return '. '.join(sentences[:2]) + ('.' if len(sentences) > 2 else '')

    # Join the relevant sentences
    relevant_answer = ' '.join(filtered_sentences)

    # Summarise the answer if it's too long
    if len(relevant_answer.split()) > 50:
        relevant_answer = summarize_text(relevant_answer, 2)

    # Ensure the answer is a complete sentence
    relevant_answer = relevant_answer.capitalize()
    if not relevant_answer.endswith('.'):
        relevant_answer += '.'

    return relevant_answer

# Function to summarise text
def summarize_text(text, num_sentences):
    sentences = sent_tokenize(text)
    words = word_tokenize(text.lower())

    stop_words = set(stopwords.words('english'))
    words = [word for word in words if word not in stop_words]

    word_freq = {}
    for word in words:
        if word not in word_freq:
            word_freq[word] = 1
        else:
            word_freq[word] += 1

    sentence_scores = {}
    for i, sentence in enumerate(sentences):
        for word in word_tokenize(sentence.lower()):
            if word in word_freq:
                if i not in sentence_scores:
                    sentence_scores[i] = word_freq[word]
                else:
                    sentence_scores[i] += word_freq[word]

    top_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:num_sentences]
    top_sentences.sort()

    summary = ' '.join([sentences[i] for i in top_sentences])
    return summary

# Function to extract citation
def extract_citation(context, start, end):
    citation_start = max(0, start - 100)
    citation_end = min(len(context), end + 100)
    return context[citation_start:citation_end].strip()

# Function to load and preprocess documents
def load_and_preprocess_documents(anonymized_data_path):
    all_text = []
    for filename in os.listdir(anonymized_data_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(anonymized_data_path, filename)
            logging.info(f"Reading file: {file_path}")
            pdf_text = extract_text_from_pdf(file_path)
            all_text.extend([(preprocess_text(page_text), filename, page_num) for page_text, page_num in pdf_text])
    return all_text

# Function to find best answer
def find_best_answer(model, tokenizer, device, question, all_text, ai_model):
    best_answer = ""
    best_score = float('-inf')
    best_source = ""
    best_page = 0
    best_citation = ""

    for text, source, page_num in all_text:
        window_size = 1000
        stride = 500
        for i in range(0, len(text) - window_size + 1, stride):
            context = text[i:i+window_size]
            answer, start, end = get_answer(model, tokenizer, device, question, context, ai_model)
            
            if answer and len(answer) > 5:
                score = calculate_relevance_score(answer, question)
                if score > best_score:
                    best_answer = answer
                    best_score = score
                    best_source = source
                    best_page = page_num
                    best_citation = extract_citation(context, start, end)

    return best_answer, best_source, best_page, best_citation

# Function to count tokens in a string
def num_tokens_from_string(string: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(string))

# Function to chunk text
def chunk_text(text: str, max_tokens: int = 90000) -> List[str]:
    chunks = []
    current_chunk = ""
    current_chunk_tokens = 0
    
    for paragraph in text.split('\n\n'):
        paragraph_tokens = num_tokens_from_string(paragraph)
        
        if current_chunk_tokens + paragraph_tokens > max_tokens:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
            current_chunk_tokens = paragraph_tokens
        else:
            current_chunk += "\n\n" + paragraph
            current_chunk_tokens += paragraph_tokens
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

# Function to process with Claude
def process_with_claude(api_key: str, questions: List[str], context: str, pdf_info: List[Tuple[str, int, str]]) -> List[Dict[str, str]]:
    client = Anthropic(api_key=api_key)
    chunks = chunk_text(context)
    results = [{
        "question": q,
        "answer": "",
        "source": "",
        "citation": ""
    } for q in questions]

    system_prompt = "You are an AI assistant tasked with answering questions based on the provided context. The context is a chunk of a larger document, so some questions may not have answers in this specific chunk. If you can't find a relevant answer in this chunk, simply state 'No relevant information in this chunk.' and move to the next question. Do not make up information or guess. Always include the source document name and page number in your answer."

    for i, chunk in enumerate(chunks):
        questions_text = "\n".join([f"{j+1}. {q['question']}" for j, q in enumerate(results) if not q['answer']])
        
        # Find the corresponding PDF info for this chunk
        chunk_start = i * 90000  # Assuming 90000 tokens per chunk
        chunk_end = (i + 1) * 90000
        relevant_pdf_info = [info for info in pdf_info if chunk_start <= info[1] < chunk_end]
        
        pdf_info_text = "\n".join([f"Document: {info[0]}, Page: {info[2]}" for info in relevant_pdf_info])
        
        user_message = f"""Context (chunk {i+1} of {len(chunks)}):
{chunk}

PDF Information:
{pdf_info_text}

Questions:
{questions_text}

Please answer each question based solely on the information provided in the context. If the answer is found, provide it along with the specific document name and page number where the information was found. Use the format 'Source: [Document Name], Page: [Page Number]' at the end of each answer."""

        try:
            response = client.messages.create(
                model="claude-3-opus-20240229",
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ],
                max_tokens=3000,
            )
            
            answers = response.content[0].text.strip().split('\n\n')
            for answer in answers:
                if '. ' in answer:
                    question_num, answer_text = answer.split('. ', 1)
                    question_index = int(question_num) - 1
                    if question_index < len(results) and not results[question_index]['answer']:
                        if "No relevant information in this chunk" not in answer_text:
                            # Extract source and page information
                            source_match = re.search(r'Source: (.*?), Page: (\d+)', answer_text)
                            if source_match:
                                source_doc = source_match.group(1)
                                page_num = source_match.group(2)
                                source = f"{source_doc}, Page: {page_num}"
                                # Remove the source information from the answer text
                                answer_text = re.sub(r'Source: .*?, Page: \d+', '', answer_text).strip()
                            else:
                                source = f"Information found in chunk {i+1}"
                            
                            results[question_index]['answer'] = answer_text
                            results[question_index]['source'] = source
                            results[question_index]['citation'] = f"\"{answer_text}\""  # Use the answer as the citation
        
        except Exception as e:
            logging.error(f"Error in Claude API call for chunk {i+1}: {str(e)}")

    # For questions with no answers, keep the default "No relevant information found" response
    for result in results:
        if not result['answer']:
            result['answer'] = "No relevant information found in the provided context."
            result['source'] = "N/A"
            result['citation'] = "No relevant information found in any chunk."

    return results

# Function to format results
def format_results(results: List[Dict[str, str]]) -> str:
    formatted_output = "**Analysis Results**\n"
    for i, result in enumerate(results, 1):
        formatted_output += f"**Question {i}**\n"
        formatted_output += f"**Q:** {result['question']}\n"
        formatted_output += f"**A:** {result['answer']}\n"
        formatted_output += f"**Source:** {result['source']}\n"
        formatted_output += f"**Citation:** {result['citation']}\n\n"
    return formatted_output

# Function to process with ChatGPT
def process_with_chatgpt(api_key: str, questions: List[str], context: str) -> List[Dict[str, str]]:
    openai.api_key = api_key
    results = []
    for question in questions:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant answering questions based on the given context."},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
            ]
        )
        results.append({
            "question": question,
            "answer": response.choices[0].message['content'].strip(),
            "source": "ChatGPT",
            "citation": "Generated by ChatGPT based on the provided context."
        })
    return results

# Main function to process security questions
def process_security_questions(ai_model: str, api_key: str, questions: List[str], anonymized_data_path: str) -> List[Dict[str, str]]:
    logging.info(f"Starting processing with {ai_model} model")
    try:
        all_text = load_and_preprocess_documents(anonymized_data_path)
        if not all_text:
            logging.error("No valid content found in the anonymised data after preprocessing")
            return [{"question": q, "answer": "Error: No valid content available after preprocessing.", "source": "N/A", "citation": "N/A"} for q in questions]

        context = ""
        pdf_info = []
        token_count = 0
        for text, filename, page_num in all_text:
            context += text + " "
            pdf_info.append((filename, token_count, page_num))
            token_count += len(text.split())

        if ai_model == 'claude':
            return process_with_claude(api_key, questions, context, pdf_info)
        elif ai_model == 'chatgpt':
            return process_with_chatgpt(api_key, questions, context)
        else:
            model, tokenizer, device = load_model_and_tokenizer(ai_model)
            all_results = []
            for question in questions:
                logging.info(f"Processing question: {question}")
                best_answer, best_source, best_page, best_citation = find_best_answer(model, tokenizer, device, question, all_text, ai_model)
                
                processed_answer = post_process_answer(best_answer, question)
                formatted_citation = f"\"<i>{best_citation}</i>\""
                
                result = {
                    "question": question,
                    "answer": processed_answer if processed_answer else "No relevant answer found in the provided documents.",
                    "source": f"{best_source}, Page: {best_page}" if best_source else "N/A",
                    "citation": formatted_citation if best_citation else "N/A"
                }
                
                all_results.append(result)

            logging.info("All questions processed successfully")
            return all_results

    except Exception as e:
        logging.error(f"Error in process_security_questions: {str(e)}")
        logging.error(traceback.format_exc())
        return [{"question": q, "answer": f"Error: {str(e)}", "source": "N/A", "citation": "N/A"} for q in questions]

# Function to get TinyBERT progress
def get_tinybert_progress():
    return 100.0