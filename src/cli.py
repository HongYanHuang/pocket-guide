#!/usr/bin/env python3
"""
Pocket Guide CLI - AI-powered walking tour content generator
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rprint
from pathlib import Path
import sys
from datetime import datetime

from utils import (
    load_config, ensure_poi_directory, save_metadata, save_transcript,
    list_cities, list_pois, text_to_ssml, load_transcript, get_poi_path,
    load_metadata, get_next_version, save_versioned_transcript,
    save_generation_record, extract_used_nodes
)
from content_generator import ContentGenerator
from tts_generator import TTSGenerator
from poi_metadata_agent import POIMetadataAgent

console = Console()


@click.group()
@click.pass_context
def cli(ctx):
    """Pocket Guide - AI Walking Tour Content Generator"""
    try:
        config = load_config()
        ctx.ensure_object(dict)
        ctx.obj['config'] = config
        ctx.obj['content_dir'] = config.get('content_dir', './content')
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def cities(ctx):
    """List all cities"""
    content_dir = ctx.obj['content_dir']
    cities_list = list_cities(content_dir)

    if not cities_list:
        console.print("[yellow]No cities found. Create one with 'generate' command.[/yellow]")
        return

    table = Table(title="Cities")
    table.add_column("City", style="cyan")
    table.add_column("Path", style="dim")

    for city in cities_list:
        table.add_row(city['name'], city['path'])

    console.print(table)


@cli.command()
@click.argument('city')
@click.pass_context
def pois(ctx, city):
    """List all POIs for a city"""
    content_dir = ctx.obj['content_dir']
    pois_list = list_pois(content_dir, city)

    if not pois_list:
        console.print(f"[yellow]No POIs found for {city}. Create one with 'generate' command.[/yellow]")
        return

    table = Table(title=f"POIs in {city}")
    table.add_column("POI", style="cyan")
    table.add_column("Has Content", style="green")
    table.add_column("Has Audio", style="magenta")

    for poi in pois_list:
        poi_path = Path(poi['path'])
        has_content = "✓" if (poi_path / "transcript.txt").exists() else "✗"
        has_audio = "✓" if (poi_path / "audio.mp3").exists() else "✗"
        table.add_row(poi['name'], has_content, has_audio)

    console.print(table)


@cli.command()
@click.option('--city', prompt='City name', help='Name of the city')
@click.option('--poi', prompt='POI name', help='Name of the point of interest')
@click.option('--provider', type=click.Choice(['openai', 'anthropic', 'google']), help='AI provider')
@click.option('--description', help='Description of the POI')
@click.option('--interests', help='Comma-separated interests (e.g., history,architecture)')
@click.option('--custom-prompt', help='Custom prompt for content generation')
@click.option('--language', default='English', help='Content language')
@click.option('--skip-research', is_flag=True, help='Skip research phase (use description only)')
@click.option('--force-research', is_flag=True, help='Force new research even if cached')
@click.pass_context
def generate(ctx, city, poi, provider, description, interests, custom_prompt, language, skip_research, force_research):
    """Generate content for a POI"""
    config = ctx.obj['config']
    content_dir = ctx.obj['content_dir']

    try:
        console.print(f"[dim]Step 1: Creating directory structure...[/dim]")
        # Create POI directory
        poi_path = ensure_poi_directory(content_dir, city, poi)
        console.print(f"[dim]✓ Directory created: {poi_path}[/dim]")

        # Load existing metadata for version tracking
        existing_metadata = load_metadata(poi_path)

        # Parse interests
        interests_list = interests.split(',') if interests else None

        # Interactive prompts if not provided
        if not description and not custom_prompt and not interests_list:
            console.print("\n[cyan]Let's gather some information about this POI:[/cyan]")
            description = Prompt.ask("Brief description (or press Enter to skip)", default="")
            interests_input = Prompt.ask(
                "Focus areas (e.g., history, architecture, food) - comma separated",
                default=""
            )
            interests_list = interests_input.split(',') if interests_input else None

            use_custom = Confirm.ask("Want to provide a custom prompt instead?")
            if use_custom:
                custom_prompt = Prompt.ask("Enter your custom prompt")
                description = None
                interests_list = None

        # Select provider if not specified
        if not provider:
            console.print("\n[cyan]Select AI provider:[/cyan]")
            console.print("1. OpenAI (GPT-4)")
            console.print("2. Anthropic (Claude)")
            console.print("3. Google (Gemini)")
            provider_choice = Prompt.ask("Choose provider", choices=['1', '2', '3'], default='1')
            provider_map = {'1': 'openai', '2': 'anthropic', '3': 'google'}
            provider = provider_map[provider_choice]

        console.print(f"\n[dim]Step 2: Initializing {provider} content generator...[/dim]")
        # Generate content
        generator = ContentGenerator(config)
        console.print(f"[dim]Step 3: Calling {provider} API to generate content...[/dim]")
        console.print(f"[dim]   (This usually takes 10-30 seconds)[/dim]")

        transcript, summary_points, generation_metadata = generator.generate(
            poi_name=poi,
            provider=provider,
            city=city,
            description=description or None,
            interests=[i.strip() for i in interests_list] if interests_list else None,
            custom_prompt=custom_prompt,
            language=language,
            skip_research=skip_research,
            force_research=force_research
        )

        console.print(f"[dim]✓ Content received from API[/dim]")

        console.print(f"[dim]Step 4: Calculating version and saving files...[/dim]")

        # Calculate version number
        version_num, version_string = get_next_version(existing_metadata)

        # Extract used nodes from transcript
        used_nodes = {'poi': [], 'core_features': [], 'entities': []}
        if generation_metadata['research_data']:
            used_nodes = extract_used_nodes(
                transcript,
                generation_metadata['research_data']
            )

        # Build complete generation record
        generation_record = {
            'version': version_num,
            'version_string': version_string,
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'generation_params': {
                'poi_name': poi,
                'city': city,
                'provider': provider,
                'language': language,
                'description': description,
                'interests': interests_list,
                'custom_prompt': custom_prompt,
                'skip_research': skip_research,
                'force_research': force_research
            },
            'research_source': {
                'path': generation_metadata.get('research_path'),
                'research_depth': generation_metadata['research_data'].get('research_depth', 0) if generation_metadata['research_data'] else 0,
                'total_entities': len(generation_metadata['research_data'].get('entities', {})) if generation_metadata['research_data'] else 0,
                'api_calls_used': generation_metadata['research_data'].get('api_calls', 0) if generation_metadata['research_data'] else 0
            } if generation_metadata['research_data'] else None,
            'nodes_used': used_nodes,
            'filtering_applied': {
                'interests': interests_list,
                'entities_before_filter': generation_metadata.get('entities_before_filter', 0),
                'entities_after_filter': generation_metadata.get('entities_after_filter', 0)
            },
            'output': {
                'transcript_length': len(transcript),
                'word_count': len(transcript.split()),
                'summary_points_count': len(summary_points)
            },
            'system_info': {
                'config_version': '1.0',
                'content_generator_version': '1.0',
                'research_agent_version': '1.0'
            }
        }

        # Save generation record
        save_generation_record(poi_path, version_string, generation_record)

        # Save versioned transcripts
        save_versioned_transcript(poi_path, transcript, version_string, format='txt')

        # Convert to SSML and save
        ssml_content = text_to_ssml(transcript)
        save_versioned_transcript(poi_path, ssml_content, version_string, format='ssml')

        # Build version history entry
        version_entry = {
            'version': version_num,
            'version_string': version_string,
            'generated_at': generation_record['generated_at'],
            'provider': provider,
            'language': language,
            'generation_record': f"generation_record_{version_string}.json"
        }

        # Save metadata with version history
        metadata = {
            'city': city,
            'poi': poi,
            'provider': provider,
            'language': language,
            'description': description,
            'interests': interests_list,
            'summary_points': summary_points,
            'current_version': version_num,
            'version_history': existing_metadata.get('version_history', []) + [version_entry]
        }
        save_metadata(poi_path, metadata)

        console.print(f"[dim]✓ Files saved[/dim]")

        # Display result
        console.print(f"\n[green]✓ Content generated successfully! (Version {version_string})[/green]")

        # Display summary points
        console.print("\n[cyan]Summary - What visitors will learn:[/cyan]")
        for i, point in enumerate(summary_points, 1):
            console.print(f"  {i}. {point}")

        # Display transcript
        console.print(Panel(transcript, title=f"{poi} - {city}", border_style="green"))
        console.print(f"\n[dim]Files saved to: {poi_path}[/dim]")

    except Exception as e:
        console.print(f"[red]Error generating content: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
@click.option('--city', prompt='City name', help='Name of the city')
@click.option('--poi', prompt='POI name', help='Name of the point of interest')
@click.option('--provider', type=click.Choice(['openai', 'google', 'edge']), help='TTS provider')
@click.option('--voice', help='Voice name/ID (provider-specific)')
@click.option('--language', help='Language code (e.g., en-US, es-ES)')
@click.pass_context
def tts(ctx, city, poi, provider, voice, language):
    """Generate audio (TTS) from transcript"""
    config = ctx.obj['config']
    content_dir = ctx.obj['content_dir']

    try:
        # Get POI path
        poi_path = get_poi_path(content_dir, city, poi)

        if not poi_path.exists():
            console.print(f"[red]Error: POI '{poi}' not found in city '{city}'[/red]")
            console.print("[yellow]Generate content first using 'generate' command[/yellow]")
            sys.exit(1)

        # Load transcript
        try:
            transcript = load_transcript(poi_path, format='txt')
        except FileNotFoundError:
            console.print("[red]Error: No transcript found for this POI[/red]")
            console.print("[yellow]Generate content first using 'generate' command[/yellow]")
            sys.exit(1)

        # Select provider if not specified
        if not provider:
            console.print("\n[cyan]Select TTS provider:[/cyan]")
            console.print("1. Edge TTS (Free, good quality)")
            console.print("2. OpenAI TTS (Paid, ~$0.015/1000 chars)")
            console.print("3. Google Cloud TTS (Paid, best multilingual)")
            provider_choice = Prompt.ask("Choose provider", choices=['1', '2', '3'], default='1')
            provider_map = {'1': 'edge', '2': 'openai', '3': 'google'}
            provider = provider_map[provider_choice]

        with console.status(f"[bold green]Generating audio with {provider}..."):
            # Generate TTS
            tts_gen = TTSGenerator(config)
            audio_file = tts_gen.generate(
                text=transcript,
                output_path=poi_path,
                provider=provider,
                language=language,
                voice=voice
            )

            console.print(f"\n[green]✓ Audio generated successfully![/green]")
            console.print(f"[dim]Audio file: {audio_file}[/dim]")

    except Exception as e:
        console.print(f"[red]Error generating audio: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@cli.command()
@click.pass_context
def voices(ctx):
    """List available Edge TTS voices (free)"""
    from tts_generator import TTSGenerator

    with console.status("[bold green]Loading available voices..."):
        try:
            voices = TTSGenerator.list_edge_voices()

            # Group by language
            voice_by_lang = {}
            for voice in voices:
                lang = voice['Locale']
                if lang not in voice_by_lang:
                    voice_by_lang[lang] = []
                voice_by_lang[lang].append(voice)

            # Display
            for lang in sorted(voice_by_lang.keys())[:10]:  # Show first 10 languages
                console.print(f"\n[cyan]{lang}[/cyan]")
                for voice in voice_by_lang[lang][:3]:  # Show first 3 voices per language
                    console.print(f"  • {voice['ShortName']} - {voice['Gender']}")

            console.print(f"\n[dim]Showing 10 of {len(voice_by_lang)} languages[/dim]")
            console.print("[dim]Full list: https://github.com/rany2/edge-tts#voice-list[/dim]")

        except Exception as e:
            console.print(f"[red]Error listing voices: {e}[/red]")


@cli.command()
@click.option('--city', required=True, help='City name')
@click.option('--poi', required=True, help='POI name')
@click.pass_context
def info(ctx, city, poi):
    """Show information about a POI"""
    content_dir = ctx.obj['content_dir']
    poi_path = get_poi_path(content_dir, city, poi)

    if not poi_path.exists():
        console.print(f"[red]Error: POI '{poi}' not found in city '{city}'[/red]")
        sys.exit(1)

    from utils import load_metadata

    metadata = load_metadata(poi_path)

    # Extract summary points separately
    summary_points = metadata.pop('summary_points', None)

    table = Table(title=f"{poi} - {city}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    for key, value in metadata.items():
        if key != 'summary_points':  # Already extracted
            table.add_row(key, str(value))

    # Check file existence
    table.add_row("Transcript", "✓" if (poi_path / "transcript.txt").exists() else "✗")
    table.add_row("SSML", "✓" if (poi_path / "transcript.ssml").exists() else "✗")
    table.add_row("Audio", "✓" if (poi_path / "audio.mp3").exists() else "✗")

    console.print(table)

    # Display summary points if available
    if summary_points:
        console.print("\n[cyan]Summary - What visitors will learn:[/cyan]")
        for i, point in enumerate(summary_points, 1):
            console.print(f"  {i}. {point}")


# ==== POI Metadata Commands ====

@cli.group()
def poi_metadata():
    """POI metadata collection and management commands"""
    pass


@poi_metadata.command('collect')
@click.option('--city', required=True, help='City name')
@click.pass_context
def metadata_collect(ctx, city):
    """Collect metadata for all POIs in a city (coordinates, hours, distances)"""
    config = ctx.obj['config']

    # Check if Google Maps API key is configured
    api_key = config.get('poi_metadata', {}).get('google_maps', {}).get('api_key', '')
    if not api_key:
        console.print("[red]Error: Google Maps API key not configured[/red]")
        console.print("[yellow]Please add your Google Maps API key to config.yaml[/yellow]")
        console.print("[dim]Get your key from: https://console.cloud.google.com[/dim]")
        console.print("[dim]Enable: Places API, Geocoding API, and Distance Matrix API[/dim]")
        sys.exit(1)

    try:
        agent = POIMetadataAgent(config)

        console.print(f"\n[cyan]Collecting metadata for {city}...[/cyan]")
        console.print("[dim]This will collect coordinates, hours, and calculate travel distances[/dim]\n")

        with console.status("[bold green]Collecting POI metadata..."):
            result = agent.collect_all_metadata(city)

        # Display results
        console.print(f"\n[green]✓ Metadata collection complete![/green]")
        console.print(f"  • POIs processed: {result.get('pois_total', 0)}")
        console.print(f"  • POIs updated: {result.get('pois_updated', 0)}")

        # Distance matrix results
        dm_result = result.get('distance_matrix', {})
        if dm_result.get('success'):
            console.print(f"  • Distance pairs calculated: {dm_result.get('poi_pairs', 0)}")
        else:
            console.print(f"  [yellow]⚠ Distance matrix: {dm_result.get('error', 'unknown error')}[/yellow]")

        # Show errors if any
        if result.get('errors'):
            console.print(f"\n[yellow]Warnings/Errors:[/yellow]")
            for error in result['errors']:
                console.print(f"  • {error}")

    except Exception as e:
        console.print(f"[red]Error collecting metadata: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@poi_metadata.command('verify')
@click.option('--city', required=True, help='City name')
@click.pass_context
def metadata_verify(ctx, city):
    """Verify metadata completeness for all POIs in a city"""
    config = ctx.obj['config']

    try:
        agent = POIMetadataAgent(config)

        console.print(f"\n[cyan]Verifying metadata for {city}...[/cyan]\n")

        report = agent.verify_metadata(city)

        # Create summary table
        table = Table(title=f"Metadata Status - {city}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total POIs", str(report['total_pois']))
        table.add_row("Complete", f"[green]{report['complete']}[/green]")
        table.add_row("Incomplete", f"[yellow]{report['incomplete']}[/yellow]")

        console.print(table)

        # Show missing fields summary
        if report['missing_fields']:
            console.print("\n[yellow]Missing fields:[/yellow]")
            for field, count in report['missing_fields'].items():
                console.print(f"  • {field}: {count} POIs")

        # Show POI details
        console.print("\n[cyan]POI Details:[/cyan]")
        for poi_info in report['pois']:
            status = "[green]✓[/green]" if not poi_info['missing_fields'] else "[yellow]⚠[/yellow]"
            console.print(f"{status} {poi_info['poi_name']}")
            if poi_info['missing_fields']:
                console.print(f"   Missing: {', '.join(poi_info['missing_fields'])}")

    except Exception as e:
        console.print(f"[red]Error verifying metadata: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@poi_metadata.command('show')
@click.option('--city', required=True, help='City name')
@click.option('--poi-id', help='POI ID to show (optional, shows all if not specified)')
@click.pass_context
def metadata_show(ctx, city, poi_id):
    """Show metadata for POI(s) in a city"""
    config = ctx.obj['config']

    try:
        agent = POIMetadataAgent(config)

        result = agent.show_metadata(city, poi_id)

        if 'error' in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            sys.exit(1)

        if poi_id:
            # Show single POI details
            console.print(f"\n[cyan]{result['poi_name']}[/cyan]")
            console.print(f"[dim]ID: {result['poi_id']}[/dim]\n")

            metadata = result.get('metadata', {})

            if not metadata:
                console.print("[yellow]No metadata available[/yellow]")
                return

            # Coordinates
            coords = metadata.get('coordinates', {})
            if coords:
                console.print(f"[green]Coordinates:[/green]")
                console.print(f"  Lat: {coords.get('latitude')}")
                console.print(f"  Lng: {coords.get('longitude')}")
                console.print(f"  Source: {coords.get('source')}")

            # Hours
            hours = metadata.get('operation_hours', {})
            if hours:
                console.print(f"\n[green]Hours:[/green]")
                if 'weekday_text' in hours:
                    for day in hours['weekday_text']:
                        console.print(f"  {day}")
                elif 'open_now' in hours:
                    status = "Open now" if hours['open_now'] else "Closed now"
                    console.print(f"  {status}")

            # Visit info
            visit_info = metadata.get('visit_info', {})
            if visit_info:
                console.print(f"\n[green]Visit Info:[/green]")
                console.print(f"  Indoor/Outdoor: {visit_info.get('indoor_outdoor', 'unknown')}")
                console.print(f"  Typical duration: {visit_info.get('typical_duration_minutes', 'unknown')} min")

        else:
            # Show all POIs summary
            table = Table(title=f"POIs in {city}")
            table.add_column("POI ID", style="cyan")
            table.add_column("POI Name", style="white")
            table.add_column("Has Metadata", style="green")
            table.add_column("Has Coords", style="yellow")

            for poi in result['pois']:
                has_meta = "✓" if poi['has_metadata'] else "✗"
                has_coords = "✓" if poi['has_coordinates'] else "✗"
                table.add_row(
                    poi['poi_id'],
                    poi['poi_name'],
                    has_meta,
                    has_coords
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error showing metadata: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@poi_metadata.command('distances')
@click.option('--city', required=True, help='City name')
@click.option('--mode', type=click.Choice(['walking', 'transit', 'driving']), default='walking', help='Transportation mode')
@click.pass_context
def metadata_distances(ctx, city, mode):
    """Show distance matrix for a city"""
    config = ctx.obj['config']

    try:
        agent = POIMetadataAgent(config)

        distance_matrix = agent.load_distance_matrix(city)

        if not distance_matrix:
            console.print(f"[yellow]No distance matrix found for {city}[/yellow]")
            console.print("[dim]Run 'poi-metadata collect --city {city}' first[/dim]")
            sys.exit(1)

        console.print(f"\n[cyan]Distance Matrix - {city} ({mode})[/cyan]")
        console.print(f"[dim]Generated: {distance_matrix.get('generated_at')}[/dim]\n")

        # Create table
        table = Table(title=f"{mode.capitalize()} Distances")
        table.add_column("From", style="cyan")
        table.add_column("To", style="cyan")
        table.add_column("Duration", style="yellow")
        table.add_column("Distance", style="white")

        for pair_key, pair_data in distance_matrix.get('poi_pairs', {}).items():
            if mode not in pair_data:
                continue

            mode_data = pair_data[mode]

            table.add_row(
                pair_data['origin_poi_name'][:30],
                pair_data['destination_poi_name'][:30],
                mode_data.get('duration_text', 'N/A'),
                mode_data.get('distance_text', 'N/A')
            )

        console.print(table)

        # Summary
        total_pairs = len(distance_matrix.get('poi_pairs', {}))
        console.print(f"\n[dim]Total POI pairs: {total_pairs}[/dim]")

    except Exception as e:
        console.print(f"[red]Error showing distances: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == '__main__':
    cli(obj={})
