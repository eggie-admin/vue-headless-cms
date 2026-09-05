package art.eggiebagelface.cathedral

import android.app.admin.DevicePolicyManager
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
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

class CathedralAndroidPlugin(godot: Godot) : GodotPlugin(godot) {
    companion object {
        private const val APP_ORIGIN = "https://appassets.androidplatform.net"
        private const val CMS_URL = "$APP_ORIGIN/assets/cms/index.html"
        private const val BRIDGE_NAME = "CathedralBridge"
        private val CMS_MESSAGE_SIGNAL = SignalInfo("cms_message", String::class.java)
    }

    private var cmsView: WebView? = null
    @Volatile private var cmsOpen = false

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
    fun isManagedKioskPermitted(): Boolean {
        val hostActivity = activity ?: return false
        val dpm = hostActivity.getSystemService(DevicePolicyManager::class.java) ?: return false
        return dpm.isLockTaskPermitted(hostActivity.packageName)
    }

    @UsedByGodot
    fun requestManagedKioskStart(): Boolean {
        val hostActivity = activity ?: return false
        val dpm = hostActivity.getSystemService(DevicePolicyManager::class.java) ?: return false
        if (!dpm.isLockTaskPermitted(hostActivity.packageName)) {
            return false
        }
        runOnHostThread {
            runCatching { hostActivity.startLockTask() }
            setImmersiveKiosk(true)
        }
        return true
    }

    @UsedByGodot
    fun requestManagedKioskStop(): Boolean {
        val hostActivity = activity ?: return false
        runOnHostThread {
            runCatching { hostActivity.stopLockTask() }
            setImmersiveKiosk(false)
        }
        return true
    }

    @UsedByGodot
    fun deviceSnapshot(): String {
        val hostActivity = activity ?: return "{}"
        val webView = WebViewCompat.getCurrentWebViewPackage(hostActivity)
        val packageManager = hostActivity.packageManager
        val dpm = hostActivity.getSystemService(DevicePolicyManager::class.java)
        val kioskPermitted = dpm?.isLockTaskPermitted(hostActivity.packageName) == true
        val payload = JSONObject()
            .put("manufacturer", Build.MANUFACTURER)
            .put("model", Build.MODEL)
            .put("sdk", Build.VERSION.SDK_INT)
            .put("abi", Build.SUPPORTED_ABIS.firstOrNull() ?: "unknown")
            .put("webview_package", webView?.packageName ?: "unknown")
            .put("webview_version", webView?.versionName ?: "unknown")
            .put("vulkan_feature", packageManager.hasSystemFeature(PackageManager.FEATURE_VULKAN_HARDWARE_LEVEL))
            .put("developer_options_control", "open_only")
            .put("kiosk_control", "managed_lock_task_when_allowlisted")
            .put("managed_kiosk_permitted", kioskPermitted)
        return payload.toString()
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
                emitSignal(CMS_MESSAGE_SIGNAL.name, data)
                replyProxy.postMessage("{\"ok\":true}")
            }
        }

        val params = FrameLayout.LayoutParams(
            (hostActivity.resources.displayMetrics.widthPixels * 0.68f).toInt(),
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
