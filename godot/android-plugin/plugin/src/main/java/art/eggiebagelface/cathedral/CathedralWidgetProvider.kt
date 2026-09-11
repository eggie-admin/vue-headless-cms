package art.eggiebagelface.cathedral

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.provider.Settings
import android.widget.RemoteViews
import android.widget.Toast
import androidx.webkit.WebViewCompat

class CathedralWidgetProvider : AppWidgetProvider() {
    companion object {
        private const val ACTION_START = "art.eggiebagelface.cathedral.widget.START"
        private const val ACTION_STOP = "art.eggiebagelface.cathedral.widget.STOP"
        private const val ACTION_SMOKE = "art.eggiebagelface.cathedral.widget.SMOKE"
        private const val ACTION_GUARD = "art.eggiebagelface.cathedral.widget.GUARD"
        private const val ACTION_BENCH = "art.eggiebagelface.cathedral.widget.BENCH"
        private const val ACTION_DEV = "art.eggiebagelface.cathedral.widget.DEV"
        private const val ACTION_OPEN = "art.eggiebagelface.cathedral.widget.OPEN"

        private const val SAMSUNG_BACKGROUND_ACTION =
            "com.samsung.android.sm.ACTION_OPEN_CHECKABLE_LISTACTIVITY"
        private const val SAMSUNG_DEVICE_CARE_PACKAGE = "com.samsung.android.lool"
        private const val SAMSUNG_NEVER_SLEEPING = 2
    }

    override fun onUpdate(context: Context, manager: AppWidgetManager, appWidgetIds: IntArray) {
        appWidgetIds.forEach { updateWidget(context, manager, it, "APP READY") }
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        when (intent.action) {
            ACTION_START, ACTION_OPEN -> openCathedral(context)
            ACTION_STOP -> {
                Toast.makeText(context, "Android manages LuHm OS app lifecycle", Toast.LENGTH_SHORT).show()
                updateAll(context, "OS MANAGED")
            }
            ACTION_SMOKE -> localSmoke(context)
            ACTION_GUARD -> openBackgroundGuard(context)
            ACTION_BENCH -> {
                updateAll(context, "OPEN APP")
                openCathedral(context)
            }
            ACTION_DEV -> openDeveloperOptions(context)
        }
    }

    private fun localSmoke(context: Context) {
        val launchable = context.packageManager.getLaunchIntentForPackage(context.packageName) != null
        val webView = WebViewCompat.getCurrentWebViewPackage(context)
        val status = when {
            !launchable -> "RED LAUNCHER"
            webView == null -> "YELLOW WV?"
            else -> "GREEN ${webViewLabel(context)}"
        }
        updateAll(context, status)
    }

    private fun webViewLabel(context: Context): String {
        val info = WebViewCompat.getCurrentWebViewPackage(context) ?: return "WV?"
        val major = info.versionName?.substringBefore('.') ?: "?"
        return "WV$major"
    }

    private fun openBackgroundGuard(context: Context) {
        val samsungIntent = Intent(SAMSUNG_BACKGROUND_ACTION).apply {
            setPackage(SAMSUNG_DEVICE_CARE_PACKAGE)
            putExtra("activity_type", SAMSUNG_NEVER_SLEEPING)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        val openedSamsung = runCatching {
            context.startActivity(samsungIntent)
            true
        }.getOrDefault(false)

        if (!openedSamsung) {
            val fallback = Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            runCatching { context.startActivity(fallback) }
                .onFailure {
                    Toast.makeText(context, "Battery guard settings unavailable", Toast.LENGTH_SHORT).show()
                    return
                }
        }

        Toast.makeText(
            context,
            "Add LuHm OS to Never sleeping apps only if you want persistent background work",
            Toast.LENGTH_LONG,
        ).show()
        updateAll(context, "GUARD MENU")
    }

    private fun openDeveloperOptions(context: Context) {
        val intent = Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        runCatching { context.startActivity(intent) }
            .onFailure {
                Toast.makeText(context, "Developer Options unavailable", Toast.LENGTH_SHORT).show()
            }
    }

    private fun openCathedral(context: Context) {
        val launchIntent = context.packageManager.getLaunchIntentForPackage(context.packageName)
        if (launchIntent == null) {
            Toast.makeText(context, "LuHm OS launcher unavailable", Toast.LENGTH_SHORT).show()
            updateAll(context, "RED LAUNCHER")
            return
        }
        launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(launchIntent)
        updateAll(context, "OPEN")
    }

    private fun updateAll(context: Context, status: String) {
        val manager = AppWidgetManager.getInstance(context)
        val ids = manager.getAppWidgetIds(ComponentName(context, CathedralWidgetProvider::class.java))
        ids.forEach { updateWidget(context, manager, it, status) }
    }

    private fun updateWidget(context: Context, manager: AppWidgetManager, widgetId: Int, status: String) {
        val views = RemoteViews(context.packageName, R.layout.cathedral_widget)
        views.setTextViewText(R.id.widget_status, status)
        views.setOnClickPendingIntent(R.id.widget_title, actionIntent(context, ACTION_OPEN))
        views.setOnClickPendingIntent(R.id.widget_on, actionIntent(context, ACTION_START))
        views.setOnClickPendingIntent(R.id.widget_off, actionIntent(context, ACTION_STOP))
        views.setOnClickPendingIntent(R.id.widget_smoke, actionIntent(context, ACTION_SMOKE))
        views.setOnClickPendingIntent(R.id.widget_guard, actionIntent(context, ACTION_GUARD))
        views.setOnClickPendingIntent(R.id.widget_bench, actionIntent(context, ACTION_BENCH))
        views.setOnClickPendingIntent(R.id.widget_dev, actionIntent(context, ACTION_DEV))
        manager.updateAppWidget(widgetId, views)
    }

    private fun actionIntent(context: Context, action: String): PendingIntent {
        val intent = Intent(context, CathedralWidgetProvider::class.java).setAction(action)
        return PendingIntent.getBroadcast(
            context,
            action.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }
}
