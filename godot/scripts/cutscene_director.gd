extends Node

signal beat_started(beat_id: String)
signal beat_finished(beat_id: String)
signal cutscene_finished(cutscene_id: String)

var _cancelled := false

func play_cutscene(document: Dictionary) -> void:
    _cancelled = false
    var cutscene_id := str(document.get("id", "unnamed"))
    for beat in document.get("beats", []):
        if _cancelled:
            return
        var beat_id := str(beat.get("id", "beat"))
        beat_started.emit(beat_id)
        await _play_beat(beat)
        beat_finished.emit(beat_id)
    cutscene_finished.emit(cutscene_id)

func cancel() -> void:
    _cancelled = true

func _play_beat(beat: Dictionary) -> void:
    var duration := float(beat.get("duration", 0.0))
    # Avatar animation, camera, dialogue and audio dispatch will be resolved by
    # typed beat adapters. The director remains data-driven and reversible.
    if duration > 0.0:
        await get_tree().create_timer(duration).timeout
