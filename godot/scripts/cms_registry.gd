extends Node

signal synced(revision: int)
signal document_changed(document_id: String)
signal sync_failed(reason: String)

const MANIFEST_URL := "http://127.0.0.1:8000/api/cms/runtime-manifest"

var revision: int = 0
var documents: Dictionary = {}
var _syncing := false

func _ready() -> void:
    sync()

func sync() -> void:
    if _syncing:
        return
    _syncing = true
    var request := HTTPRequest.new()
    add_child(request)
    request.request_completed.connect(_on_sync_completed.bind(request))
    var error := request.request(MANIFEST_URL)
    if error != OK:
        _syncing = false
        request.queue_free()
        sync_failed.emit("request error %s" % error)

func get_document(document_id: String) -> Dictionary:
    return documents.get(document_id, {})

func get_payload(document_id: String) -> Dictionary:
    var document: Dictionary = get_document(document_id)
    var payload = document.get("payload", {})
    return payload if payload is Dictionary else {}

func _on_sync_completed(_result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray, request: HTTPRequest) -> void:
    _syncing = false
    request.queue_free()
    if response_code < 200 or response_code >= 300:
        sync_failed.emit("HTTP %s" % response_code)
        return
    var decoded = JSON.parse_string(body.get_string_from_utf8())
    if not decoded is Dictionary:
        sync_failed.emit("invalid JSON")
        return
    var manifest = decoded.get("manifest", {})
    if not manifest is Dictionary:
        sync_failed.emit("manifest missing")
        return
    var next_documents: Dictionary = {}
    for item in manifest.get("documents", []):
        if item is Dictionary and item.has("id"):
            next_documents[String(item["id"])] = item
    documents = next_documents
    revision = int(manifest.get("revision", 0))
    synced.emit(revision)
