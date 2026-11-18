package com.eykon.memory.video

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MakerSettingsTest {

    @Test
    fun theTeamsPhonesGetTheRightHint() {
        // Build.MANUFACTURER as our phones report it: the A32, the Infinix, the Pixel
        assertTrue(MakerSettings.hint("samsung")!!.contains("Sleeping"))
        assertTrue(MakerSettings.hint("INFINIX")!!.contains("Auto-start management"))
        assertNull(MakerSettings.hint("Google"))
    }

    @Test
    fun everyTranssionAndXiaomiBrandIsCoveredWhateverItsCase() {
        for (maker in listOf("Xiaomi", "Redmi", "POCO", "TECNO", "Infinix", "itel")) assertNotNull(maker, MakerSettings.hint(maker))
        assertEquals(MakerSettings.hint("xiaomi"), MakerSettings.hint(" Xiaomi "))
    }
}
