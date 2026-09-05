package art.eggiebagelface.cathedral

import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import android.provider.Settings
import android.view.Gravity
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
import java.util.UUID

class CathedralAndroidPlugin(godot: Godot) : GodotPlugin(godot) {
    companion object {
        private const val APP_ORIGIN = "https://appassets.androidplatform.net"
        private const val CMS_URL = "$APP_ORIGIN/assets/cms/index.html"
        private const val BRIDGE_NAME = "CathedralBridge"
        private const val GALLERY_REQUEST_CODE = 9401
        private const val MAX_GALLERY_BYTES = 50L * 1024L * 1024L
        private val CMS_MESSAGE_SIGNAL = SignalInfo("cms_message", String::class.java)
        private val GALLERY_IMAGE_SIGNAL = SignalInfo("gallery_image_selected", String::class.java)
    }

    private var cmsView: WebView? = null
    @Volatile private var cmsOpen = false

    override fun getPluginName() = BuildConfig.GODOT_PLUGIN_NAME

    override fun getPluginSignals() = setOf(CMS_MESSAGE_SIGNAL, GALLERY_IMAGE_SIGNAL)

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
    fun pickGalleryImage() {
        runOnHostThread {
            val hostActivity = activity ?: return@runOnHostThread
            val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                Intent(MediaStore.ACTION_PICK_IMAGES).apply { type = "image/*" }
            } else {
                Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE)
                    type = "image/*"
                }
            }
            runCatching {
                hostActivity.startActivityForResult(intent, GALLERY_REQUEST_CODE)
            }.onFailure { error ->
                emitGalleryResult(JSONObject()
                    .put("ok", false)
                    .put("error", "picker_launch_failed")
                    .put("detail", error.javaClass.simpleName))
            }
        }
    }

    override fun onMainActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        if (requestCode != GALLERY_REQUEST_CODE) {
            super.onMainActivityResult(requestCode, resultCode, data)
            return
        }
        if (resultCode != Activity.RESULT_OK) {
            emitGalleryResult(JSONObject().put("ok", false).put("error", "picker_cancelled"))
            return
        }
        val uri = data?.data
        if (uri == null) {
            emitGalleryResult(JSONObject().put("ok", false).put("error", "picker_missing_uri"))
            return
        }
        val payload = runCatching { cacheGallerySelection(uri) }
            .getOrElse { error ->
                JSONObject()
                    .put("ok", false)
                    .put("error", "picker_copy_failed")
                    .put("detail", error.javaClass.simpleName)
            }
        emitGalleryResult(payload)
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
            .put("gallery_control", "system_photo_picker")
        return payload.toString()
    }

    private fun cacheGallerySelection(uri: Uri): JSONObject {
        require(uri.scheme == "content") { "Only content:// gallery URIs are accepted" }
        val hostActivity = activity ?: error("Godot Activity unavailable")
        val resolver = hostActivity.contentResolver
        val mime = resolver.getType(uri) ?: "application/octet-stream"
        require(mime.startsWith("image/")) { "Selected item is not an image" }

        val extension = when (mime) {
            "image/jpeg" -> "jpg"
            "image/png" -> "png"
            "image/webp" -> "webp"
            "image/gif" -> "gif"
            "image/heic", "image/heif" -> "heic"
            else -> "img"
        }
        val cacheDir = File(hostActivity.cacheDir, "edge-gallery").apply { mkdirs() }
        val target = File(cacheDir, "${UUID.randomUUID()}.$extension")

        var total = 0L
        try {
            resolver.openInputStream(uri)?.use { input ->
                target.outputStream().use { output ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        total += read
                        require(total <= MAX_GALLERY_BYTES) { "Selected image exceeds 50 MiB limit" }
                        output.write(buffer, 0, read)
                    }
                }
            } ?: error("Unable to open selected image")
        } catch (error: Throwable) {
            target.delete()
            throw error
        }

        return JSONObject()
            .put("ok", true)
            .put("mime", mime)
            .put("bytes", total)
            .put("cache_path", target.absolutePath)
    }

    private fun emitGalleryResult(payload: JSONObject) {
        emitSignal(GALLERY_IMAGE_SIGNAL.name, payload.toString())
    }

    private fun ensureCmsView(): WebView {
        cmsView?.let { return it }

        val hostActivity = activity ?: error("Godot Activity unavailable for Cathedral CMS")
        val assetLoader = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(hostActivity))
            .build()

        val view = WebView(hostActivity)
        view.setBackgroundColor(Color.rgb(17, 18, 22))
        view.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            javaScriptCanOpenWindowsAutomatically = false
            setSupportMultipleWindows(false)
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
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
                if (uri.scheme == "https" || uri.scheme == "http") {
                    runCatching { hostActivity.startActivity(Intent(Intent.ACTION_VIEW, uri)) }
                } else {
                    emitSignal(CMS_MESSAGE_SIGNAL.name, JSONObject()
                        .put("type", "cms.navigation.blocked")
                        .put("scheme", uri.scheme ?: "unknown")
                        .toString())
                }
                return true
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
                if (data.length > 32768) {
                    replyProxy.postMessage("{\"ok\":false,\"error\":\"message_too_large\"}")
                    return@addWebMessageListener
                }
                emitSignal(CMS_MESSAGE_SIGNAL.name, data)
                replyProxy.postMessage("{\"ok\":true}")
            }
        }

        val metrics = hostActivity.resources.displayMetrics
        val widthDp = metrics.widthPixels / metrics.density
        val panelWidth = if (widthDp <= 720f) {
            ViewGroup.LayoutParams.MATCH_PARENT
        } else {
            (metrics.widthPixels * 0.68f).toInt()
        }
        val params = FrameLayout.LayoutParams(
            panelWidth,
            ViewGroup.LayoutParams.MATCH_PARENT
        ).apply {
            gravity = Gravity.END
        }

        hostActivity.addContentView(view, params)
        view.loadUrl(CMS_URL)
        cmsView = view
        return view
    }
}
