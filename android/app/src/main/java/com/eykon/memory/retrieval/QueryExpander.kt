package com.eykon.memory.retrieval

object QueryExpander {
    private val conceptMap = mapOf(
        "morning" to "wake alarm routine breakfast bus shuttle early",
        "financial" to "money rupees allowance budget expenses save cost price",
        "dentist" to "teeth tooth doctor medical appointment health clinic",
        "health" to "doctor medical fitness exercise gym running sick ill",
        "work" to "office job career task meeting boss colleague project",
        "family" to "mom dad sister brother parents relatives home",
        "travel" to "flight ticket hotel trip journey vacation train bus",
        "food" to "eat dinner lunch breakfast restaurant snack meal cook",
        "shopping" to "buy store grocery clothes mall supermarket",
        "study" to "exam university college learn read book class course"
    )

    fun expand(query: String): String {
        val lowerQuery = query.lowercase()
        var expanded = query
        for ((key, value) in conceptMap) {
            if (lowerQuery.contains(key)) {
                expanded += " $value"
            }
        }
        return expanded
    }
}
