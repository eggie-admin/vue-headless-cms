package art.eggiebagelface.cathedral

import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
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

    private fun ensureCmsView(): WebView {
        cmsView?.let { return it }

        val hostActivity = activity
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
