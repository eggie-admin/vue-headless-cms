extends Node

signal cms_ready
signal cms_message(message: String)

const PLUGIN_NAME := "CathedralAndroid"
var _plugin = null

func _ready() -> void:
    if OS.get_name() != "Android":
        return
    if not Engine.has_singleton(PLUGIN_NAME):
        push_error("CathedralAndroid plugin is missing")
        return
    _plugin = Engine.get_singleton(PLUGIN_NAME)
    if _plugin.has_signal("cms_message"):
        _plugin.connect("cms_message", _on_cms_message)
    if _plugin.has_signal("gallery_image_selected"):
        _plugin.connect("gallery_image_selected", _on_gallery_image_selected)
    await get_tree().create_timer(0.35).timeout
    _plugin.openCms()

func open_cms() -> void:
    if _plugin: _plugin.openCms()

func close_cms() -> void:
    if _plugin: _plugin.closeCms()

func send_to_cms(message: Dictionary) -> void:
    if _plugin: _plugin.postToCms(JSON.stringify(message))

func _on_gallery_image_selected(raw: String) -> void:
    if raw.length() > 8192:
        push_warning("Rejected oversized gallery result")
        return
    var parsed = JSON.parse_string(raw)
    if parsed is Dictionary:
        send_to_cms({"type": "android.gallery.selected", "payload": parsed})

func _on_cms_message(raw: String) -> void:
    if raw.length() > 32768:
        push_warning("Rejected oversized CMS bridge message")
        return
    cms_message.emit(raw)
    var parsed = JSON.parse_string(raw)
    if not parsed is Dictionary:
        return
    var message: Dictionary = parsed
    var kind := String(message.get("type", ""))
    var payload = message.get("payload", {})
    if not payload is Dictionary:
        payload = {}
    var host := get_parent()
    var registry := host.get_node_or_null("CmsRegistry") if host else null
    match kind:
        "cms.ready":
            cms_ready.emit()
            if registry: registry.sync()
        "cms.document.saved", "cms.document.deleted":
            if registry: registry.sync()
        "godot.window.open":
            var allowed_panels := ["renderQueue", "lumAgent", "cutsceneDirector", "cms"]
            var panel := String(payload.get("panel", ""))
            if panel in allowed_panels and host and host.has_method("open_tool_window"):
                host.open_tool_window(panel)
        "godot.avatar.state":
            var allowed_states := ["idle", "thinking", "speaking", "rendering", "error"]
            var state := String(payload.get("state", "idle"))
            if state in allowed_states and host and host.has_method("set_avatar_state"):
                host.set_avatar_state(StringName(state))
        "android.gallery.pick":
            if _plugin and _plugin.has_method("pickGalleryImage"):
                _plugin.pickGalleryImage()
        "android.kiosk.set":
            if _plugin and _plugin.has_method("setImmersiveKiosk"):
                _plugin.setImmersiveKiosk(bool(payload.get("enabled", false)))
        "android.device.snapshot":
            if _plugin and _plugin.has_method("deviceSnapshot"):
                var snapshot = JSON.parse_string(String(_plugin.deviceSnapshot()))
                if snapshot is Dictionary:
                    send_to_cms({"type": "android.device.snapshot", "payload": snapshot})
        _:
            pass
