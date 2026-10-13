package com.eykon.memory.ml.vision

/**
 * CLIP's text tokenizer (the one MobileCLIP uses), in plain Kotlin: words are split into
 * sub-word pieces by merging the most common neighbouring pairs first, and each piece is a
 * number. It follows open_clip's SimpleTokenizer; the unit test compares it with that
 * tokenizer's output for the same sentences.
 *
 * [merges] are the merge rules, most common first, one "left right" pair per line
 * (assets/clip_bpe_merges.txt, from OpenAI CLIP's vocabulary).
 */
class ClipTokenizer(merges: List<String>) {

    private val rank = HashMap<Pair<String, String>, Int>(merges.size * 2)
    private val ids = HashMap<String, Int>(merges.size * 2)
    private val byteChar = CharArray(256)

    init {
        // Every byte gets a printable character; the 68 unprintable ones are moved above 255.
        val printable = (33..126) + (161..172) + (174..255)
        var next = 256
        val order = ArrayList<Int>(printable)
        for (b in printable) byteChar[b] = b.toChar()
        for (b in 0..255) if (b !in printable) { byteChar[b] = (next++).toChar(); order.add(b) }

        // Ids: the 256 characters, the same 256 as word endings, then one per merge rule.
        order.forEachIndexed { i, b -> ids[byteChar[b].toString()] = i }
        order.forEachIndexed { i, b -> ids[byteChar[b] + END] = 256 + i }
        merges.forEachIndexed { i, line ->
            val space = line.indexOf(' ')
            val pair = line.substring(0, space) to line.substring(space + 1)
            rank[pair] = i
            ids[pair.first + pair.second] = 512 + i
        }
        check(512 + merges.size == START) { "expected ${START - 512} merge rules, got ${merges.size}" }
    }

    /** [LENGTH] numbers: start marker, the pieces, end marker, then zeros. Longer text is cut. */
    fun encode(text: String): LongArray {
        val pieces = ArrayList<Int>()
        pieces.add(START)
        val clean = text.trim().replace(Regex("\\s+"), " ").lowercase()
        for (word in WORDS.findAll(clean)) {
            val mapped = word.value.toByteArray(Charsets.UTF_8).map { byteChar[it.toInt() and 0xFF].toString() }
            split(mapped).forEach { pieces.add(ids.getValue(it)) }
        }
        pieces.add(END_ID)
        val out = LongArray(LENGTH)
        for (i in 0 until minOf(pieces.size, LENGTH)) out[i] = pieces[i].toLong()
        if (pieces.size > LENGTH) out[LENGTH - 1] = END_ID.toLong()
        return out
    }

    /** Merge neighbouring pieces, most common pair first, until no known pair is left. */
    private fun split(characters: List<String>): List<String> {
        var word = characters.dropLast(1) + (characters.last() + END)
        while (word.size > 1) {
            val best = (0 until word.size - 1).map { word[it] to word[it + 1] }.minBy { rank[it] ?: Int.MAX_VALUE }
            if (best !in rank) break
            val merged = ArrayList<String>(word.size)
            var i = 0
            while (i < word.size) {
                if (i < word.size - 1 && word[i] == best.first && word[i + 1] == best.second) {
                    merged.add(best.first + best.second)
                    i += 2
                } else {
                    merged.add(word[i])
                    i++
                }
            }
            word = merged
        }
        return word
    }

    companion object {
        const val LENGTH = 77
        const val START = 49406
        const val END_ID = 49407
        private const val END = "</w>"
        // an ending like 's or 't, or a run of letters, or one digit, or a run of anything else that is not a space
        private val WORDS = Regex("'s|'t|'re|'ve|'m|'ll|'d|[\\p{L}]+|[\\p{N}]|[^\\s\\p{L}\\p{N}]+")
    }
}
