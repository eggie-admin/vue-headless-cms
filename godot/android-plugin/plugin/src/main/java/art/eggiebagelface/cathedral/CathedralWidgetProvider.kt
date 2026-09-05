package art.eggiebagelface.cathedral

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings
import android.widget.RemoteViews
import android.widget.Toast
import androidx.webkit.WebViewCompat
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

class CathedralWidgetProvider : AppWidgetProvider() {
    companion object {
        private const val ACTION_START = "art.eggiebagelface.cathedral.widget.START"
        private const val ACTION_STOP = "art.eggiebagelface.cathedral.widget.STOP"
        private const val ACTION_SMOKE = "art.eggiebagelface.cathedral.widget.SMOKE"
        private const val ACTION_GUARD = "art.eggiebagelface.cathedral.widget.GUARD"
        private const val ACTION_BENCH = "art.eggiebagelface.cathedral.widget.BENCH"
        private const val ACTION_DEV = "art.eggiebagelface.cathedral.widget.DEV"
        private const val ACTION_OPEN = "art.eggiebagelface.cathedral.widget.OPEN"

        private const val TERMUX_PACKAGE = "com.termux"
        private const val TERMUX_RUN_SERVICE = "com.termux.app.RunCommandService"
        private const val TERMUX_ACTION = "com.termux.RUN_COMMAND"
        private const val TERMUX_PATH = "com.termux.RUN_COMMAND_PATH"
        private const val TERMUX_ARGS = "com.termux.RUN_COMMAND_ARGUMENTS"
        private const val TERMUX_WORKDIR = "com.termux.RUN_COMMAND_WORKDIR"
        private const val TERMUX_BACKGROUND = "com.termux.RUN_COMMAND_BACKGROUND"
        private const val TERMUX_HOME = "/data/data/com.termux/files/home"
        private const val CONTROL_SCRIPT = "$TERMUX_HOME/kai9000/bin/cathedral-control"
        private const val HEALTH_URL = "http://127.0.0.1:8000/api/health"

        private const val SAMSUNG_BACKGROUND_ACTION =
            "com.samsung.android.sm.ACTION_OPEN_CHECKABLE_LISTACTIVITY"
        private const val SAMSUNG_DEVICE_CARE_PACKAGE = "com.samsung.android.lool"
        private const val SAMSUNG_NEVER_SLEEPING = 2

        private val executor = Executors.newSingleThreadExecutor()
    }

    override fun onUpdate(context: Context, manager: AppWidgetManager, appWidgetIds: IntArray) {
        appWidgetIds.forEach { updateWidget(context, manager, it, "READY") }
    }

    override fun onReceive(context: Context, intent: Intent) {
        super.onReceive(context, intent)
        when (intent.action) {
            ACTION_START -> runControlAndProbe(context, "start", expectedOnline = true)
            ACTION_STOP -> runControlAndProbe(context, "stop", expectedOnline = false)
            ACTION_SMOKE -> probeAsync(context)
            ACTION_GUARD -> openBackgroundGuard(context)
            ACTION_BENCH -> {
                if (invokeTermux(context, "benchmark")) {
                    updateAll(context, "BENCH RUN")
                }
            }
            ACTION_DEV -> openDeveloperOptions(context)
            ACTION_OPEN -> openCathedral(context)
        }
    }

    private fun runControlAndProbe(context: Context, command: String, expectedOnline: Boolean) {
        val pendingResult = goAsync()
        updateAll(context, if (expectedOnline) "STARTING" else "STOPPING")
        executor.execute {
            try {
                if (!invokeTermux(context, command)) {
                    updateAll(context, "TERMUX PERM")
                    return@execute
                }
                Thread.sleep(if (expectedOnline) 1400L else 800L)
                val online = probeHealth()
                val status = when {
                    expectedOnline && online -> "GREEN ${webViewLabel(context)}"
                    !expectedOnline && !online -> "OFF"
                    expectedOnline -> "START FAIL"
                    else -> "STILL ON"
                }
                updateAll(context, status)
            } finally {
                pendingResult.finish()
            }
        }
    }

    private fun probeAsync(context: Context) {
        val pendingResult = goAsync()
        updateAll(context, "SMOKE...")
        executor.execute {
            try {
                val status = if (probeHealth()) "GREEN ${webViewLabel(context)}" else "RED /health"
                updateAll(context, status)
            } finally {
                pendingResult.finish()
            }
        }
    }

    private fun invokeTermux(context: Context, command: String): Boolean {
        return try {
            val intent = Intent(TERMUX_ACTION).apply {
                component = ComponentName(TERMUX_PACKAGE, TERMUX_RUN_SERVICE)
                putExtra(TERMUX_PATH, CONTROL_SCRIPT)
                putExtra(TERMUX_ARGS, arrayOf(command))
                putExtra(TERMUX_WORKDIR, TERMUX_HOME)
                putExtra(TERMUX_BACKGROUND, true)
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
            true
        } catch (_: SecurityException) {
            Toast.makeText(context, "Grant Video Forge: Run commands in Termux", Toast.LENGTH_LONG).show()
            false
        } catch (_: Exception) {
            Toast.makeText(context, "Termux control unavailable", Toast.LENGTH_SHORT).show()
            false
        }
    }

    private fun probeHealth(): Boolean {
        return runCatching {
            val connection = URL(HEALTH_URL).openConnection() as HttpURLConnection
            connection.requestMethod = "GET"
            connection.connectTimeout = 900
            connection.readTimeout = 900
            connection.useCaches = false
            try {
                connection.responseCode == HttpURLConnection.HTTP_OK
            } finally {
                connection.disconnect()
            }
        }.getOrDefault(false)
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
            "Add Termux + Video Forge to Never sleeping apps",
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
            Toast.makeText(context, "Cathedral launcher unavailable", Toast.LENGTH_SHORT).show()
            return
        }
        launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(launchIntent)
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
