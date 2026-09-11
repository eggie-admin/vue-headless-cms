extends SceneTree

func _initialize() -> void:
    assert(DisplayServer.get_name() == "headless")
    assert(ProjectSettings.get_setting("application/config/name") == "LuHm OS")
    assert(ProjectSettings.get_setting("display/window/size/viewport_width") == 1080)
    assert(ProjectSettings.get_setting("display/window/size/viewport_height") == 1920)
    assert(ProjectSettings.get_setting("display/window/handheld/orientation") == DisplayServer.SCREEN_SENSOR)
    assert(ProjectSettings.get_setting("display/window/stretch/mode") == "canvas_items")
    assert(ProjectSettings.get_setting("display/window/stretch/aspect") == "expand")
    print("LUHMOS_HEADLESS_GODOT_GREEN")
    quit(0)
