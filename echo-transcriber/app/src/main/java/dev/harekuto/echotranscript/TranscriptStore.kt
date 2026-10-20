package dev.harekuto.echotranscript

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream
import java.util.UUID
import java.util.zip.ZipInputStream

data class TranscriptSegment(val startMs: Long, val endMs: Long, val text: String)

data class TranscriptJob(
    val id: String,
    val name: String,
    val audioPath: String,
    val createdAt: Long,
    var model: String = "",
    var language: String = "",
    var nextChunk: Int = 0,
    var totalChunks: Int = 0,
    var durationMs: Long = 0L,
    val segments: MutableList<TranscriptSegment> = mutableListOf()
) {
    val completed: Boolean get() = totalChunks > 0 && nextChunk >= totalChunks
    fun asText(): String = buildString {
        append("Audio: ").append(name).append('\n')
        append("Model: ").append(model).append(" | Language: ").append(language).append('\n')
        append("Progress: ").append(nextChunk).append("/").append(totalChunks).append("\n\n")
        for (s in segments) append('[').append(TranscriptFormat.clock(s.startMs))
            .append("] ").append(s.text.trim()).append('\n')
    }
    fun asSrt(): String = buildString {
        segments.forEachIndexed { i, s ->
            append(i + 1).append('\n')
            append(TranscriptFormat.srtClock(s.startMs)).append(" --> ")
                .append(TranscriptFormat.srtClock(s.endMs.coerceAtLeast(s.startMs + 1000)))
                .append('\n')
            append(s.text.trim()).append("\n\n")
        }
    }
}

class TranscriptStore(private val context: Context) {
    private val inputDir = File(context.filesDir, "audio").apply { mkdirs() }
    private val jobDir = File(context.filesDir, "jobs").apply { mkdirs() }
    val cacheDir = File(context.cacheDir, "transcription").apply { mkdirs() }

    fun findAll(): List<TranscriptJob> = jobDir.listFiles()
        ?.filter { it.isFile && it.extension == "json" }
        ?.mapNotNull { runCatching { decode(JSONObject(it.readText(Charsets.UTF_8))) }.getOrNull() }
        ?.sortedByDescending { it.createdAt } ?: emptyList()

    fun save(job: TranscriptJob) {
        val json = JSONObject()
        json.put("id", job.id).put("name", job.name).put("audioPath", job.audioPath)
        json.put("createdAt", job.createdAt).put("model", job.model).put("language", job.language)
        json.put("nextChunk", job.nextChunk).put("totalChunks", job.totalChunks)
        json.put("durationMs", job.durationMs)
        val segments = JSONArray()
        job.segments.forEach {
            segments.put(JSONObject().put("startMs", it.startMs).put("endMs", it.endMs).put("text", it.text))
        }
        json.put("segments", segments)
        val atomic = AtomicFile(File(jobDir, job.id + ".json"))
        val stream = atomic.startWrite()
        try {
            stream.write(json.toString().toByteArray(Charsets.UTF_8))
            stream.flush()
            atomic.finishWrite(stream)
        } catch (e: Exception) {
            atomic.failWrite(stream)
            throw e
        }
    }

    private fun decode(j: JSONObject): TranscriptJob {
        val segments = mutableListOf<TranscriptSegment>()
        val arr = j.optJSONArray("segments") ?: JSONArray()
        for (i in 0 until arr.length()) {
            val segment = arr.getJSONObject(i)
            segments.add(TranscriptSegment(
                segment.getLong("startMs"), segment.getLong("endMs"), segment.getString("text")
            ))
        }
        return TranscriptJob(
            j.getString("id"), j.getString("name"), j.getString("audioPath"),
            j.getLong("createdAt"), j.optString("model"), j.optString("language"),
            j.optInt("nextChunk"), j.optInt("totalChunks"), j.optLong("durationMs"), segments
        )
    }

    private fun supported(name: String): Boolean =
        listOf(".m4a", ".aac", ".mp3", ".wav", ".flac", ".ogg", ".oga", ".mp4", ".3gp")
            .any { name.lowercase(java.util.Locale.ROOT).endsWith(it) }

    fun import(uri: Uri, update: (String) -> Unit): List<TranscriptJob> {
        val originalName = queryName(uri)
        val imported = mutableListOf<TranscriptJob>()
        context.contentResolver.openInputStream(uri).use { stream ->
            requireNotNull(stream) { "Не удалось прочитать выбранный файл" }
            if (originalName.endsWith(".zip", ignoreCase = true)) {
                val zip = ZipInputStream(stream.buffered())
                var totalBytes = 0L
                var count = 0
                while (true) {
                    val entry = zip.nextEntry ?: break
                    val name = TranscriptFormat.displayName(entry.name)
                    if (!entry.isDirectory && supported(name)) {
                        if (++count > 100) throw IllegalArgumentException("Слишком много аудиофайлов в ZIP")
                        update("Импорт ZIP: $name")
                        val job = addAudio(name, zip) { copied ->
                            totalBytes += copied
                            if (totalBytes > 3L * 1024 * 1024 * 1024)
                                throw IllegalArgumentException("Слишком большой архив")
                        }
                        imported.add(job)
                    }
                    zip.closeEntry()
                }
                if (imported.isEmpty()) throw IllegalArgumentException("ZIP не содержит поддерживаемых аудиозаписей")
            } else {
                require(supported(originalName)) { "Поддерживаются M4A, AAC, MP3, WAV, OGG, FLAC, MP4 и ZIP" }
                imported.add(addAudio(originalName, stream))
            }
        }
        return imported
    }

    private fun addAudio(name: String, stream: InputStream, countBytes: (Long) -> Unit = {}): TranscriptJob {
        val id = UUID.randomUUID().toString()
        val extension = name.substringAfterLast('.', "m4a").lowercase(java.util.Locale.ROOT)
        val out = File(inputDir, "$id.$extension")
        val partial = File(inputDir, "$id.part")
        try {
            FileOutputStream(partial).buffered().use { target ->
                val buffer = ByteArray(64 * 1024)
                var size = 0L
                while (true) {
                    val n = stream.read(buffer)
                    if (n < 0) break
                    size += n
                    if (size > 1024L * 1024L * 1024L) throw IllegalArgumentException("Аудио больше 1 ГБ")
                    target.write(buffer, 0, n)
                    countBytes(n.toLong())
                }
                target.flush()
            }
            if (partial.length() == 0L) throw IllegalArgumentException("Пустой аудиофайл")
            if (!partial.renameTo(out)) throw IllegalStateException("Ошибка сохранения импорта")
            val job = TranscriptJob(id, TranscriptFormat.displayName(name), out.absolutePath, System.currentTimeMillis())
            save(job)
            return job
        } finally {
            if (partial.exists()) partial.delete()
        }
    }

    private fun queryName(uri: Uri): String {
        context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
            if (c.moveToFirst()) return TranscriptFormat.displayName(c.getString(0) ?: "record.m4a")
        }
        return TranscriptFormat.displayName(uri.lastPathSegment ?: "record.m4a")
    }
}
