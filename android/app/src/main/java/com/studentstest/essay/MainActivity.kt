package com.studentstest.essay

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

private const val API_BASE_URL = "http://8.154.34.227:8000"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = Color(0xFF2563EB),
                    secondary = Color(0xFF0F766E),
                    surface = Color(0xFFF8FAFC),
                ),
            ) {
                EssayCorrectionApp()
            }
        }
    }
}

data class EssayTemplate(
    val id: String,
    val title: String,
    val requirements: String,
    val gradeLevel: String,
    val essayType: String,
)

data class EssayScore(
    val total: Int,
    val content: Int,
    val structure: Int,
    val language: Int,
    val mechanics: Int,
    val presentation: Int,
)

data class EssayComments(
    val summary: String,
    val strengths: List<String>,
    val issues: List<String>,
    val suggestions: List<String>,
    val encouragement: String,
    val spellingIssues: List<String>,
    val sentenceIssues: List<String>,
    val revisionExample: String,
    val teacherNotes: String,
)

data class EssayCorrection(
    val id: String,
    val ocrText: String,
    val score: EssayScore,
    val comments: EssayComments,
)

data class EssayUiState(
    val templates: List<EssayTemplate> = emptyList(),
    val selectedTemplate: EssayTemplate? = null,
    val correction: EssayCorrection? = null,
    val title: String = "我爱四季",
    val requirements: String = "围绕四季特点写清楚内容，语句通顺，有真情实感。",
    val gradeLevel: String = "小学三年级",
    val essayType: String = "命题作文",
    val selectedImageUri: Uri? = null,
    val selectedImageLabel: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
)

class EssayViewModel : ViewModel() {
    private val api = EssayApiClient(API_BASE_URL)
    private val _uiState = MutableStateFlow(EssayUiState())
    val uiState: StateFlow<EssayUiState> = _uiState

    fun loadTemplates() {
        viewModelScope.launch {
            runApiCall {
                val templates = api.listTemplates()
                _uiState.update { it.copy(templates = templates) }
            }
        }
    }

    fun updateTitle(value: String) = _uiState.update { it.copy(title = value) }
    fun updateRequirements(value: String) = _uiState.update { it.copy(requirements = value) }
    fun updateGradeLevel(value: String) = _uiState.update { it.copy(gradeLevel = value) }
    fun updateEssayType(value: String) = _uiState.update { it.copy(essayType = value) }

    fun createTemplate() {
        val state = _uiState.value
        if (state.title.isBlank()) {
            _uiState.update { it.copy(errorMessage = "请先填写作文题目") }
            return
        }
        viewModelScope.launch {
            runApiCall {
                val template = api.createTemplate(
                    title = state.title.trim(),
                    requirements = state.requirements.trim(),
                    gradeLevel = state.gradeLevel.trim().ifBlank { "小学三年级" },
                    essayType = state.essayType.trim().ifBlank { "命题作文" },
                )
                val templates = api.listTemplates()
                _uiState.update {
                    it.copy(
                        templates = templates,
                        selectedTemplate = template,
                        correction = null,
                        selectedImageUri = null,
                        selectedImageLabel = "",
                    )
                }
            }
        }
    }

    fun selectTemplate(template: EssayTemplate) {
        _uiState.update {
            it.copy(
                selectedTemplate = template,
                correction = null,
                selectedImageUri = null,
                selectedImageLabel = "",
                errorMessage = null,
            )
        }
    }

    fun goBackToTemplates() {
        _uiState.update {
            it.copy(
                selectedTemplate = null,
                correction = null,
                selectedImageUri = null,
                selectedImageLabel = "",
                errorMessage = null,
            )
        }
    }

    fun setSelectedImage(uri: Uri?, label: String) {
        _uiState.update {
            it.copy(
                selectedImageUri = uri,
                selectedImageLabel = label,
                correction = null,
                errorMessage = null,
            )
        }
    }

    fun submitCorrection(context: Context) {
        val state = _uiState.value
        val template = state.selectedTemplate
        val imageUri = state.selectedImageUri
        if (template == null) {
            _uiState.update { it.copy(errorMessage = "请先选择模板") }
            return
        }
        if (imageUri == null) {
            _uiState.update { it.copy(errorMessage = "请先拍照或选择图片") }
            return
        }
        viewModelScope.launch {
            runApiCall {
                val correction = api.correctEssay(context, template.id, imageUri)
                _uiState.update { it.copy(correction = correction) }
            }
        }
    }

    private suspend fun runApiCall(block: suspend () -> Unit) {
        _uiState.update { it.copy(isLoading = true, errorMessage = null) }
        try {
            block()
        } catch (error: Exception) {
            _uiState.update { it.copy(errorMessage = error.message ?: "请求失败，请稍后重试") }
        } finally {
            _uiState.update { it.copy(isLoading = false) }
        }
    }
}

class EssayApiClient(private val baseUrl: String) {
    suspend fun listTemplates(): List<EssayTemplate> = withContext(Dispatchers.IO) {
        val json = request("GET", "$baseUrl/api/v1/essay-templates")
        val items = JSONObject(json).getJSONArray("items")
        buildList {
            for (index in 0 until items.length()) {
                add(items.getJSONObject(index).toTemplate())
            }
        }
    }

    suspend fun createTemplate(
        title: String,
        requirements: String,
        gradeLevel: String,
        essayType: String,
    ): EssayTemplate = withContext(Dispatchers.IO) {
        val payload = JSONObject()
            .put("title", title)
            .put("requirements", requirements)
            .put("grade_level", gradeLevel)
            .put("essay_type", essayType)
        JSONObject(request("POST", "$baseUrl/api/v1/essay-templates", payload.toString()))
            .toTemplate()
    }

    suspend fun correctEssay(context: Context, templateId: String, imageUri: Uri): EssayCorrection =
        withContext(Dispatchers.IO) {
            val imageBytes = context.contentResolver.openInputStream(imageUri)?.use { input ->
                input.readBytes()
            } ?: error("无法读取图片")
            val boundary = "EssayBoundary${UUID.randomUUID().toString().replace("-", "")}"
            val lineBreak = "\r\n"
            val body = ByteArrayOutputStream()
            body.writeText("--$boundary$lineBreak")
            body.writeText("Content-Disposition: form-data; name=\"template_id\"$lineBreak$lineBreak")
            body.writeText(templateId)
            body.writeText(lineBreak)
            body.writeText("--$boundary$lineBreak")
            body.writeText(
                "Content-Disposition: form-data; name=\"image\"; filename=\"essay.jpg\"$lineBreak",
            )
            body.writeText("Content-Type: image/jpeg$lineBreak$lineBreak")
            body.write(imageBytes)
            body.writeText(lineBreak)
            body.writeText("--$boundary--$lineBreak")

            val json = request(
                method = "POST",
                url = "$baseUrl/api/v1/essay-corrections",
                body = body.toByteArray(),
                contentType = "multipart/form-data; boundary=$boundary",
                timeoutMillis = 180_000,
            )
            JSONObject(json).toCorrection()
        }

    private fun request(
        method: String,
        url: String,
        jsonBody: String? = null,
    ): String {
        return request(
            method = method,
            url = url,
            body = jsonBody?.toByteArray(Charsets.UTF_8),
            contentType = if (jsonBody == null) null else "application/json; charset=utf-8",
            timeoutMillis = 30_000,
        )
    }

    private fun request(
        method: String,
        url: String,
        body: ByteArray? = null,
        contentType: String? = null,
        timeoutMillis: Int,
    ): String {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = timeoutMillis
            readTimeout = timeoutMillis
            doInput = true
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", contentType)
                setRequestProperty("Content-Length", body.size.toString())
            }
        }
        try {
            if (body != null) {
                connection.outputStream.use { it.write(body) }
            }
            val responseCode = connection.responseCode
            val stream = if (responseCode in 200..299) {
                connection.inputStream
            } else {
                connection.errorStream ?: connection.inputStream
            }
            val text = stream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            if (responseCode !in 200..299) {
                throw IllegalStateException("服务返回 $responseCode：$text")
            }
            return text
        } finally {
            connection.disconnect()
        }
    }
}

private fun ByteArrayOutputStream.writeText(value: String) {
    write(value.toByteArray(Charsets.UTF_8))
}

private fun JSONObject.toTemplate(): EssayTemplate {
    return EssayTemplate(
        id = getString("id"),
        title = getString("title"),
        requirements = optString("requirements"),
        gradeLevel = optString("grade_level", "小学三年级"),
        essayType = optString("essay_type", "命题作文"),
    )
}

private fun JSONObject.toCorrection(): EssayCorrection {
    val scoreJson = getJSONObject("score")
    val commentsJson = getJSONObject("comments")
    return EssayCorrection(
        id = getString("id"),
        ocrText = getString("ocrText"),
        score = EssayScore(
            total = scoreJson.getInt("total"),
            content = scoreJson.getInt("content"),
            structure = scoreJson.getInt("structure"),
            language = scoreJson.getInt("language"),
            mechanics = scoreJson.getInt("mechanics"),
            presentation = scoreJson.getInt("presentation"),
        ),
        comments = EssayComments(
            summary = commentsJson.getString("summary"),
            strengths = commentsJson.optStringList("strengths"),
            issues = commentsJson.optStringList("issues"),
            suggestions = commentsJson.optStringList("suggestions"),
            encouragement = commentsJson.getString("encouragement"),
            spellingIssues = commentsJson.optStringList("spellingIssues"),
            sentenceIssues = commentsJson.optStringList("sentenceIssues"),
            revisionExample = commentsJson.optString("revisionExample"),
            teacherNotes = commentsJson.optString("teacherNotes"),
        ),
    )
}

private fun JSONObject.optStringList(key: String): List<String> {
    val values = optJSONArray(key) ?: JSONArray()
    return buildList {
        for (index in 0 until values.length()) {
            add(values.optString(index))
        }
    }.filter { it.isNotBlank() }
}

@Composable
fun EssayCorrectionApp(viewModel: EssayViewModel = androidx.lifecycle.viewmodel.compose.viewModel()) {
    val uiState by viewModel.uiState.collectAsState()
    LaunchedEffect(Unit) {
        viewModel.loadTemplates()
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.surface,
    ) {
        if (uiState.selectedTemplate == null) {
            TemplateListScreen(uiState = uiState, viewModel = viewModel)
        } else {
            TemplateDetailScreen(uiState = uiState, viewModel = viewModel)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TemplateListScreen(uiState: EssayUiState, viewModel: EssayViewModel) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("作文批改") },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            ErrorBanner(uiState.errorMessage)
            LoadingRow(uiState.isLoading)

            SectionCard(title = "新建模板") {
                OutlinedTextField(
                    value = uiState.title,
                    onValueChange = viewModel::updateTitle,
                    label = { Text("作文题目") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                OutlinedTextField(
                    value = uiState.requirements,
                    onValueChange = viewModel::updateRequirements,
                    label = { Text("作文要求") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 3,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = uiState.gradeLevel,
                        onValueChange = viewModel::updateGradeLevel,
                        label = { Text("年级") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                    )
                    OutlinedTextField(
                        value = uiState.essayType,
                        onValueChange = viewModel::updateEssayType,
                        label = { Text("类型") },
                        modifier = Modifier.weight(1f),
                        singleLine = true,
                    )
                }
                Button(
                    onClick = viewModel::createTemplate,
                    enabled = !uiState.isLoading,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("创建并进入模板")
                }
            }

            SectionCard(title = "已有模板") {
                if (uiState.templates.isEmpty()) {
                    Text("暂无模板")
                }
                uiState.templates.forEach { template ->
                    TemplateRow(template = template, onClick = { viewModel.selectTemplate(template) })
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TemplateDetailScreen(uiState: EssayUiState, viewModel: EssayViewModel) {
    val context = LocalContext.current
    val template = uiState.selectedTemplate ?: return
    var cameraUri by remember { mutableStateOf<Uri?>(null) }

    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        viewModel.setSelectedImage(uri, if (uri == null) "" else "已选择相册图片")
    }
    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        viewModel.setSelectedImage(
            uri = if (success) cameraUri else null,
            label = if (success) "已拍照" else "",
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            val uri = createCameraUri(context)
            cameraUri = uri
            cameraLauncher.launch(uri)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(template.title) },
                navigationIcon = {
                    OutlinedButton(
                        onClick = viewModel::goBackToTemplates,
                        modifier = Modifier.padding(start = 8.dp),
                    ) {
                        Text("返回")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            ErrorBanner(uiState.errorMessage)
            LoadingRow(uiState.isLoading)

            SectionCard(title = "模板要求") {
                Text(template.requirements.ifBlank { "无额外要求" })
                Text("${template.gradeLevel} · ${template.essayType}", color = Color(0xFF64748B))
            }

            SectionCard(title = "作文图片") {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { imagePicker.launch("image/*") }, modifier = Modifier.weight(1f)) {
                        Text("选图")
                    }
                    OutlinedButton(
                        onClick = {
                            if (ContextCompat.checkSelfPermission(
                                    context,
                                    Manifest.permission.CAMERA,
                                ) == PackageManager.PERMISSION_GRANTED
                            ) {
                                val uri = createCameraUri(context)
                                cameraUri = uri
                                cameraLauncher.launch(uri)
                            } else {
                                permissionLauncher.launch(Manifest.permission.CAMERA)
                            }
                        },
                        modifier = Modifier.weight(1f),
                    ) {
                        Text("拍照")
                    }
                }
                Text(uiState.selectedImageLabel.ifBlank { "还没有选择图片" })
                Button(
                    onClick = { viewModel.submitCorrection(context) },
                    enabled = !uiState.isLoading,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("开始批改")
                }
            }

            uiState.correction?.let { correction ->
                CorrectionResultCard(correction)
            }
        }
    }
}

@Composable
private fun SectionCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        border = BorderStroke(1.dp, Color(0xFFE2E8F0)),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            content()
        }
    }
}

@Composable
private fun TemplateRow(template: EssayTemplate, onClick: () -> Unit) {
    OutlinedButton(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Column(horizontalAlignment = Alignment.Start, modifier = Modifier.fillMaxWidth()) {
            Text(template.title, fontWeight = FontWeight.SemiBold)
            Text("${template.gradeLevel} · ${template.essayType}", color = Color(0xFF64748B))
        }
    }
}

@Composable
private fun CorrectionResultCard(correction: EssayCorrection) {
    SectionCard(title = "批改结果") {
        Text("总分 ${correction.score.total}", style = MaterialTheme.typography.headlineSmall)
        Text(
            "内容 ${correction.score.content} · 结构 ${correction.score.structure} · 语言 ${correction.score.language} · 标点字词 ${correction.score.mechanics} · 卷面 ${correction.score.presentation}",
            color = Color(0xFF475569),
        )
        LabeledText("总评", correction.comments.summary)
        BulletList("亮点", correction.comments.strengths)
        BulletList("问题", correction.comments.issues)
        BulletList("修改建议", correction.comments.suggestions)
        BulletList("错别字/识别疑点", correction.comments.spellingIssues)
        BulletList("语句问题", correction.comments.sentenceIssues)
        LabeledText("修改示例", correction.comments.revisionExample)
        LabeledText("鼓励", correction.comments.encouragement)
        LabeledText("老师备注", correction.comments.teacherNotes)
        LabeledText("OCR 文本", correction.ocrText)
    }
}

@Composable
private fun LabeledText(label: String, value: String) {
    if (value.isBlank()) return
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(label, fontWeight = FontWeight.SemiBold)
        Text(value)
    }
}

@Composable
private fun BulletList(label: String, items: List<String>) {
    if (items.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(label, fontWeight = FontWeight.SemiBold)
        items.forEach { item -> Text("· $item") }
    }
}

@Composable
private fun ErrorBanner(message: String?) {
    if (message.isNullOrBlank()) return
    Text(
        text = message,
        color = Color(0xFF991B1B),
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFFFEE2E2), RoundedCornerShape(8.dp))
            .padding(12.dp),
    )
}

@Composable
private fun LoadingRow(isLoading: Boolean) {
    if (!isLoading) return
    Row(verticalAlignment = Alignment.CenterVertically) {
        CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
        Spacer(modifier = Modifier.width(8.dp))
        Text("正在处理...")
    }
}

private fun createCameraUri(context: Context): Uri {
    val directory = File(context.cacheDir, "camera").apply { mkdirs() }
    val image = File.createTempFile("essay-", ".jpg", directory)
    return FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", image)
}
