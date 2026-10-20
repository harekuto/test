package dev.harekuto.echotranscript

import android.app.Activity
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.DocumentsContract
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import dev.ffmpegkit.whisper.Whisper
import dev.ffmpegkit.whisper.WhisperConfig
import kotlinx.coroutines.runBlocking
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class MainActivity : Activity() {
    private val main = Handler(Looper.getMainLooper())
    private val work = Executors.newSingleThreadExecutor()
    private val cancelled = AtomicBoolean(false)
    private lateinit var store: TranscriptStore
    private lateinit var manager: ModelManager
    private val jobs = mutableListOf<TranscriptJob>()
    private lateinit var jobsSpinner: Spinner
    private lateinit var modelsSpinner: Spinner
    private lateinit var languageSpinner: Spinner
    private lateinit var jobsAdapter: ArrayAdapter<String>
    private lateinit var progress: ProgressBar
    private lateinit var status: TextView
    private lateinit var output: TextView
    private lateinit var runButton: Button
    private lateinit var stopButton: Button
    private lateinit var importButton: Button
    private lateinit var downloadButton: Button
    private var busy = false
    private var currentJobId: String? = null
    private var pendingExport: String? = null
    private var exportSrt = false

    companion object {
        const val PICK_AUDIO = 101
        const val PICK_MODEL = 102
        const val SAVE_TEXT = 103
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = TranscriptStore(this)
        manager = ModelManager(this)
        window.statusBarColor = Color.rgb(8, 15, 29)
        window.navigationBarColor = Color.rgb(8, 15, 29)
        buildUi()
        refreshJobs()
        showMessage("Импортируй ZIP EchoVault или M4A. Разговоры не отправляются в облако.")
    }

    private fun color(code: String): Int = Color.parseColor(code)
    private fun dp(value: Int): Int = (resources.displayMetrics.density * value + 0.5f).toInt()
    private fun rounded(background: Int, radius: Int = 14): GradientDrawable =
        GradientDrawable().apply { setColor(background); cornerRadius = dp(radius).toFloat() }
    private fun title(label: String, size: Float = 15f): TextView =
        TextView(this).apply {
            text = label
            textSize = size
            setTextColor(color("#E8F1F8"))
            typeface = Typeface.DEFAULT_BOLD
        }
    private fun hint(label: String): TextView =
        TextView(this).apply {
            text = label
            textSize = 13f
            setTextColor(color("#A6B7C8"))
            setPadding(0, dp(5), 0, dp(7))
        }
    private fun button(label: String, accent: Boolean = false): Button =
        Button(this).apply {
            text = label
            textSize = 13f
            isAllCaps = false
            setTextColor(if (accent) color("#071725") else color("#E4ECF6"))
            background = rounded(if (accent) color("#62E3D0") else color("#26364D"))
            minHeight = dp(48)
            minimumHeight = dp(48)
            setPadding(dp(8), 0, dp(8), 0)
        }
    private fun add(parent: LinearLayout, view: View, top: Int = 8) {
        val p = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        p.topMargin = dp(top)
        parent.addView(view, p)
    }
    private fun section(container: LinearLayout): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(17), dp(14), dp(17), dp(17))
            background = rounded(color("#152236"))
            add(container, this, 15)
        }
    private fun spinner(values: List<String>): Spinner {
        val s = Spinner(this)
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, values)
        s.adapter = adapter
        s.background = rounded(color("#26364D"), 10)
        s.setPadding(dp(8), dp(5), dp(8), dp(5))
        s.minimumHeight = dp(48)
        return s
    }

    private fun buildUi() {
        val screen = ScrollView(this).apply {
            setBackgroundColor(color("#091323"))
            isFillViewport = true
        }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(20), dp(16), dp(30))
        }
        screen.addView(root)
        setContentView(screen)
        val h = title("ECHO TRANSCRIPT", 23f).apply {
            setTextColor(color("#69E9D5"))
            letterSpacing = 0.07f
        }
        add(root, h, 0)
        add(root, hint("Локальная транскрипция длинных аудиозаписей · M4A / ZIP"), 3)

        val filesCard = section(root)
        add(filesCard, title("01  Аудиозаписи"), 0)
        importButton = button("＋  Импортировать M4A / ZIP", true)
        add(filesCard, importButton)
        importButton.setOnClickListener { pickAudio() }
        jobsSpinner = spinner(listOf("Пока нет записей"))
        jobsAdapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, mutableListOf())
        jobsSpinner.adapter = jobsAdapter
        add(filesCard, jobsSpinner)
        jobsSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) { if (!busy) showSelection() }
        }

        val modelCard = section(root)
        add(modelCard, title("02  Распознавание"), 0)
        add(modelCard, hint("Выбирай мультиязычную модель. Для русско-казахской речи лучше Base или Small."), 0)
        modelsSpinner = spinner(manager.choices.map { it.display })
        modelsSpinner.setSelection(1)
        add(modelCard, modelsSpinner, 0)
        downloadButton = button("↓  Скачать модель", true)
        add(modelCard, downloadButton)
        downloadButton.setOnClickListener { downloadModel() }
        val selectModel = button("Импортировать свою GGML-модель")
        add(modelCard, selectModel)
        selectModel.setOnClickListener { pickModel() }
        add(modelCard, hint("Язык аудиозаписи"), 5)
        languageSpinner = spinner(listOf("Авто (русский / қазақша)", "Русский", "Қазақша"))
        add(modelCard, languageSpinner, 0)
        runButton = button("▶  Распознать / продолжить", true)
        add(modelCard, runButton, 16)
        runButton.setOnClickListener { beginTranscription() }
        stopButton = button("■  Остановить после текущего фрагмента")
        add(modelCard, stopButton)
        stopButton.setOnClickListener {
            cancelled.set(true)
            showMessage("Запрошена остановка. Распознанные части уже сохранены.")
        }
        stopButton.isEnabled = false

        val resultsCard = section(root)
        add(resultsCard, title("03  Прогресс и текст"), 0)
        progress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            progress = 0
        }
        add(resultsCard, progress, 12)
        status = hint("")
        add(resultsCard, status, 5)
        output = TextView(this).apply {
            text = "Импортируй аудиозапись, чтобы начать."
            setTextColor(color("#D4E1EF"))
            textSize = 14f
            typeface = Typeface.MONOSPACE
            setPadding(dp(11), dp(12), dp(11), dp(12))
            background = rounded(color("#0D192C"))
            setTextIsSelectable(true)
            minHeight = dp(110)
        }
        add(resultsCard, output)
        val copy = button("Копировать полный текст")
        add(resultsCard, copy)
        copy.setOnClickListener {
            val job = selectedJob() ?: return@setOnClickListener
            val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            cm.setPrimaryClip(ClipData.newPlainText(job.name, job.asText()))
            showMessage("Текст скопирован")
        }
        val saveTxt = button("Экспорт TXT")
        add(resultsCard, saveTxt)
        saveTxt.setOnClickListener { saveDocument(false) }
        val saveSrt = button("Экспорт SRT (субтитры)")
        add(resultsCard, saveSrt)
        saveSrt.setOnClickListener { saveDocument(true) }
        add(root, hint("Приватность: исходники и распознанные фрагменты хранятся только на устройстве. Экспортируй их отдельно до удаления приложения."), 15)
    }

    private fun selectedJob(): TranscriptJob? = jobs.getOrNull(jobsSpinner.selectedItemPosition)
    private fun selectedModel(): ModelChoice = manager.choices[modelsSpinner.selectedItemPosition.coerceIn(0, manager.choices.lastIndex)]
    private fun selectedLanguage(): String = when (languageSpinner.selectedItemPosition) {
        1 -> "ru"
        2 -> "kk"
        else -> "auto"
    }
    private fun showMessage(message: String) {
        main.post { if (::status.isInitialized) status.text = message }
    }
    private fun showProgress(value: Int) { main.post { progress.progress = value.coerceIn(0, 100) } }
    private fun refreshJobs(wantId: String? = null) {
        val old = wantId ?: selectedJob()?.id
        jobs.clear()
        jobs.addAll(store.findAll())
        jobsAdapter.clear()
        jobsAdapter.addAll(jobs.map { it.name + if (it.completed) "  ✓" else if (it.nextChunk > 0) "  • ${it.nextChunk}/${it.totalChunks}" else "" })
        jobsAdapter.notifyDataSetChanged()
        val index = jobs.indexOfFirst { it.id == old }
        if (index >= 0) jobsSpinner.setSelection(index)
        else if (jobs.isNotEmpty()) jobsSpinner.setSelection(0)
        showSelection()
    }
    private fun showSelection() {
        val job = selectedJob()
        output.text = job?.asText() ?: "Нет импортированных записей."
        progress.progress = if (job != null && job.totalChunks > 0) job.nextChunk * 100 / job.totalChunks else 0
        if (!busy && job != null) {
            status.text = if (job.completed) "Готово. Экспортируй TXT или SRT."
                else "Сохранено: ${job.nextChunk} из ${job.totalChunks} фрагментов."
        }
    }
    private fun task(label: String, jobId: String? = null, block: () -> Unit) {
        if (busy) return
        busy = true
        cancelled.set(false)
        currentJobId = jobId
        importButton.isEnabled = false
        downloadButton.isEnabled = false
        runButton.isEnabled = false
        stopButton.isEnabled = true
        jobsSpinner.isEnabled = false
        modelsSpinner.isEnabled = false
        languageSpinner.isEnabled = false
        showMessage(label)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        work.execute {
            try { block() }
            catch (e: InterruptedException) { showMessage("Остановлено. Частичный результат сохранён.") }
            catch (e: Exception) { showMessage("Ошибка: ${e.localizedMessage ?: e.javaClass.simpleName}") }
            finally {
                main.post {
                    busy = false
                    currentJobId = null
                    importButton.isEnabled = true
                    downloadButton.isEnabled = true
                    runButton.isEnabled = true
                    stopButton.isEnabled = false
                    jobsSpinner.isEnabled = true
                    modelsSpinner.isEnabled = true
                    languageSpinner.isEnabled = true
                    window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                    val previous = jobId ?: selectedJob()?.id
                    refreshJobs(previous)
                }
            }
        }
    }
    private fun pickAudio() {
        val i = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
        }
        startActivityForResult(i, PICK_AUDIO)
    }
    private fun pickModel() {
        val i = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
        }
        startActivityForResult(i, PICK_MODEL)
    }
    @Deprecated("Android Activity result API; intentionally used to avoid UI library dependencies")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode != RESULT_OK || data == null) return
        when (requestCode) {
            PICK_AUDIO -> {
                val uris = mutableListOf<Uri>()
                data.data?.let { uris.add(it) }
                data.clipData?.let { clip ->
                    for (i in 0 until clip.itemCount) {
                        val item = clip.getItemAt(i).uri
                        if (item !in uris) uris.add(item)
                    }
                }
                if (uris.isNotEmpty()) task("Импорт аудиозаписей...") {
                    val imported = mutableListOf<TranscriptJob>()
                    uris.forEach { uri ->
                        if (cancelled.get()) throw InterruptedException()
                        imported.addAll(store.import(uri) { showMessage(it) })
                    }
                    main.post { refreshJobs(imported.firstOrNull()?.id) }
                    showMessage("Импортировано файлов: ${imported.size}. Исходники сохранены.")
                }
            }
            PICK_MODEL -> data.data?.let { uri ->
                val choice = selectedModel()
                task("Импорт модели ${choice.name}...") {
                    manager.importModel(this, uri, choice)
                    showMessage("Модель ${choice.name} проверена и сохранена")
                }
            }
            SAVE_TEXT -> {
                val text = pendingExport
                pendingExport = null
                if (text != null) data.data?.let { uri ->
                    task("Экспорт документа...") {
                        contentResolver.openOutputStream(uri, "w").use { out ->
                            if (out == null) error("Не удалось создать документ")
                            out.write(text.toByteArray(Charsets.UTF_8))
                            out.flush()
                        }
                        showMessage("Документ сохранён")
                    }
                }
            }
        }
    }
    private fun downloadModel() {
        val choice = selectedModel()
        task("Загрузка ${choice.name}...") {
            manager.download(choice, { cancelled.get() }) { showMessage(it) }
        }
    }
    private fun beginTranscription() {
        val job = selectedJob()
        if (job == null) { showMessage("Сначала импортируй аудио или ZIP"); return }
        if (job.completed) { showMessage("Запись уже завершена, выбери экспорт TXT"); return }
        val choice = if (job.nextChunk > 0 && job.model.isNotBlank()) {
            manager.choices.firstOrNull { it.name == job.model } ?: selectedModel()
        } else selectedModel()
        if (!manager.valid(choice)) { showMessage("Сначала скачай модель ${choice.name} (или импортируй GGML)"); return }
        val lang = if (job.nextChunk > 0 && job.language.isNotEmpty()) job.language else selectedLanguage()
        task("Подготовка аудио...", job.id) {
            transcribe(job, choice, lang)
        }
    }
    private fun transcribe(job: TranscriptJob, choice: ModelChoice, language: String) {
        val inputFile = File(job.audioPath)
        require(inputFile.isFile) { "Исходный файл не найден" }
        val pcm = File(store.cacheDir, job.id + ".pcm")
        val samples = AudioPreparer.prepare(inputFile, pcm, { cancelled.get() }) { p ->
            showMessage("Декодирование M4A: $p%")
        }
        if (cancelled.get()) throw InterruptedException()
        val total = AudioPreparer.chunkCount(samples)
        require(total > 0) { "Пустое аудио" }
        require(job.nextChunk <= total) { "Повреждена позиция продолжения" }
        if (job.nextChunk > 0) require(job.totalChunks == total) { "Аудио изменилось после сохранения" }
        job.model = choice.name
        job.language = language
        job.totalChunks = total
        job.durationMs = samples * 1000 / 16_000
        store.save(job)
        showMessage("Загрузка Whisper: ${choice.name}")
        val model = runBlocking { Whisper.loadModel(this@MainActivity, manager.get(choice).absolutePath) }
        val wav = File(store.cacheDir, "segment-${job.id}.wav")
        try {
            for (i in job.nextChunk until total) {
                if (cancelled.get()) throw InterruptedException()
                val part = AudioPreparer.buildChunk(pcm, i, wav)
                showMessage("Распознавание: ${i + 1} / $total")
                val result = runBlocking {
                    Whisper.transcribe(
                        model, wav.absolutePath,
                        if (language == "auto") WhisperConfig() else WhisperConfig(language = language)
                    )
                }
                var count = 0
                for (segment in result.segments) {
                    val start = part.readStartMs + segment.startMs.toLong()
                    val end = part.readStartMs + segment.endMs.toLong()
                    if (end <= part.primaryStartMs) continue
                    val text = segment.text.trim()
                    if (text.isBlank()) continue
                    job.segments.add(TranscriptSegment(
                        maxOf(start, part.primaryStartMs), maxOf(end, part.primaryStartMs + 1000), text
                    ))
                    count++
                }
                if (count == 0 && result.segments.isEmpty() && result.text.isNotBlank()) {
                    job.segments.add(TranscriptSegment(part.primaryStartMs,
                        minOf(job.durationMs, part.primaryStartMs + 28_000), result.text.trim()))
                }
                job.nextChunk = i + 1
                store.save(job) // checkpoint after EVERY segment; preserve partial transcripts
                showProgress(job.nextChunk * 100 / total)
                main.post { if (currentJobId == job.id) output.text = job.asText() }
            }
            if (job.completed) {
                pcm.delete() // transient PCM only; never delete the imported audio or transcript
                showMessage("Транскрипция завершена. Экспортируй TXT.")
            }
        } finally {
            wav.delete()
            Whisper.releaseModel(model)
        }
    }
    private fun saveDocument(isSrt: Boolean) {
        val job = selectedJob() ?: return
        exportSrt = isSrt
        pendingExport = if (isSrt) job.asSrt() else job.asText()
        val fileName = job.name.substringBeforeLast('.', job.name).take(50) +
            if (isSrt) ".srt" else ".txt"
        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = if (isSrt) "application/x-subrip" else "text/plain"
            putExtra(Intent.EXTRA_TITLE, fileName)
        }
        startActivityForResult(intent, SAVE_TEXT)
    }
    override fun onDestroy() {
        super.onDestroy()
        if (isFinishing) {
            cancelled.set(true)
            work.shutdown()
        }
    }
}
