package dev.harekuto.echotranscript

object TranscriptFormat {
    fun clock(ms: Long): String {
        val secs = (ms.coerceAtLeast(0) / 1000)
        return "%02d:%02d:%02d".format(java.util.Locale.US, secs / 3600, secs / 60 % 60, secs % 60)
    }
    fun srtClock(ms: Long): String = "%s,%03d".format(
        java.util.Locale.US, clock(ms), ms.coerceAtLeast(0) % 1000)
    fun displayName(original: String): String =
        original.substringAfterLast('/').substringAfterLast('\\').replace(Regex("[\\r\\n\\t]"), " ").take(150)
}
