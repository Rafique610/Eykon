"""Query expansion module for retrieval augmentation."""
from __future__ import annotations

# Static concept map for expanding abstract terms into concrete retrieval keywords.
# This bridges the vocabulary gap between semantic queries and concrete stored memories.
CONCEPT_MAP = {
    "morning": "wake alarm routine breakfast bus shuttle early",
    "financial": "money rupees allowance budget expenses save cost price",
    "comfort": "money budget afford struggle save expense",
    "stress": "deadline assignment exam pressure sleep tired overwhelmed",
    "cope": "manage handle sleep tea assignment deadline",
    "social": "friends group cricket team study hang out",
    "active": "sport cricket exercise walk activity hobby game",
    "struggle": "difficult hard grade fail low mark exam",
    "free time": "weekend hobby game read cricket evening relax",
    "sleep": "night hours bed alarm wake tired rest",
    "eat": "food meal lunch dinner breakfast cafeteria canteen",
    "habit": "routine daily morning evening regular pattern",
    "health": "sleep eat sick fever clinic exercise stress tired",
    "hobby": "game cricket read book play weekend evening",
    "study": "library notes revision exam prepare homework",
    "transport": "bus shuttle rickshaw walk ride morning commute",
    "room": "hostel room floor bed desk window furniture",
    "friend": "omar hassan zara bilal classmate roommate group",
    "professor": "sir mam teacher class lecture office hours grade",
    "project": "fyp thesis model training experiment report supervisor",
}

def expand_query(query: str) -> str:
    """Append semantically related concrete terms to abstract queries.
    
    If any keyword from the CONCEPT_MAP is found in the query, its associated
    concrete terms are appended to improve retrieval recall.
    """
    lower_query = query.lower()
    expansions = []
    
    for concept, related_terms in CONCEPT_MAP.items():
        if concept in lower_query:
            expansions.append(related_terms)
            
    if not expansions:
        return query
        
    return f"{query} {' '.join(expansions)}"
