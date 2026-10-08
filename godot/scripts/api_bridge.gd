extends Node

signal control_plane_status(ok: bool)

const HEALTH_URL := "http://127.0.0.1:8000/api/health"

func _ready() -> void:
    probe_control_plane()

func probe_control_plane() -> void:
    var request := HTTPRequest.new()
    add_child(request)
    request.request_completed.connect(_on_probe_completed.bind(request))
    var error := request.request(HEALTH_URL)
    if error != OK:
        request.queue_free()
        control_plane_status.emit(false)

func _on_probe_completed(_result: int, response_code: int, _headers: PackedStringArray, _body: PackedByteArray, request: HTTPRequest) -> void:
    request.queue_free()
    control_plane_status.emit(response_code >= 200 and response_code < 300)
