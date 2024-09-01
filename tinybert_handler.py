# Excluded TinyBERT from main functionality, due to bad performance

import os
import logging
import time
from typing import List, Dict
from transformers import AutoTokenizer, AutoModelForQuestionAnswering, Trainer, TrainingArguments
from datasets import Dataset
from torch.utils.data import DataLoader
from multiprocessing import Process, Value, Lock

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TinyBERTHandler:
    def __init__(self):
        self.model_name = "huawei-noah/TinyBERT_General_4L_312D"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForQuestionAnswering.from_pretrained(self.model_name)
        self.fine_tuned_model_path = "./fine_tuned_tinybert"
        self.progress = Value('d', 0.0)
        self.lock = Lock()
        self.process = None

    def prepare_training_data(self, anonymised_pdfs: List[str]) -> Dataset:
        # Create a simple dataset from PDF contents
        training_data = [
            {
                "context": pdf_content,
                "question": "What is this document about?",
                "answer": "This is a placeholder answer"
            } for pdf_content in anonymised_pdfs
        ]
        return Dataset.from_dict({
            "context": [item["context"] for item in training_data],
            "question": [item["question"] for item in training_data],
            "answer": [item["answer"] for item in training_data]
        })

    def start_fine_tuning(self, anonymised_pdfs: List[str]):
        # Start the fine-tuning process in a separate process
        self.process = Process(target=self._fine_tune, args=(anonymised_pdfs,))
        self.process.start()

    def _fine_tune(self, anonymised_pdfs: List[str]):
        # Perform the actual fine-tuning
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

        class ProgressCallback:
            def __init__(self, progress, lock):
                self.progress = progress
                self.lock = lock

            def on_train_begin(self, args, state, control, **kwargs):
                with self.lock:
                    self.progress.value = 0.0

            def on_epoch_end(self, args, state, control, **kwargs):
                with self.lock:
                    self.progress.value = (state.epoch / args.num_train_epochs) * 100

        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            callbacks=[ProgressCallback(self.progress, self.lock)],
        )

        trainer.train()
        self.model.save_pretrained(self.fine_tuned_model_path)
        self.tokenizer.save_pretrained(self.fine_tuned_model_path)
        logging.info("TinyBERT fine-tuning complete")

        with self.lock:
            self.progress.value = 100.0

    def get_progress(self):
        # Get the current progress of fine-tuning
        with self.lock:
            return self.progress.value

    def is_fine_tuning_complete(self):
        # Check if fine-tuning is complete
        return self.get_progress() == 100.0

    def answer_questions(self, questions: List[str], context: str) -> List[Dict[str, str]]:
        # Answer questions using the fine-tuned model
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

# Create a global instance of TinyBERTHandler
tinybert_handler = TinyBERTHandler()

def start_tinybert_fine_tuning(anonymised_pdfs: List[str]):
    # Start the fine-tuning process
    tinybert_handler.start_fine_tuning(anonymised_pdfs)

def get_tinybert_fine_tuning_progress():
    # Get the current progress of fine-tuning
    return tinybert_handler.get_progress()

def is_tinybert_fine_tuning_complete():
    # Check if fine-tuning is complete
    return tinybert_handler.is_fine_tuning_complete()

def process_with_tinybert(questions: List[str], anonymised_pdfs: List[str]) -> List[Dict[str, str]]:
    # Process questions using TinyBERT
    if not os.path.exists(tinybert_handler.fine_tuned_model_path):
        start_tinybert_fine_tuning(anonymised_pdfs)
        while not is_tinybert_fine_tuning_complete():
            progress = get_tinybert_fine_tuning_progress()
            logging.info(f"Fine-tuning progress: {progress:.2f}%")
            time.sleep(5)  # Wait for 5 seconds before checking again
    
    # Combine all PDFs into a single context for answering
    combined_context = " ".join(anonymised_pdfs)
    
    # Answer the questions
    return tinybert_handler.answer_questions(questions, combined_context)