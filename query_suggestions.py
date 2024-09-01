from fastapi import APIRouter, HTTPException
from cachetools import TTLCache
from typing import List
import logging
from security_questions_data import SECURITY_QUESTIONS

# Set up router, cache, and logger
router = APIRouter()
cache = TTLCache(maxsize=1000, ttl=3600)  # Cache for 1 hour
logger = logging.getLogger(__name__)

def get_suggestions(partial_input: str) -> List[str]:
    # Find matching questions based on partial input
    partial_input = partial_input.lower()
    return [q for q in SECURITY_QUESTIONS if partial_input in q.lower()]

@router.get("/suggest_questions")
async def suggest_questions(partial_input: str) -> dict:
    # Return empty list for short inputs
    if len(partial_input) < 3:
        return {"suggestions": []}
    
    try:
        # Return cached results if available
        if partial_input in cache:
            logger.info(f"Cache hit for query: {partial_input}")
            return {"suggestions": cache[partial_input]}
        
        # Generate and cache new suggestions
        suggestions = get_suggestions(partial_input)[:5]  # Limit to 5 suggestions
        cache[partial_input] = suggestions
        logger.info(f"Generated suggestions for query: {partial_input}")
        return {"suggestions": suggestions}
    except Exception as e:
        # Log error and raise HTTP exception
        logger.error(f"Error generating suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")