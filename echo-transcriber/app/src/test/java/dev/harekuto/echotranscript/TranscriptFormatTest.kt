package dev.harekuto.echotranscript

import org.junit.Assert.assertEquals
import org.junit.Test

class TranscriptFormatTest {
    @Test fun hoursMinutesSeconds() = assertEquals("01:02:03", TranscriptFormat.clock(3723456))
    @Test fun millisecondsSrt() = assertEquals("00:00:02,125", TranscriptFormat.srtClock(2125))
    @Test fun safeFilename() = assertEquals("voice.m4a", TranscriptFormat.displayName("C:\\foo\\voice.m4a"))
}
