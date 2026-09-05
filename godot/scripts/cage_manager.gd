extends Node

signal avatar_state_changed(state: StringName)

var avatar_state: StringName = &"idle"

func _ready() -> void:
    get_window().gui_embed_subwindows = true
    set_avatar_state(&"idle")

func set_avatar_state(next_state: StringName) -> void:
    avatar_state = next_state
    avatar_state_changed.emit(avatar_state)

func open_tool_window(title: String, size := Vector2i(520, 360)) -> Window:
    var window := Window.new()
    window.title = title
    window.size = size
    window.transient = false
    window.exclusive = false
    add_child(window)
    window.popup_centered()
    return window
