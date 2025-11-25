# Implementation Plan: Transcript Versioning & Node Usage Tracking

## Overview
Add version tracking and node usage recording to transcripts. Each generation creates:
- Versioned transcript files: `transcript_v{N}_{YYYY-MM-DD}.txt`
- Generation record: `generation_record_v{N}_{YYYY-MM-DD}.json`
- Updated metadata with version history
- Backward-compatible copies as `transcript.txt`

## User Requirements
- **Versioning**: Hybrid format `v{N}_{YYYY-MM-DD}` (e.g., `v1_2025-01-15`)
- **Node Tracking**: Entity IDs used (format: `Person:Galerius`, `Event:Battle`)
- **Storage**: Keep all version files + version history in metadata.json
- **Separate Record File**: Track generation inputs and nodes used

## Key Design Decisions

### 1. Version Management
Store version counter in `metadata.json`:
```json
{
  "current_version": 3,
  "version_history": [
    {
      "version": 1,
      "version_string": "v1_2025-01-15",
      "generated_at": "2025-01-15T10:30:45Z",
      "provider": "anthropic",
      "language": "English",
      "generation_record": "generation_record_v1_2025-01-15.json"
    }
  ]
}
```

### 2. File Structure
```
content/{city}/{poi}/
  transcript_v1_2025-01-15.txt           # Versioned transcript
  transcript_v1_2025-01-15.ssml          # Versioned SSML
  transcript_v2_2025-01-16.txt           # Next version
  transcript.txt                         # Copy of latest (backward compat)
  generation_record_v1_2025-01-15.json   # Full audit trail
  metadata.json                          # Version history
```

### 3. Node Usage Tracking
**Approach**: Post-generation string matching
- Scan transcript for entity names
- Match against research YAML entity IDs
- Core features always included (all indices)
- Simple, fast, good enough for audit purposes

**Alternative Rejected**: AI-based citations - adds complexity and token usage

### 4. Generation Record Schema
```json
{
  "version": 1,
  "version_string": "v1_2025-01-15",
  "generated_at": "2025-01-15T10:30:45Z",
  "generation_params": {
    "poi_name": "Arch of Galerius",
    "provider": "anthropic",
    "interests": ["drama"],
    "skip_research": false,
    "force_research": false
  },
  "research_source": {
    "path": "poi_research/Thessaloniki/arch_of_galerius.yaml",
    "research_depth": 2,
    "total_entities": 9,
    "api_calls_used": 10
  },
  "nodes_used": {
    "poi": ["arch-of-galerius"],
    "core_features": [0, 1, 2, 3, 4],
    "entities": ["Person:Galerius", "Person:Diocletian"]
  },
  "filtering_applied": {
    "interests": ["drama"],
    "entities_before_filter": 9,
    "entities_after_filter": 5
  },
  "output": {
    "transcript_length": 4345,
    "word_count": 672
  }
}
```

### 5. Migration Strategy
**Approach**: Version-on-regenerate
- Existing POIs keep current files unchanged
- First regeneration creates v1
- Safe, no data modification risk

**Alternative Rejected**: Migrate all to v1 - complex, risky

## Implementation Steps

### Phase 1: Add Utility Functions (src/utils.py)

Add 4 new functions:

```python
def get_next_version(metadata: Dict[str, Any]) -> Tuple[int, str]:
    """Calculate next version number and string"""
    if 'version_history' not in metadata or not metadata['version_history']:
        version = 1
    else:
        version = metadata.get('current_version', 0) + 1

    date_str = datetime.now().strftime('%Y-%m-%d')
    return version, f"v{version}_{date_str}"

def save_versioned_transcript(poi_path: Path, content: str,
                              version_string: str, format: str = "txt"):
    """Save versioned file + current copy for backward compat"""
    # Save versioned
    versioned_path = poi_path / f"transcript_{version_string}.{format}"
    versioned_path.write_text(content, encoding='utf-8')

    # Save current copy
    current_path = poi_path / f"transcript.{format}"
    current_path.write_text(content, encoding='utf-8')

def save_generation_record(poi_path: Path, version_string: str,
                           record_data: Dict[str, Any]):
    """Save generation record JSON"""
    record_path = poi_path / f"generation_record_{version_string}.json"
    with open(record_path, 'w', encoding='utf-8') as f:
        json.dump(record_data, f, indent=2, ensure_ascii=False)

def extract_used_nodes(transcript: str, research_data: Dict) -> Dict[str, List]:
    """Extract which nodes appear in transcript via string matching"""
    used_nodes = {
        'poi': [research_data.get('poi', {}).get('poi_id', 'unknown')],
        'core_features': list(range(len(research_data.get('core_features', [])))),
        'entities': []
    }

    transcript_lower = transcript.lower()
    for entity_id, entity_data in research_data.get('entities', {}).items():
        entity_name = entity_data.get('name', '')
        if entity_name and entity_name.lower() in transcript_lower:
            used_nodes['entities'].append(entity_id)

    return used_nodes
```

### Phase 2: Modify ContentGenerator (src/content_generator.py)

Change `generate()` return signature:
- **Before**: `-> Tuple[str, List[str]]` (transcript, summary_points)
- **After**: `-> Tuple[str, List[str], Dict[str, Any]]` (add generation_metadata)

Add before return (line ~115):
```python
generation_metadata = {
    'research_data': research_data if use_research else None,
    'research_path': str(research_path) if use_research else None,
    'filtered_research': filtered_research if use_research else None,
    'entities_before_filter': len(research_data.get('entities', {})) if research_data else 0,
    'entities_after_filter': len(filtered_research.get('entities', {})) if use_research else 0
}
return (transcript, summary_points, generation_metadata)
```

### Phase 3: Update CLI Generate Command (src/cli.py)

Major changes to generate command (lines 96-194):

1. **Load existing metadata** (after line 104):
```python
existing_metadata = load_metadata(poi_path)
```

2. **Unpack 3-tuple** (line ~142):
```python
transcript, summary_points, generation_metadata = generator.generate(...)
```

3. **Calculate version**:
```python
version_num, version_string = get_next_version(existing_metadata)
```

4. **Extract used nodes**:
```python
used_nodes = extract_used_nodes(transcript, generation_metadata['research_data'])
```

5. **Build generation record**:
```python
generation_record = {
    'version': version_num,
    'version_string': version_string,
    'generated_at': datetime.utcnow().isoformat() + 'Z',
    'generation_params': {...},
    'research_source': {...},
    'nodes_used': used_nodes,
    'filtering_applied': {...},
    'output': {...}
}
```

6. **Save all files**:
```python
save_generation_record(poi_path, version_string, generation_record)
save_versioned_transcript(poi_path, transcript, version_string, format='txt')
save_versioned_transcript(poi_path, ssml_content, version_string, format='ssml')
```

7. **Update metadata**:
```python
version_entry = {
    'version': version_num,
    'version_string': version_string,
    'generated_at': generation_record['generated_at'],
    'provider': provider,
    'language': language,
    'generation_record': f"generation_record_{version_string}.json"
}

metadata = {
    # ... existing fields ...
    'current_version': version_num,
    'version_history': existing_metadata.get('version_history', []) + [version_entry]
}
```

## Critical Files to Modify

1. **src/utils.py** - Add 4 utility functions (~70 lines)
2. **src/content_generator.py** - Change return signature, add metadata (lines 34, 115)
3. **src/cli.py** - Major updates to generate command (lines 96-194, ~100 new lines)

## Testing Strategy

**Unit Tests**:
- `test_get_next_version()` - version numbering
- `test_extract_used_nodes()` - entity matching
- `test_save_versioned_transcript()` - file creation

**Integration Tests**:
1. New POI → creates v1 files
2. Regenerate → increments to v2
3. Verify generation_record structure
4. Check metadata version_history
5. Ensure transcript.txt = latest version

## Risks & Mitigations

**Risk**: Breaking existing code (TTS, display)
**Mitigation**: Keep `transcript.txt` as unversioned copy

**Risk**: Tuple unpacking errors
**Mitigation**: Search codebase for all `generator.generate()` calls

**Risk**: Node extraction false positives
**Mitigation**: Conservative approach acceptable for analytics

## Backward Compatibility

- Existing `transcript.txt` and `transcript.ssml` maintained as copies
- All existing metadata fields preserved
- New fields are additions only
- Existing POIs work until regenerated
- TTS and other tools continue working unchanged
