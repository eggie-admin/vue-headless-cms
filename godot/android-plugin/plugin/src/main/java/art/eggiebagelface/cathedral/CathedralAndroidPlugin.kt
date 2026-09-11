package art.eggiebagelface.cathedral

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInfo
import android.content.pm.PackageInstaller
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.webkit.CookieManager
import android.webkit.RenderProcessGoneDetail
import android.webkit.WebMessage
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import androidx.webkit.WebViewAssetLoader
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import org.godotengine.godot.Godot
import org.godotengine.godot.plugin.GodotPlugin
import org.godotengine.godot.plugin.SignalInfo
import org.godotengine.godot.plugin.UsedByGodot
import org.json.JSONObject
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

class CathedralAndroidPlugin(godot: Godot) : GodotPlugin(godot) {
    companion object {
        private const val APP_ORIGIN = "https://appassets.androidplatform.net"
        private const val CMS_URL = "$APP_ORIGIN/assets/cms/index.html"
        private const val BRIDGE_NAME = "CathedralBridge"
        private const val MAX_APK_BYTES = 350L * 1024L * 1024L
        internal const val ACTION_UPDATE_STATUS = "art.eggiebagelface.cathedral.UPDATE_STATUS"
        private val CMS_MESSAGE_SIGNAL = SignalInfo("cms_message", String::class.java)

        @Volatile
        private var activePlugin: CathedralAndroidPlugin? = null

        internal fun publishInstallerStatus(context: Context, intent: Intent) {
            val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)
            val statusMessage = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE).orEmpty()
            when (status) {
                PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                    activePlugin?.emitUpdateEvent("app.update.confirmation", "Android install confirmation opened.")
                    val confirmIntent: Intent? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                    } else {
                        @Suppress("DEPRECATION")
                        intent.getParcelableExtra(Intent.EXTRA_INTENT)
                    }
                    confirmIntent?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    if (confirmIntent != null) {
                        context.startActivity(confirmIntent)
                    }
                }

                PackageInstaller.STATUS_SUCCESS -> {
                    activePlugin?.emitUpdateEvent("app.update.success", "LuHm OS update installed.")
                }

                else -> {
                    activePlugin?.emitUpdateEvent(
                        "app.update.error",
                        statusMessage.ifBlank { "Android installer failed with status $status." }
                    )
                }
            }
        }
    }

    private var cmsView: WebView? = null
    @Volatile private var cmsOpen = false

    init {
        activePlugin = this
    }

    override fun getPluginName() = BuildConfig.GODOT_PLUGIN_NAME

    override fun getPluginSignals() = setOf(CMS_MESSAGE_SIGNAL)

    @UsedByGodot
    fun openCms() {
        runOnHostThread {
            val view = ensureCmsView()
            view.visibility = View.VISIBLE
            view.bringToFront()
            cmsOpen = true
        }
    }

    @UsedByGodot
    fun closeCms() {
        runOnHostThread {
            cmsView?.visibility = View.GONE
            cmsOpen = false
        }
    }

    @UsedByGodot
    fun isCmsOpen(): Boolean = cmsOpen

    @UsedByGodot
    fun postToCms(message: String) {
        runOnHostThread {
            cmsView?.postWebMessage(WebMessage(message), Uri.parse(APP_ORIGIN))
        }
    }

    @UsedByGodot
    fun openDeveloperOptions() {
        runOnHostThread {
            val hostActivity = activity ?: return@runOnHostThread
            val intent = Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)
            runCatching { hostActivity.startActivity(intent) }
        }
    }

    @UsedByGodot
    fun setImmersiveKiosk(enabled: Boolean) {
        runOnHostThread {
            val hostActivity = activity ?: return@runOnHostThread
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val controller = hostActivity.window.insetsController ?: return@runOnHostThread
                if (enabled) {
                    controller.hide(WindowInsets.Type.statusBars() or WindowInsets.Type.navigationBars())
                    controller.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                } else {
                    controller.show(WindowInsets.Type.statusBars() or WindowInsets.Type.navigationBars())
                }
            } else {
                @Suppress("DEPRECATION")
                hostActivity.window.decorView.systemUiVisibility = if (enabled) {
                    View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
                        View.SYSTEM_UI_FLAG_FULLSCREEN or
                        View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                        View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                        View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or
                        View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                } else {
                    View.SYSTEM_UI_FLAG_VISIBLE
                }
            }
        }
    }

    @UsedByGodot
    fun deviceSnapshot(): String {
        val hostActivity = activity ?: return "{}"
        val webView = WebViewCompat.getCurrentWebViewPackage(hostActivity)
        val packageManager = hostActivity.packageManager
        val current = currentPackageInfo(packageManager, hostActivity.packageName)
        val payload = JSONObject()
            .put("manufacturer", Build.MANUFACTURER)
            .put("model", Build.MODEL)
            .put("sdk", Build.VERSION.SDK_INT)
            .put("abi", Build.SUPPORTED_ABIS.firstOrNull() ?: "unknown")
            .put("webview_package", webView?.packageName ?: "unknown")
            .put("webview_version", webView?.versionName ?: "unknown")
            .put("vulkan_feature", packageManager.hasSystemFeature(PackageManager.FEATURE_VULKAN_HARDWARE_LEVEL))
            .put("developer_options_control", "open_only")
            .put("kiosk_control", "immersive_app_shell")
            .put("package_name", hostActivity.packageName)
            .put("version_code", current?.let(::packageVersionCode) ?: -1L)
            .put("can_request_package_installs", canRequestPackageInstalls(hostActivity))
        return payload.toString()
    }

    private fun ensureCmsView(): WebView {
        cmsView?.let { return it }

        val hostActivity = activity ?: error("Godot Activity unavailable for Cathedral CMS")
        val assetLoader = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(hostActivity))
            .build()

        val view = WebView(hostActivity)
        view.setBackgroundColor(Color.rgb(3, 9, 20))
        view.overScrollMode = View.OVER_SCROLL_NEVER
        view.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            setSupportMultipleWindows(false)
            mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
        }
        CookieManager.getInstance().setAcceptThirdPartyCookies(view, false)
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)

        view.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                return assetLoader.shouldInterceptRequest(request.url)
            }

            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val uri = request.url
                if (uri.scheme == "https" && uri.host == "appassets.androidplatform.net") {
                    return false
                }
                runCatching {
                    hostActivity.startActivity(Intent(Intent.ACTION_VIEW, uri))
                }
                return true
            }

            override fun onPageFinished(view: WebView, url: String) {
                super.onPageFinished(view, url)
                emitSignal(CMS_MESSAGE_SIGNAL.name, "{\"type\":\"cms.page.finished\",\"url\":\"$url\"}")
            }

            override fun onRenderProcessGone(view: WebView, detail: RenderProcessGoneDetail): Boolean {
                view.destroy()
                cmsView = null
                cmsOpen = false
                emitSignal(CMS_MESSAGE_SIGNAL.name, "{\"type\":\"cms.renderer.gone\"}")
                return true
            }
        }

        if (WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            WebViewCompat.addWebMessageListener(
                view,
                BRIDGE_NAME,
                setOf(APP_ORIGIN)
            ) { _, message, sourceOrigin, isMainFrame, replyProxy ->
                if (!isMainFrame || sourceOrigin.toString() != APP_ORIGIN) {
                    return@addWebMessageListener
                }
                val data = message.data ?: return@addWebMessageListener
                val parsed = runCatching { JSONObject(data) }.getOrNull()
                if (parsed?.optString("type") == "app.update.install") {
                    val payload = parsed.optJSONObject("payload")
                    val updateUrl = payload?.optString("url").orEmpty()
                    beginApkUpdate(updateUrl)
                }
                emitSignal(CMS_MESSAGE_SIGNAL.name, data)
                replyProxy.postMessage("{\"ok\":true}")
            }
        }

        val params = FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        )

        hostActivity.addContentView(view, params)
        view.loadUrl(CMS_URL)
        cmsView = view
        return view
    }

    private fun beginApkUpdate(rawUrl: String) {
        val hostActivity = activity ?: run {
            emitUpdateEvent("app.update.error", "Android host activity unavailable.")
            return
        }
        val uri = runCatching { Uri.parse(rawUrl.trim()) }.getOrNull()
        if (uri == null || uri.scheme != "https" || uri.host.isNullOrBlank()) {
            emitUpdateEvent("app.update.error", "Update URL must be HTTPS.")
            return
        }

        if (!canRequestPackageInstalls(hostActivity)) {
            emitUpdateEvent(
                "app.update.permission.required",
                "Enable Allow from this source for LuHm OS, then tap Install / Update again."
            )
            runOnHostThread {
                val settingsIntent = Intent(
                    Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:${hostActivity.packageName}")
                )
                hostActivity.startActivity(settingsIntent)
            }
            return
        }

        emitUpdateEvent("app.update.downloading", "Downloading LuHm OS update…")
        Thread({ downloadVerifyAndInstall(hostActivity.applicationContext, uri.toString()) }, "luhmos-apk-updater").start()
    }

    private fun downloadVerifyAndInstall(context: Context, url: String) {
        var connection: HttpURLConnection? = null
        try {
            val updateDir = File(context.cacheDir, "updates").apply { mkdirs() }
            val apkFile = File(updateDir, "luhmos-update.apk")
            if (apkFile.exists()) apkFile.delete()

            connection = (URL(url).openConnection() as HttpURLConnection).apply {
                instanceFollowRedirects = true
                connectTimeout = 20_000
                readTimeout = 60_000
                requestMethod = "GET"
                setRequestProperty("User-Agent", "LuHmOS-Updater/1.0")
            }
            val status = connection.responseCode
            if (status !in 200..299) error("Update download failed: HTTP $status")
            val declaredLength = connection.contentLengthLong
            if (declaredLength > MAX_APK_BYTES) error("Update APK exceeds size limit")

            val digest = MessageDigest.getInstance("SHA-256")
            var total = 0L
            connection.inputStream.use { input ->
                FileOutputStream(apkFile).use { output ->
                    val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        total += count
                        if (total > MAX_APK_BYTES) error("Update APK exceeds size limit")
                        digest.update(buffer, 0, count)
                        output.write(buffer, 0, count)
                    }
                    output.fd.sync()
                }
            }
            if (total <= 0L) error("Downloaded APK is empty")
            val sha256 = digest.digest().joinToString("") { "%02x".format(it) }

            val packageManager = context.packageManager
            val archive = archivePackageInfo(packageManager, apkFile)
                ?: error("Downloaded file is not a readable APK")
            if (archive.packageName != context.packageName) {
                error("Rejected APK package ${archive.packageName}; expected ${context.packageName}")
            }

            val installed = currentPackageInfo(packageManager, context.packageName)
                ?: error("Installed LuHm OS package metadata unavailable")
            val archiveSigners = signerDigests(archive)
            val installedSigners = signerDigests(installed)
            if (archiveSigners.isEmpty() || installedSigners.isEmpty() || archiveSigners.intersect(installedSigners).isEmpty()) {
                error("Rejected APK: signing certificate does not match installed LuHm OS")
            }

            val archiveVersion = packageVersionCode(archive)
            val installedVersion = packageVersionCode(installed)
            if (archiveVersion < installedVersion) {
                error("Rejected downgrade $archiveVersion < $installedVersion")
            }

            emitUpdateEvent(
                "app.update.verified",
                "Verified LuHm OS v$archiveVersion · ${sha256.take(12)}…"
            )
            commitPackageInstallerSession(context, apkFile, sha256, archiveVersion)
        } catch (error: Throwable) {
            emitUpdateEvent("app.update.error", error.message ?: error.javaClass.simpleName)
        } finally {
            connection?.disconnect()
        }
    }

    private fun commitPackageInstallerSession(context: Context, apkFile: File, sha256: String, versionCode: Long) {
        val installer = context.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL).apply {
            setAppPackageName(context.packageName)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_REQUIRED)
            }
        }
        val sessionId = installer.createSession(params)
        installer.openSession(sessionId).use { session ->
            FileInputStream(apkFile).use { input ->
                session.openWrite("base.apk", 0, apkFile.length()).use { output ->
                    input.copyTo(output)
                    session.fsync(output)
                }
            }
            val statusIntent = Intent(context, CathedralUpdateReceiver::class.java)
                .setAction(ACTION_UPDATE_STATUS)
                .putExtra("sha256", sha256)
                .putExtra("version_code", versionCode)
            val pendingIntent = PendingIntent.getBroadcast(
                context,
                sessionId,
                statusIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_MUTABLE
            )
            emitUpdateEvent("app.update.staged", "APK staged. Handing off to Android installer…")
            session.commit(pendingIntent.intentSender)
        }
        apkFile.delete()
    }

    private fun emitUpdateEvent(type: String, message: String) {
        val event = JSONObject()
            .put("type", type)
            .put("payload", JSONObject().put("message", message))
            .toString()
        runOnHostThread {
            cmsView?.postWebMessage(WebMessage(event), Uri.parse(APP_ORIGIN))
        }
    }

    private fun canRequestPackageInstalls(context: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.packageManager.canRequestPackageInstalls()
        } else {
            true
        }
    }

    private fun currentPackageInfo(packageManager: PackageManager, packageName: String): PackageInfo? {
        return runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                packageManager.getPackageInfo(
                    packageName,
                    PackageManager.PackageInfoFlags.of(PackageManager.GET_SIGNING_CERTIFICATES.toLong())
                )
            } else {
                @Suppress("DEPRECATION")
                packageManager.getPackageInfo(packageName, PackageManager.GET_SIGNING_CERTIFICATES)
            }
        }.getOrNull()
    }

    private fun archivePackageInfo(packageManager: PackageManager, apkFile: File): PackageInfo? {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            packageManager.getPackageArchiveInfo(
                apkFile.absolutePath,
                PackageManager.PackageInfoFlags.of(PackageManager.GET_SIGNING_CERTIFICATES.toLong())
            )
        } else {
            @Suppress("DEPRECATION")
            packageManager.getPackageArchiveInfo(apkFile.absolutePath, PackageManager.GET_SIGNING_CERTIFICATES)
        }
    }

    private fun packageVersionCode(info: PackageInfo): Long {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            info.longVersionCode
        } else {
            @Suppress("DEPRECATION")
            info.versionCode.toLong()
        }
    }

    private fun signerDigests(info: PackageInfo): Set<String> {
        val signatures = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            val signingInfo = info.signingInfo ?: return emptySet()
            if (signingInfo.hasMultipleSigners()) {
                signingInfo.apkContentsSigners
            } else {
                signingInfo.signingCertificateHistory
            }
        } else {
            @Suppress("DEPRECATION")
            info.signatures
        }
        return signatures.orEmpty().map { signature ->
            MessageDigest.getInstance("SHA-256")
                .digest(signature.toByteArray())
                .joinToString("") { "%02x".format(it) }
        }.toSet()
    }
}

class CathedralUpdateReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != CathedralAndroidPlugin.ACTION_UPDATE_STATUS) return
        CathedralAndroidPlugin.publishInstallerStatus(context, intent)
    }
}
