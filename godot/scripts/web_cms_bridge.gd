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

    await get_tree().create_timer(0.35).timeout
    _plugin.openCms()

func open_cms() -> void:
    if _plugin:
        _plugin.openCms()

func close_cms() -> void:
    if _plugin:
        _plugin.closeCms()

func send_to_cms(message: Dictionary) -> void:
    if _plugin:
        _plugin.postToCms(JSON.stringify(message))

func _on_cms_message(raw: String) -> void:
    cms_message.emit(raw)
    var parsed = JSON.parse_string(raw)
    if not parsed is Dictionary:
        return

    var message: Dictionary = parsed
    var kind := String(message.get("type", ""))
    var payload = message.get("payload", {})
    if not payload is Dictionary:
        payload = {}

    match kind:
        "cms.ready":
            cms_ready.emit()
        "godot.window.open":
            var panel := String(payload.get("panel", "CMS Tool"))
            var host := get_parent()
            if host and host.has_method("open_tool_window"):
                host.open_tool_window(panel)
        "godot.avatar.state":
            var state := StringName(String(payload.get("state", "idle")))
            var host := get_parent()
            if host and host.has_method("set_avatar_state"):
                host.set_avatar_state(state)
        _:
            pass
