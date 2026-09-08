package art.eggiebagelface.cathedral

/**
 * Internal target for immutable widget PendingIntents.
 *
 * The AppWidgetProvider itself must remain exported for Android widget lifecycle
 * broadcasts. This subclass is declared non-exported and is the only receiver
 * allowed by CathedralWidgetProvider to execute KAI control actions.
 */
class CathedralWidgetActionReceiver : CathedralWidgetProvider()
