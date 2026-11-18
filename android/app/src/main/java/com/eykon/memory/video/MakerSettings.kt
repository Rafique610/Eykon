package com.eykon.memory.video

/**
 * EYKO-122: some phone makers stop background work beyond what Android does, and there is no API to change that; only the person
 * can, in the maker's own settings. Paths from dontkillmyapp.com (Samsung, Xiaomi, Tecno pages); the Infinix reboot check
 * (EYKO-44 check D) matches the Tecno page. docs/research/2026-11-16-head3-background-and-limits.md has the quotes.
 */
object MakerSettings {

    /** What to change on a phone from [manufacturer] (`Build.MANUFACTURER`), or null when the maker needs nothing extra. */
    fun hint(manufacturer: String): String? = when (manufacturer.trim().lowercase()) {
        "samsung" ->
            "Samsung phones put apps to sleep. So videos keep processing with Eykon closed: Settings, Apps, Eykon, Battery, " +
                "\"Unrestricted\". Also check Eykon is not in Battery, Background usage limits, Sleeping or Deep sleeping apps."
        "xiaomi", "redmi", "poco" ->
            "Xiaomi phones stop background work by default. So videos keep processing with Eykon closed: Settings, Apps, Eykon, " +
                "turn on Autostart, and set Battery saver to \"No restrictions\"."
        "tecno", "infinix", "itel" ->
            "This phone stops apps in the background. So videos keep processing with Eykon closed: Phone Master, Toolbox, " +
                "Auto-start management, allow Eykon; and in Settings, Apps, Eykon, Battery, choose \"Unrestricted\"."
        else -> null
    }
}
