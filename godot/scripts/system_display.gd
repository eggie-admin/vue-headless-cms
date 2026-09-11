extends Node

signal metrics_changed(metrics: Dictionary)

const PORTRAIT_DESIGN := Vector2i(1080, 1920)
const LANDSCAPE_DESIGN := Vector2i(1920, 1080)

var metrics: Dictionary = {}

func _ready() -> void:
    var root := get_tree().root
    root.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
    root.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_EXPAND

    if DisplayServer.get_name() == "headless":
        metrics = {
            "display_server": "headless",
            "headless": true,
            "design_size": PORTRAIT_DESIGN,
        }
        print("LUHMOS_HEADLESS_DISPLAY_GREEN")
        return

    if OS.has_feature("android"):
        DisplayServer.screen_set_orientation(DisplayServer.SCREEN_SENSOR)

    if not root.size_changed.is_connected(_refresh):
        root.size_changed.connect(_refresh)

    call_deferred("_refresh")

func _refresh() -> void:
    var root := get_tree().root
    var window_size := root.size
    var portrait := window_size.y >= window_size.x
    var design_size := PORTRAIT_DESIGN if portrait else LANDSCAPE_DESIGN

    root.content_scale_size = design_size
    root.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
    root.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_EXPAND

    var screen_size := DisplayServer.screen_get_size(DisplayServer.SCREEN_OF_MAIN_WINDOW)
    var usable_rect := DisplayServer.screen_get_usable_rect(DisplayServer.SCREEN_OF_MAIN_WINDOW)
    var safe_area := DisplayServer.get_display_safe_area()
    var orientation := DisplayServer.screen_get_orientation(DisplayServer.SCREEN_OF_MAIN_WINDOW)

    metrics = {
        "display_server": DisplayServer.get_name(),
        "headless": false,
        "window_size": window_size,
        "screen_size": screen_size,
        "usable_rect": usable_rect,
        "safe_area": safe_area,
        "orientation": orientation,
        "portrait": portrait,
        "design_size": design_size,
    }
    metrics_changed.emit(metrics)
    print("LUHMOS_DISPLAY_METRICS ", metrics)

func snapshot() -> Dictionary:
    return metrics.duplicate(true)
