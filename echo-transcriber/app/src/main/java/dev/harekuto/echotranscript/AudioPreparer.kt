package dev.harekuto.echotranscript

import android.media.AudioFormat
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.nio.ByteOrder
import kotlin.math.roundToInt

/**
 * Uses Android's media decoder rather than trusting Whisper's WAV/MP3-only miniaudio reader
 * to support EchoVault's M4A/AAC source files. Never changes or deletes the original.
 */
object AudioPreparer {
    private const val RATE = 16_000
    private const val PRIMARY_SECONDS = 28
    private const val OVERLAP_SECONDS = 2

    fun prepare(
        input: File,
        destination: File,
        cancelled: () -> Boolean,
        progress: (Int) -> Unit
    ): Long {
        if (destination.isFile && destination.length() >= 2L) return destination.length() / 2L
        destination.parentFile?.mkdirs()
        val part = File(destination.parentFile, destination.name + ".part")
        val extractor = MediaExtractor()
        var codec: MediaCodec? = null
        try {
            extractor.setDataSource(input.absolutePath)
            val index = (0 until extractor.trackCount).firstOrNull {
                extractor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("audio/") == true
            } ?: throw IOException("Файл не содержит поддерживаемой аудиодорожки")
            val format = extractor.getTrackFormat(index)
            val mime = format.getString(MediaFormat.KEY_MIME) ?: throw IOException("Нет MIME аудио")
            val durationUs = if (format.containsKey(MediaFormat.KEY_DURATION)) format.getLong(MediaFormat.KEY_DURATION) else -1L
            extractor.selectTrack(index)
            val decoder = MediaCodec.createDecoderByType(mime)
            codec = decoder
            decoder.configure(format, null, null, 0)
            decoder.start()
            val info = MediaCodec.BufferInfo()
            var inputEnded = false
            var outputEnded = false
            var sampleRate = format.getInteger(MediaFormat.KEY_SAMPLE_RATE)
            var channels = format.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
            var pcmEncoding = AudioFormat.ENCODING_PCM_16BIT
            var lastProgress = 0L
            BufferedOutputStream(FileOutputStream(part), 64 * 1024).use { stream ->
                val resampler = StreamingResampler(stream)
                while (!outputEnded) {
                    if (cancelled()) throw InterruptedException("Остановлено")
                    if (!inputEnded) {
                        val bufferId = decoder.dequeueInputBuffer(10_000)
                        if (bufferId >= 0) {
                            val buf = decoder.getInputBuffer(bufferId) ?: throw IOException("Нет входного буфера")
                            buf.clear()
                            val length = extractor.readSampleData(buf, 0)
                            if (length < 0) {
                                decoder.queueInputBuffer(bufferId, 0, 0, 0L, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                                inputEnded = true
                            } else {
                                val timestamp = extractor.sampleTime.coerceAtLeast(0L)
                                decoder.queueInputBuffer(bufferId, 0, length, timestamp, 0)
                                extractor.advance()
                            }
                        }
                    }
                    val bufferId = decoder.dequeueOutputBuffer(info, 10_000)
                    when (bufferId) {
                        MediaCodec.INFO_TRY_AGAIN_LATER -> Unit
                        MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                            val outputFormat = decoder.outputFormat
                            sampleRate = outputFormat.getInteger(MediaFormat.KEY_SAMPLE_RATE)
                            channels = outputFormat.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
                            pcmEncoding = if (outputFormat.containsKey(MediaFormat.KEY_PCM_ENCODING)) {
                                outputFormat.getInteger(MediaFormat.KEY_PCM_ENCODING)
                            } else AudioFormat.ENCODING_PCM_16BIT
                            if (pcmEncoding != AudioFormat.ENCODING_PCM_16BIT && pcmEncoding != AudioFormat.ENCODING_PCM_FLOAT)
                                throw IOException("Неподдерживаемое PCM кодирование: $pcmEncoding")
                        }
                        else -> if (bufferId >= 0) {
                            if (info.size > 0) {
                                val buf = decoder.getOutputBuffer(bufferId) ?: throw IOException("Нет выходного буфера")
                                buf.order(ByteOrder.LITTLE_ENDIAN)
                                buf.position(info.offset)
                                buf.limit(info.offset + info.size)
                                val bytesPerSample = if (pcmEncoding == AudioFormat.ENCODING_PCM_FLOAT) 4 else 2
                                if (channels !in 1..8) throw IOException("Неподдерживаемое число каналов: $channels")
                                val frames = info.size / (bytesPerSample * channels)
                                repeat(frames) {
                                    var sum = 0f
                                    repeat(channels) {
                                        sum += if (pcmEncoding == AudioFormat.ENCODING_PCM_FLOAT) buf.float
                                        else buf.short.toFloat() / 32768f
                                    }
                                    resampler.add(sum / channels, sampleRate)
                                }
                                val now = android.os.SystemClock.elapsedRealtime()
                                if (now - lastProgress > 500 && durationUs > 0) {
                                    progress((info.presentationTimeUs * 100 / durationUs).toInt().coerceIn(0, 99))
                                    lastProgress = now
                                }
                            }
                            outputEnded = (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0
                            decoder.releaseOutputBuffer(bufferId, false)
                        }
                    }
                }
                stream.flush()
            }
            if (part.length() < 2) throw IOException("Декодировано 0 аудиосэмплов")
            if (!part.renameTo(destination)) throw IOException("Не удалось сохранить подготовленное аудио")
            progress(100)
            return destination.length() / 2
        } finally {
            try { codec?.stop() } catch (_: Exception) { }
            try { codec?.release() } catch (_: Exception) { }
            extractor.release()
            if (part.exists()) part.delete()
        }
    }

    private class StreamingResampler(private val stream: BufferedOutputStream) {
        private var srcRate = 0
        private var framesSeen = 0L
        private var nextOutputIndex = 0.0
        private var lastValue = 0f
        private fun writeSample(value: Float) {
            val sample = (value.coerceIn(-1f, 1f) * 32767f).roundToInt().coerceIn(-32768, 32767)
            stream.write(sample and 0xff)
            stream.write((sample ushr 8) and 0xff)
        }
        fun add(value: Float, sourceRate: Int) {
            if (sourceRate <= 0) throw IOException("Неправильная частота дискретизации")
            if (srcRate == 0) srcRate = sourceRate
            if (srcRate != sourceRate) throw IOException("Частота аудио изменилась в середине файла")
            if (framesSeen == 0L) {
                writeSample(value)
                nextOutputIndex = sourceRate.toDouble() / RATE
                lastValue = value
                framesSeen++
                return
            }
            val intervalStart = framesSeen - 1
            while (nextOutputIndex <= framesSeen) {
                val fraction = (nextOutputIndex - intervalStart).toFloat().coerceIn(0f, 1f)
                writeSample(lastValue + (value - lastValue) * fraction)
                nextOutputIndex += sourceRate.toDouble() / RATE
            }
            lastValue = value
            framesSeen++
        }
    }

    data class Chunk(val path: File, val index: Int, val primaryStartMs: Long, val readStartMs: Long)
    fun chunkCount(samples: Long): Int = ((samples + RATE * PRIMARY_SECONDS - 1) / (RATE * PRIMARY_SECONDS)).toInt()

    fun buildChunk(rawPcm: File, index: Int, outFile: File): Chunk {
        val samples = rawPcm.length() / 2L
        val primaryStart = index.toLong() * PRIMARY_SECONDS * RATE
        require(primaryStart < samples) { "Сегмент за пределами аудио" }
        val readStart = (primaryStart - OVERLAP_SECONDS.toLong() * RATE).coerceAtLeast(0)
        val end = (primaryStart + PRIMARY_SECONDS.toLong() * RATE).coerceAtMost(samples)
        val lengthBytes = (end - readStart) * 2
        FileOutputStream(outFile).buffered().use { out ->
            val bytes = lengthBytes.toInt()
            val header = java.nio.ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
            header.put("RIFF".toByteArray(Charsets.US_ASCII))
            header.putInt(36 + bytes)
            header.put("WAVEfmt ".toByteArray(Charsets.US_ASCII))
            header.putInt(16)
            header.putShort(1.toShort())
            header.putShort(1.toShort())
            header.putInt(RATE)
            header.putInt(RATE * 2)
            header.putShort(2.toShort())
            header.putShort(16.toShort())
            header.put("data".toByteArray(Charsets.US_ASCII))
            header.putInt(bytes)
            out.write(header.array())
            FileInputStream(rawPcm).use { raw ->
                raw.channel.position(readStart * 2)
                val buffer = ByteArray(65_536)
                var remaining = lengthBytes
                while (remaining > 0) {
                    val n = raw.read(buffer, 0, minOf(buffer.size.toLong(), remaining).toInt())
                    if (n < 0) throw IOException("Неполный PCM файл")
                    out.write(buffer, 0, n)
                    remaining -= n
                }
            }
        }
        return Chunk(outFile, index, primaryStart * 1000 / RATE, readStart * 1000 / RATE)
    }
}
