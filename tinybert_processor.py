# Excluded TinyBERT from main functionality, due to bad performance

import os
import logging
from typing import List, Dict
from transformers import AutoTokenizer, AutoModelForQuestionAnswering, Trainer, TrainingArguments
from datasets import Dataset
from torch.utils.data import DataLoader

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TinyBERTProcessor:
    def __init__(self):
        # Initialise TinyBERT model and tokeniser
        self.model_name = "huawei-noah/TinyBERT_General_4L_312D"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForQuestionAnswering.from_pretrained(self.model_name)
        self.fine_tuned_model_path = "./fine_tuned_tinybert"

    def prepare_training_data(self, anonymised_pdfs: List[str]) -> Dataset:
        # Create a simplified dataset from anonymised PDFs
        training_data = []
        for pdf_content in anonymised_pdfs:
            training_data.append({
                "context": pdf_content,
                "question": "What is this document about?",
                "answer": "This is a placeholder answer"
            })
        return Dataset.from_dict({
            "context": [item["context"] for item in training_data],
            "question": [item["question"] for item in training_data],
            "answer": [item["answer"] for item in training_data]
        })

    def fine_tune(self, anonymised_pdfs: List[str]):
        # Fine-tune TinyBERT model on anonymised PDFs
        logging.info("Starting TinyBERT fine-tuning process")
        dataset = self.prepare_training_data(anonymised_pdfs)
        
        training_args = TrainingArguments(
            output_dir="./results",
            num_train_epochs=3,
            per_device_train_batch_size=8,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir="./logs",
        )

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
        )

        trainer.train()
        self.model.save_pretrained(self.fine_tuned_model_path)
        self.tokenizer.save_pretrained(self.fine_tuned_model_path)
        logging.info("TinyBERT fine-tuning complete")

    def answer_questions(self, questions: List[str], context: str) -> List[Dict[str, str]]:
        # Answer questions using the fine-tuned TinyBERT model
        logging.info("Answering questions with fine-tuned TinyBERT")
        if not os.path.exists(self.fine_tuned_model_path):
            raise ValueError("Fine-tuned model not found. Please run fine-tuning first.")

        self.model = AutoModelForQuestionAnswering.from_pretrained(self.fine_tuned_model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(self.fine_tuned_model_path)

        results = []
        for question in questions:
            inputs = self.tokenizer(question, context, return_tensors="pt")
            outputs = self.model(**inputs)
            answer_start = outputs.start_logits.argmax()
            answer_end = outputs.end_logits.argmax() + 1
            answer = self.tokenizer.decode(inputs["input_ids"][0][answer_start:answer_end])
            results.append({"question": question, "answer": answer})

        return results

def process_with_tinybert(questions: List[str], anonymised_pdfs: List[str]) -> List[Dict[str, str]]:
    # Process questions using TinyBERT on anonymised PDFs
    processor = TinyBERTProcessor()
    
    # Fine-tune the model if not already done
    if not os.path.exists(processor.fine_tuned_model_path):
        processor.fine_tune(anonymised_pdfs)
    
    # Combine all PDFs into a single context
    combined_context = " ".join(anonymised_pdfs)
    
    # Answer the questions
    return processor.answer_questions(questions, combined_context)