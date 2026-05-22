extends RefCounted
class_name HarboursChunkManifestLoader

const MANIFEST_PATH := "res://data/maps/chunk_manifest.json"


static func manifest_available() -> bool:
	return FileAccess.file_exists(MANIFEST_PATH)


static func load_document() -> Dictionary:
	if not manifest_available():
		return {}
	var text := FileAccess.get_file_as_string(MANIFEST_PATH)
	if text.is_empty():
		return {}
	var parsed = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("chunk_manifest.json: expected object root")
		return {}
	return parsed


static func load_chunks(doc: Dictionary) -> Array:
	var raw = doc.get("chunks", [])
	if typeof(raw) != TYPE_ARRAY:
		return []
	return raw
