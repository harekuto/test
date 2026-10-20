package dev.harekuto.echotranscript

import android.content.Context
import android.net.Uri
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

data class ModelChoice(val name: String, val filename: String, val minBytes: Long, val display: String) {
    val url: String get() = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$filename"
}

class ModelManager(context: Context) {
    private val directory = File(context.filesDir, "models").apply { mkdirs() }
    val choices = listOf(
        ModelChoice("tiny", "ggml-tiny.bin", 65L * 1024 * 1024, "Tiny • 75 МБ • быстро"),
        ModelChoice("base", "ggml-base.bin", 115L * 1024 * 1024, "Base • 142 МБ • точнее"),
        ModelChoice("small", "ggml-small.bin", 430L * 1024 * 1024, "Small • 466 МБ • медленно")
    )

    fun get(choice: ModelChoice): File = File(directory, choice.filename)

    fun valid(choice: ModelChoice): Boolean = validate(get(choice), choice)
    private fun validate(file: File, choice: ModelChoice): Boolean {
        if (!file.isFile || file.length() < choice.minBytes) return false
        return runCatching {
            FileInputStream(file).use {
                val magic = ByteArray(4)
                it.read(magic) == 4 && String(magic, Charsets.US_ASCII) == "ggml"
            }
        }.getOrDefault(false)
    }

    fun importModel(context: Context, uri: Uri, choice: ModelChoice) {
        val tmp = File(directory, choice.filename + ".incoming")
        try {
            context.contentResolver.openInputStream(uri).use { source ->
                if (source == null) throw IOException("Невозможно открыть модель")
                FileOutputStream(tmp).buffered().use { out -> source.copyTo(out) }
            }
            if (!validate(tmp, choice)) throw IOException("Неверный GGML-файл для выбранной модели")
            val output = get(choice)
            if (output.exists() && !output.delete()) throw IOException("Невозможно заменить предыдущую модель")
            if (!tmp.renameTo(output)) throw IOException("Ошибка сохранения модели")
        } finally {
            if (tmp.exists()) tmp.delete()
        }
    }

    fun download(choice: ModelChoice, shouldStop: () -> Boolean, progress: (String) -> Unit) {
        if (valid(choice)) {
            progress("Модель уже загружена")
            return
        }
        val target = get(choice)
        val partial = File(directory, choice.filename + ".part")
        var existing = partial.length()
        var conn: HttpURLConnection? = null
        try {
            val connection = URL(choice.url).openConnection() as HttpURLConnection
            conn = connection
            connection.connectTimeout = 25_000
            connection.readTimeout = 45_000
            connection.instanceFollowRedirects = true
            connection.setRequestProperty("Accept-Encoding", "identity")
            if (existing > 0L) connection.setRequestProperty("Range", "bytes=$existing-")
            val status = connection.responseCode
            if (status !in listOf(200, 206)) throw IOException("HTTP $status при загрузке модели")
            if (status == 200) existing = 0L
            val total = connection.contentLengthLong.takeIf { it > 0 }?.plus(existing) ?: -1L
            connection.inputStream.use { input ->
                FileOutputStream(partial, existing > 0).buffered(128 * 1024).use { out ->
                    val buf = ByteArray(128 * 1024)
                    var current = existing
                    var lastReport = 0L
                    while (true) {
                        if (shouldStop()) throw InterruptedException("Загрузка прервана")
                        val n = input.read(buf)
                        if (n < 0) break
                        out.write(buf, 0, n)
                        current += n
                        val now = android.os.SystemClock.elapsedRealtime()
                        if (now - lastReport >= 500L) {
                            val statusText = if (total > 0) {
                                "Модель: ${current / 1_048_576} / ${total / 1_048_576} МБ (${current * 100 / total}%)"
                            } else "Загружено ${current / 1_048_576} МБ"
                            progress(statusText)
                            lastReport = now
                        }
                    }
                }
            }
            if (!validate(partial, choice)) throw IOException("Загруженная модель повреждена или неполная")
            if (target.exists() && !target.delete()) throw IOException("Невозможно заменить модель")
            if (!partial.renameTo(target)) throw IOException("Не удалось записать модель")
            progress("Модель готова: ${choice.name}")
        } finally {
            conn?.disconnect()
        }
    }
}
