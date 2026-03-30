"""
Background Audio Generation System

Handles asynchronous audio generation for tours without blocking API responses.
Supports progress tracking, error handling, and status reporting.
"""
import json
import logging
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AudioGenerationTask:
    """
    Background task manager for audio generation.

    Creates audio files for tour POIs asynchronously and tracks status.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize audio generation task manager.

        Args:
            config: Application configuration dictionary
        """
        self.config = config
        self.status_dir = Path("audio_status")
        self.status_dir.mkdir(exist_ok=True)
        logger.info(f"Audio status directory: {self.status_dir.absolute()}")

    def start_background_generation(
        self,
        tour_id: str,
        city: str,
        language: str,
        provider: str = 'edge'
    ) -> None:
        """
        Start audio generation in background thread.

        Args:
            tour_id: Unique tour identifier
            city: City name
            language: Language code (e.g., 'zh-tw', 'en')
            provider: TTS provider ('edge', 'openai', 'google', 'qwen')
        """
        # Create initial status file
        status = {
            'tour_id': tour_id,
            'status': 'pending',
            'progress': 0,
            'total_pois': 0,
            'completed_pois': 0,
            'failed_pois': [],
            'error_message': None,
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'provider': provider,
            'language': language,
            'city': city
        }
        self._save_status(tour_id, status)

        # Start background thread
        thread = threading.Thread(
            target=self._generate_audio_sync,
            args=(tour_id, city, language, provider),
            daemon=True,
            name=f"audio-gen-{tour_id}"
        )
        thread.start()

        logger.info(
            f"Started background audio generation for tour {tour_id} "
            f"(city={city}, language={language}, provider={provider})"
        )

    def _generate_audio_sync(
        self,
        tour_id: str,
        city: str,
        language: str,
        provider: str
    ) -> None:
        """
        Synchronous audio generation (runs in background thread).

        Args:
            tour_id: Unique tour identifier
            city: City name
            language: Language code
            provider: TTS provider
        """
        try:
            # Update status to generating
            status = self._load_status(tour_id)
            status['status'] = 'generating'
            self._save_status(tour_id, status)

            # Build command
            cmd = [
                './pocket-guide', 'trip', 'tts',
                tour_id,
                '--city', city,
                '--language', language,
                '--provider', provider
            ]

            logger.info(f"Executing audio generation command: {' '.join(cmd)}")

            # Execute TTS generation via subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes max
                cwd=Path.cwd()
            )

            # Parse output to count POIs
            output_lines = result.stdout.split('\n')
            succeeded_count = 0
            failed_pois = []

            for line in output_lines:
                if 'Succeeded:' in line:
                    try:
                        succeeded_count = int(line.split(':')[1].strip())
                    except (IndexError, ValueError):
                        pass
                elif 'Failed:' in line and 'for:' not in line:
                    # Look for failed POI list
                    idx = output_lines.index(line)
                    for next_line in output_lines[idx+1:]:
                        if next_line.strip().startswith('-'):
                            poi_name = next_line.strip().lstrip('-').split(':')[0].strip()
                            if poi_name:
                                failed_pois.append(poi_name)
                        elif not next_line.strip():
                            break

            # Check result
            if result.returncode == 0:
                # Success
                status = self._load_status(tour_id)
                status['status'] = 'completed'
                status['progress'] = 100
                status['completed_pois'] = succeeded_count
                status['total_pois'] = succeeded_count + len(failed_pois)
                status['failed_pois'] = failed_pois
                status['completed_at'] = datetime.now().isoformat()
                self._save_status(tour_id, status)

                logger.info(
                    f"Audio generation completed for tour {tour_id}: "
                    f"{succeeded_count} succeeded, {len(failed_pois)} failed"
                )
            else:
                # Command failed
                status = self._load_status(tour_id)
                status['status'] = 'failed'
                status['error_message'] = result.stderr[:500] if result.stderr else 'Unknown error'
                status['completed_at'] = datetime.now().isoformat()
                self._save_status(tour_id, status)

                logger.error(
                    f"Audio generation failed for tour {tour_id}: "
                    f"{result.stderr[:200]}"
                )

        except subprocess.TimeoutExpired:
            # Timeout
            status = self._load_status(tour_id)
            status['status'] = 'failed'
            status['error_message'] = 'Audio generation timed out (>10 minutes)'
            status['completed_at'] = datetime.now().isoformat()
            self._save_status(tour_id, status)

            logger.error(f"Audio generation timeout for tour {tour_id}")

        except Exception as e:
            # Unexpected error
            status = self._load_status(tour_id)
            status['status'] = 'failed'
            status['error_message'] = f"Unexpected error: {str(e)}"
            status['completed_at'] = datetime.now().isoformat()
            self._save_status(tour_id, status)

            logger.error(f"Audio generation error for tour {tour_id}: {e}", exc_info=True)

    def get_status(self, tour_id: str) -> Dict[str, Any]:
        """
        Get current audio generation status for a tour.

        Args:
            tour_id: Unique tour identifier

        Returns:
            Status dictionary with progress, errors, etc.
        """
        return self._load_status(tour_id)

    def _save_status(self, tour_id: str, status: Dict[str, Any]) -> None:
        """
        Save status to JSON file.

        Args:
            tour_id: Unique tour identifier
            status: Status dictionary to save
        """
        status_file = self.status_dir / f"{tour_id}_audio.json"
        try:
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save audio status for {tour_id}: {e}")

    def _load_status(self, tour_id: str) -> Dict[str, Any]:
        """
        Load status from JSON file.

        Args:
            tour_id: Unique tour identifier

        Returns:
            Status dictionary, or default 'not_started' status if file doesn't exist
        """
        status_file = self.status_dir / f"{tour_id}_audio.json"

        if not status_file.exists():
            return {
                'tour_id': tour_id,
                'status': 'not_started',
                'progress': 0,
                'total_pois': 0,
                'completed_pois': 0,
                'failed_pois': [],
                'error_message': None,
                'started_at': None,
                'completed_at': None,
                'provider': None,
                'language': None,
                'city': None
            }

        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load audio status for {tour_id}: {e}")
            return {
                'tour_id': tour_id,
                'status': 'error',
                'progress': 0,
                'total_pois': 0,
                'completed_pois': 0,
                'failed_pois': [],
                'error_message': f'Failed to load status: {str(e)}',
                'started_at': None,
                'completed_at': None,
                'provider': None,
                'language': None,
                'city': None
            }
