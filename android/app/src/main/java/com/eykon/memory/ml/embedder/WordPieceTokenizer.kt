package com.eykon.memory.ml.embedder

import java.text.Normalizer

/**
 * The tokenizer bge-small-en-v1.5 was trained with (BERT's, lower-case), in plain Kotlin:
 * text is lower-cased, accents are dropped, punctuation is split off, and each word is cut
 * into the longest pieces found in the vocabulary. The unit test compares it with the
 * laptop tokenizer's output for the same sentences.
 *
 * [vocabulary] is assets/bge_vocab.txt, one piece per line; a piece's line number is its id.
 */
class WordPieceTokenizer(vocabulary: List<String>) {

    private val ids = HashMap<String, Int>(vocabulary.size * 2).apply { vocabulary.forEachIndexed { i, piece -> put(piece, i) } }
    private val unknown = ids.getValue("[UNK]")
    private val start = ids.getValue("[CLS]")
    private val end = ids.getValue("[SEP]")

    /** Start marker, the pieces, end marker. Longer text is cut to [MAX_LENGTH]. */
    fun encode(text: String): LongArray {
        val pieces = ArrayList<Int>()
        for (word in words(text)) {
            pieces.addAll(split(word))
            if (pieces.size >= MAX_LENGTH - 2) break
        }
        return (listOf(start) + pieces.take(MAX_LENGTH - 2) + end).map { it.toLong() }.toLongArray()
    }

    /** Lower-case words with accents dropped; every punctuation mark is a word of its own. */
    private fun words(text: String): List<String> {
        val plain = Normalizer.normalize(text.lowercase(), Normalizer.Form.NFD)
        val out = ArrayList<String>()
        val current = StringBuilder()
        fun flush() { if (current.isNotEmpty()) { out.add(current.toString()); current.clear() } }
        var i = 0
        while (i < plain.length) {
            val code = plain.codePointAt(i)
            i += Character.charCount(code)
            val type = Character.getType(code)
            when {
                type == Character.NON_SPACING_MARK.toInt() -> Unit // the accent itself
                code == 0 || code == 0xFFFD || (type == Character.CONTROL.toInt() && !Character.isWhitespace(code)) || type == Character.FORMAT.toInt() -> Unit
                Character.isWhitespace(code) || type == Character.SPACE_SEPARATOR.toInt() -> flush()
                isPunctuation(code, type) || isCjk(code) -> { flush(); out.add(String(Character.toChars(code))) }
                else -> current.appendCodePoint(code)
            }
        }
        flush()
        return out
    }

    /** The longest piece first, then the longest continuation ("##...") of what is left. */
    private fun split(word: String): List<Int> {
        if (word.length > MAX_WORD) return listOf(unknown)
        val found = ArrayList<Int>()
        var from = 0
        while (from < word.length) {
            var to = word.length
            var id: Int? = null
            while (to > from) {
                id = ids[(if (from > 0) "##" else "") + word.substring(from, to)]
                if (id != null) break
                to--
            }
            if (id == null) return listOf(unknown)
            found.add(id)
            from = to
        }
        return found
    }

    private fun isPunctuation(code: Int, type: Int): Boolean =
        code in 33..47 || code in 58..64 || code in 91..96 || code in 123..126 ||
            type == Character.CONNECTOR_PUNCTUATION.toInt() || type == Character.DASH_PUNCTUATION.toInt() ||
            type == Character.START_PUNCTUATION.toInt() || type == Character.END_PUNCTUATION.toInt() ||
            type == Character.INITIAL_QUOTE_PUNCTUATION.toInt() || type == Character.FINAL_QUOTE_PUNCTUATION.toInt() ||
            type == Character.OTHER_PUNCTUATION.toInt()

    private fun isCjk(code: Int): Boolean =
        code in 0x4E00..0x9FFF || code in 0x3400..0x4DBF || code in 0x20000..0x2A6DF || code in 0x2A700..0x2B73F ||
            code in 0x2B740..0x2B81F || code in 0x2B820..0x2CEAF || code in 0xF900..0xFAFF || code in 0x2F800..0x2FA1F

    companion object {
        const val MAX_LENGTH = 512
        private const val MAX_WORD = 100
    }
}
