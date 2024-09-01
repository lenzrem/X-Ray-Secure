from SPARQLWrapper import SPARQLWrapper, JSON

def query_endpoint(endpoint_url: str, query: str) -> list:
    """
    Executes a SPARQL query on the specified endpoint.
    
    Args:
        endpoint_url (str): The URL of the SPARQL endpoint.
        query (str): The SPARQL query to execute.
    
    Returns:
        list: The query results.
    """
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        return results["results"]["bindings"]
    except Exception as e:
        print(f"Error querying {endpoint_url}: {e}")
        return []

def test_dbpedia_connection():
    """Tests the connection to DBpedia and runs a sample query."""
    endpoint = "https://dbpedia.org/sparql"
    query = """
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT DISTINCT ?concept ?label WHERE {
      ?concept a dbo:Concept ;
               rdfs:label ?label .
      ?concept dct:subject/skos:broader* <http://dbpedia.org/resource/Category:Computer_security> .
      FILTER(LANG(?label) = 'en')
    } LIMIT 10
    """
    sparql = SPARQLWrapper(endpoint)
    sparql.addCustomHttpHeader("User-Agent", "Mozilla/5.0 (compatible; MyApp/1.0; mailto:your-email@example.com)")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        print(f"DBpedia test query returned {len(results['results']['bindings'])} results:")
        for result in results['results']['bindings']:
            print(f"{result['label']['value']} ({result['concept']['value']})")
    except Exception as e:
        print(f"Error querying DBpedia: {e}")

def test_wikidata_connection():
    """Tests the connection to Wikidata and runs a sample query."""
    endpoint = "https://query.wikidata.org/sparql"
    query = """
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31 wd:Q3966.  # Instance of "computer software"
      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    } LIMIT 10
    """
    sparql = SPARQLWrapper(endpoint)
    sparql.addCustomHttpHeader("User-Agent", "Mozilla/5.0 (compatible; MyApp/1.0; mailto:your-email@example.com)")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        results = sparql.query().convert()
        print(f"\nWikidata test query returned {len(results['results']['bindings'])} results:")
        for result in results['results']['bindings']:
            print(f"{result['itemLabel']['value']} ({result['item']['value']})")
    except Exception as e:
        print(f"Error querying Wikidata: {e}")

if __name__ == "__main__":
    print("Testing connection to SPARQL endpoints...")
    print("\nTesting DBpedia:")
    test_dbpedia_connection()
    print("\nTesting Wikidata:")
    test_wikidata_connection()