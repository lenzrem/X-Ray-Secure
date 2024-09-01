import random
from SPARQLWrapper import SPARQLWrapper, JSON

def query_wikidata(query: str) -> list:
    """
    Executes a SPARQL query on the Wikidata endpoint.
    
    Args:
        query (str): The SPARQL query to execute.
    
    Returns:
        list: The query results.
    """
    endpoint = "https://query.wikidata.org/sparql"
    sparql = SPARQLWrapper(endpoint)
    sparql.addCustomHttpHeader("User-Agent", "Mozilla/5.0 (compatible; MyApp/1.0; mailto:your-email@example.com)")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        print(f"Error querying Wikidata: {e}")
        return []

def generate_security_questions(num_questions: int = 50) -> list:
    """
    Generates security-related questions using Wikidata concepts.
    
    Args:
        num_questions (int): The number of questions to generate.
    
    Returns:
        list: Generated security questions.
    """
    query = """
    SELECT DISTINCT ?item ?itemLabel WHERE {
      {?item wdt:P31/wdt:P279* wd:Q870364.}  # Instance or subclass of "computer security"
      UNION
      {?item wdt:P31/wdt:P279* wd:Q21198.}   # Instance or subclass of "computer science"
      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    }
    LIMIT 1000
    """
    print("Executing SPARQL query...")
    results = query_wikidata(query)
    print(f"Query returned {len(results)} results.")
    
    concepts = [(result["item"]["value"], result["itemLabel"]["value"]) for result in results]
    print(f"Extracted {len(concepts)} concepts.")
    
    if not concepts:
        print("No concepts found. Cannot generate questions.")
        return []
    
    question_templates = [
        "How does your organisation implement {concept} in its security strategy?",
        "What measures are in place to protect against {concept}-related threats?",
        "Describe your organisation's approach to managing {concept} in your security infrastructure.",
        "How often does your organisation review and update its {concept} policies?",
        "What tools or technologies does your organisation use to address {concept} in its security framework?",
        "How do you ensure compliance with {concept} regulations in your security practices?",
        "What training do employees receive regarding {concept} in your organisation?",
        "How does your incident response plan address {concept}-related issues?",
        "What metrics do you use to evaluate the effectiveness of your {concept} measures?",
        "How does your organisation stay updated on emerging threats related to {concept}?"
    ]
    
    questions = set()
    while len(questions) < num_questions and concepts:
        concept_uri, concept_label = random.choice(concepts)
        template = random.choice(question_templates)
        question = template.format(concept=concept_label)
        questions.add(question)
    
    return list(questions)

if __name__ == "__main__":
    print("Generating cybersecurity questions using Linked Open Data from Wikidata...")
    questions = generate_security_questions()
    
    if not questions:
        print("No questions could be generated. Please check the SPARQL query and the Wikidata endpoint.")
    else:
        print(f"\nGenerated {len(questions)} questions:\n")
        for i, question in enumerate(questions, 1):
            print(f"{i}. {question}")

        with open("generated_security_questions.txt", "w", encoding="utf-8") as f:
            for question in questions:
                f.write(question + "\n")
        print("\nQuestions have been saved to 'generated_security_questions.txt'")