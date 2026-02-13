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
    save_generation_record, extract_used_nodes, normalize_language_code,
    list_available_languages, get_language_name
)
from content_generator import ContentGenerator
from tts_generator import TTSGenerator
from poi_metadata_agent import POIMetadataAgent
from poi_research_agent import POIResearchAgent
from trip_planner import POISelectorAgent, ItineraryOptimizerAgent, TourManager

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
@click.option('--language', default='en', help='Content language (ISO 639-1 code with optional region, e.g., en, zh-tw, pt-br)')
@click.option('--skip-research', is_flag=True, help='Skip research phase (use description only)')
@click.option('--force-research', is_flag=True, help='Force new research even if cached')
@click.option('--verify', is_flag=True, help='Enable transcript verification (increases cost, default: disabled)')
@click.pass_context
def generate(ctx, city, poi, provider, description, interests, custom_prompt, language, skip_research, force_research, verify):
    """Generate content for a POI"""
    config = ctx.obj['config']
    content_dir = ctx.obj['content_dir']

    try:
        # Validate and normalize language code
        try:
            language = normalize_language_code(language)
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

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

        # Pass language code directly - generator will convert it internally
        transcript, summary_points, generation_metadata = generator.generate(
            poi_name=poi,
            provider=provider,
            city=city,
            description=description or None,
            interests=[i.strip() for i in interests_list] if interests_list else None,
            custom_prompt=custom_prompt,
            language=language,
            skip_research=skip_research,
            force_research=force_research,
            verify=verify
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

        # Save versioned transcripts with language support
        save_versioned_transcript(poi_path, transcript, version_string, format='txt', language=language)

        # Convert to SSML and save
        ssml_content = text_to_ssml(transcript, language=f"{language}-US" if language == "en" else language)
        save_versioned_transcript(poi_path, ssml_content, version_string, format='ssml', language=language)

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


# ==== POI Research and Batch Generation Commands ====

@cli.group()
def poi():
    """POI research and batch generation commands"""
    pass


@poi.command('research')
@click.argument('city')
@click.option('--count', default=10, help='Number of POIs to research')
@click.option('--provider', type=click.Choice(['openai', 'anthropic', 'google']), help='AI provider')
@click.pass_context
def poi_research(ctx, city, count, provider):
    """Research and suggest top N POIs for a city using AI"""
    config = ctx.obj['config']

    # Select provider
    if not provider:
        provider = config.get('defaults', {}).get('ai_provider', 'anthropic')

    # Warn about large counts
    if count > 30:
        console.print(f"\n[yellow]⚠️  Warning: Requesting {count} POIs may cause timeouts![/yellow]")
        console.print(f"[yellow]   Recommended: Use --count 30 or less for best results[/yellow]")
        console.print(f"[yellow]   Large counts (>30) may take 90+ seconds and could timeout[/yellow]\n")

    console.print(f"[cyan]Researching top {count} POIs in {city}...[/cyan]")
    console.print(f"[dim]Using {provider} for AI research[/dim]")
    console.print(f"[yellow]⏳ Note: Large requests may take 30-120 seconds. Please wait...[/yellow]\n")

    try:
        # Initialize agent
        agent = POIResearchAgent(config, provider=provider)

        # Research POIs
        console.print(f"[dim]Sending request to {provider}... (waiting for response)[/dim]")
        candidates = agent.research_city_pois(city, count, provider)

        # Save to JSON
        output_path = agent._save_research_candidates(city, candidates)

        # Display table
        table = Table(title=f"POI Research Results - {city}")
        table.add_column("POI ID", style="cyan", width=20)
        table.add_column("Name", style="white", width=30)
        table.add_column("Category", style="yellow", width=15)
        table.add_column("Period", style="magenta", width=25)

        for poi in candidates:
            table.add_row(
                poi['poi_id'][:20],
                poi['name'][:30],
                poi['category'],
                poi.get('historical_period', 'N/A')[:25]
            )

        console.print(table)

        # Summary
        console.print(f"\n[green]✓ Research complete! Found {len(candidates)} POIs[/green]")
        console.print(f"[dim]Saved to: {output_path}[/dim]")

        # Next steps
        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"[dim]1. Review and edit: {output_path}[/dim]")
        console.print(f"[dim]2. Check for duplicates: pocket-guide poi check-redundancy {city}[/dim]")

    except Exception as e:
        console.print(f"[red]Error researching POIs: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@poi.command('fulfill')
@click.argument('city')
@click.option('--count', default=10, help='Number of additional POIs to discover')
@click.option('--provider', type=click.Choice(['openai', 'anthropic', 'google']), help='AI provider')
@click.pass_context
def poi_fulfill(ctx, city, count, provider):
    """Discover additional POIs for a city that were missed in the first research stage"""
    config = ctx.obj['config']

    if not provider:
        provider = config.get('defaults', {}).get('ai_provider', 'anthropic')

    if count > 30:
        console.print(f"\n[yellow]⚠️  Warning: Requesting {count} POIs may cause timeouts![/yellow]")
        console.print(f"[yellow]   Recommended: Use --count 30 or less for best results[/yellow]\n")

    console.print(f"[cyan]Fulfilling POIs for {city} (looking for {count} additional)...[/cyan]")
    console.print(f"[dim]Using {provider} for AI research[/dim]")
    console.print(f"[yellow]⏳ Note: This may take 30-120 seconds. Please wait...[/yellow]\n")

    try:
        agent = POIResearchAgent(config, provider=provider)

        console.print(f"[dim]Loading existing POIs...[/dim]")
        candidates = agent.fulfill_city_pois(city, count, provider)

        if not candidates:
            console.print(f"\n[yellow]No new POIs found. The existing set may already be comprehensive.[/yellow]")
            return

        # Display results table
        table = Table(title=f"New POI Candidates - {city} (Fulfill Stage)")
        table.add_column("POI ID", style="cyan", width=25)
        table.add_column("Name", style="white", width=30)
        table.add_column("Category", style="yellow", width=18)
        table.add_column("Period", style="magenta", width=25)

        for poi in candidates:
            table.add_row(
                poi['poi_id'][:25],
                poi['name'][:30],
                poi['category'],
                poi.get('historical_period', 'N/A')[:25]
            )

        console.print(table)

        # Summary
        console.print(f"\n[green]✓ Fulfill research complete! Found {len(candidates)} new POIs[/green]")

        # Next steps
        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"[dim]1. Check for duplicates: pocket-guide poi check-redundancy {city}[/dim]")
        console.print(f"[dim]2. Create text file with POI names to generate[/dim]")
        console.print(f"[dim]3. Run: pocket-guide poi batch-generate <file> --city {city}[/dim]")

    except Exception as e:
        console.print(f"[red]Error fulfilling POIs: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@poi.command('check-redundancy')
@click.argument('city')
@click.option('--provider', type=click.Choice(['openai', 'anthropic', 'google']), help='AI provider')
@click.pass_context
def poi_check_redundancy(ctx, city, provider):
    """Check research candidates for duplicates against existing POIs"""
    config = ctx.obj['config']

    if not provider:
        provider = config.get('defaults', {}).get('ai_provider', 'anthropic')

    # Check if research_candidates.json exists
    project_root = Path(__file__).parent.parent
    candidates_path = project_root / 'poi_research' / city / 'research_candidates.json'

    if not candidates_path.exists():
        console.print(f"[red]Error: No research_candidates.json found for {city}[/red]")
        console.print(f"[yellow]Run 'pocket-guide poi research {city}' first[/yellow]")
        sys.exit(1)

    console.print(f"\n[cyan]Checking for duplicates in {city}...[/cyan]")
    console.print(f"[dim]Using {provider} for semantic comparison[/dim]\n")

    try:
        agent = POIResearchAgent(config, provider=provider)

        # Run redundancy check
        with console.status(f"[bold green]Analyzing with {provider}..."):
            result = agent.check_redundancy(city, provider)

        # Display summary
        console.print(f"\n[green]✓ Redundancy check complete![/green]")
        console.print(f"  • Total candidates: {result['total_candidates']}")
        console.print(f"  • Duplicates found: {result['duplicates_found']}")
        console.print(f"  • Unique POIs: {result['unique_pois']}")

        # Display duplicates table if any
        if result['duplicates']:
            console.print()
            table = Table(title="Duplicates Found")
            table.add_column("Candidate", style="yellow", width=30)
            table.add_column("Duplicate Of", style="red", width=30)
            table.add_column("Confidence", style="cyan", width=10)
            table.add_column("Reason", style="dim", width=50)

            for dup in result['duplicates']:
                table.add_row(
                    dup['candidate_name'][:30],
                    dup['duplicate_of'][:30] if dup['duplicate_of'] else 'N/A',
                    dup['confidence'],
                    dup['reason'][:50]
                )

            console.print(table)

        # Show update message
        console.print(f"\n[dim]Updated: {candidates_path}[/dim]")

        # Next steps
        if result['unique_pois'] > 0:
            console.print(f"\n[bold]Next steps:[/bold]")
            console.print(f"[dim]1. Review updated candidates file[/dim]")
            console.print(f"[dim]2. Create text file with POI names to generate[/dim]")
            console.print(f"[dim]3. Run: pocket-guide poi batch-generate <file> --city {city}[/dim]")
        else:
            console.print(f"\n[yellow]All candidates are duplicates. No new POIs to generate.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error checking redundancy: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@poi.command('batch-generate')
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--city', help='City name (required if not in research_candidates.json)')
@click.option('--provider', type=click.Choice(['openai', 'anthropic', 'google']), help='AI provider')
@click.option('--language', default='en', help='Content language (ISO 639-1 code with optional region, e.g., en, zh-tw, pt-br)')
@click.option('--skip-research', is_flag=True, help='Skip research phase for faster generation')
@click.option('--force', is_flag=True, help='Force regeneration even if content already exists')
@click.option('--verify', is_flag=True, help='Enable transcript verification (increases cost, default: disabled)')
@click.pass_context
def poi_batch_generate(ctx, input_file, city, provider, language, skip_research, force, verify):
    """Batch generate POI content from input file (one POI name per line)"""
    config = ctx.obj['config']
    content_dir = ctx.obj['content_dir']

    # Validate and normalize language code
    try:
        language = normalize_language_code(language)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    if not provider:
        provider = config.get('defaults', {}).get('ai_provider', 'anthropic')

    # Load POI names from file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            poi_names = [line.strip() for line in f if line.strip()]
    except Exception as e:
        console.print(f"[red]Error reading input file: {e}[/red]")
        sys.exit(1)

    if not poi_names:
        console.print(f"[yellow]No POI names found in {input_file}[/yellow]")
        sys.exit(1)

    # Try to extract city from research_candidates.json if not provided
    if not city:
        input_path = Path(input_file)
        if input_path.parent.name and input_path.parent.parent.name == 'poi_research':
            city = input_path.parent.name
        else:
            console.print("[red]Error: --city parameter required[/red]")
            console.print("[dim]Usage: pocket-guide poi batch-generate <file> --city <city>[/dim]")
            sys.exit(1)

    # Load research_candidates.json to check skip flags
    try:
        agent = POIResearchAgent(config)
        candidates = agent._load_research_candidates(city)
        skip_map = {c['poi_id']: c.get('skip', False) for c in candidates}
    except FileNotFoundError:
        console.print(f"[yellow]Warning: No research_candidates.json found for {city}[/yellow]")
        console.print(f"[dim]Proceeding without skip checking[/dim]")
        skip_map = {}

    # Filter out skipped POIs
    to_generate = []
    skipped = []

    for name in poi_names:
        poi_id = name.lower().replace(' ', '-').replace('_', '-')
        if skip_map.get(poi_id, False):
            skipped.append(name)
        else:
            to_generate.append(name)

    console.print(f"\n[cyan]Batch generating POIs for {city}[/cyan]")
    force_msg = " | Force: enabled" if force else ""
    console.print(f"[dim]Provider: {provider} | Total: {len(poi_names)} | To generate: {len(to_generate)} | Skipped: {len(skipped)}{force_msg}[/dim]\n")

    if skipped:
        console.print(f"[yellow]Skipping {len(skipped)} POIs marked as duplicates:[/yellow]")
        for s in skipped:
            console.print(f"  • {s}")
        console.print()

    if not to_generate:
        console.print("[yellow]No POIs to generate (all marked as duplicates)[/yellow]")
        sys.exit(0)

    # Check if Google Maps API is configured for distance calculation
    google_maps_configured = bool(config.get('poi_metadata', {}).get('google_maps', {}).get('api_key'))
    if google_maps_configured:
        console.print("[dim]Google Maps API configured - will calculate distances for new POIs[/dim]")
        metadata_agent = POIMetadataAgent(config)
    else:
        console.print("[yellow]⚠ Google Maps API not configured - distances will not be calculated[/yellow]")
        console.print("[dim]To enable: Add Google Maps API key to config.yaml[/dim]")
        metadata_agent = None

    # Progress tracking
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

    succeeded = []
    failed = []
    already_exists = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Generating POIs...", total=len(to_generate))

        for poi_name in to_generate:
            progress.update(task, description=f"[cyan]Checking: {poi_name}")

            try:
                # Check if POI content already exists for this language (unless --force is set)
                poi_path = get_poi_path(content_dir, city, poi_name)

                # Check for language-specific transcript
                transcript_file = poi_path / f'transcript_{language}.txt'
                # Fallback to backward-compatible filename for English
                if not transcript_file.exists() and language == "en":
                    transcript_file = poi_path / 'transcript.txt'

                if transcript_file.exists() and not force:
                    # Skip POIs that already have generated content for this language
                    progress.console.print(f"[dim]⊘ {poi_name} (already exists for {language}, use --force to regenerate)[/dim]")
                    already_exists.append(poi_name)
                    progress.advance(task)
                    continue

                # Generate new content
                progress.update(task, description=f"[cyan]Generating: {poi_name}")

                # Pass language code directly - generator will convert it internally
                # Call existing generate logic
                generator = ContentGenerator(config)
                transcript, summary_points, metadata = generator.generate(
                    poi_name=poi_name,
                    city=city,
                    provider=provider,
                    language=language,
                    skip_research=skip_research,
                    verify=verify
                )

                # Save files
                poi_path = ensure_poi_directory(content_dir, city, poi_name)

                # Load existing metadata to calculate version
                existing_metadata = load_metadata(poi_path)
                version_num, version_string = get_next_version(existing_metadata)

                # Update metadata with version info
                if 'version_history' not in existing_metadata:
                    existing_metadata['version_history'] = []
                existing_metadata['current_version'] = version_num

                # Merge with new metadata
                existing_metadata.update(metadata)

                # Save updated metadata
                save_transcript(poi_path, transcript, format='txt', language=language)
                save_metadata(poi_path, existing_metadata)

                # Save generation record
                generation_record = {
                    'version': version_num,
                    'version_string': version_string,
                    'generated_at': datetime.utcnow().isoformat() + 'Z',
                    'poi_name': poi_name,
                    'city': city,
                    'provider': provider,
                    'metadata': metadata,
                    'summary_points_count': len(summary_points)
                }
                save_generation_record(poi_path, version_string, generation_record)

                # Save summary
                summary_path = poi_path / 'summary.txt'
                with open(summary_path, 'w', encoding='utf-8') as f:
                    for i, point in enumerate(summary_points, 1):
                        f.write(f"{i}. {point}\n")

                # Calculate distances for new POI if Google Maps configured
                if metadata_agent:
                    try:
                        progress.update(task, description=f"[cyan]Collecting coordinates: {poi_name}")

                        # First, collect coordinates for the new POI if not already present
                        if 'coordinates' not in existing_metadata or not existing_metadata['coordinates']:
                            # Collect coordinates using metadata agent
                            coords = metadata_agent.google_maps.get_place_details(poi_name, city)
                            if coords and coords.get('coordinates'):
                                existing_metadata['coordinates'] = coords['coordinates']
                                # Save updated metadata with coordinates
                                save_metadata(poi_path, existing_metadata)
                                progress.console.print(f"[dim]  → Coordinates collected[/dim]")

                        # Now calculate distances if we have coordinates
                        if existing_metadata.get('coordinates'):
                            progress.update(task, description=f"[cyan]Calculating distances: {poi_name}")

                            # Prepare POI dict with metadata including coordinates
                            poi_id = poi_name.lower().replace(' ', '-').replace('(', '').replace(')', '')
                            new_poi = {
                                'poi_id': poi_id,
                                'poi_name': poi_name,
                                'metadata': existing_metadata
                            }

                            # Calculate incremental distances
                            metadata_agent.calculate_incremental_distances(new_poi, city)
                            progress.console.print(f"[dim]  → Distances calculated[/dim]")
                        else:
                            progress.console.print(f"[yellow]  ⚠ Could not get coordinates for {poi_name}[/yellow]")

                    except Exception as e:
                        # Don't fail the entire generation if distance calculation fails
                        progress.console.print(f"[yellow]  ⚠ Distance calculation failed: {str(e)[:100]}[/yellow]")

                progress.console.print(f"[green]✓ {poi_name}[/green]")
                succeeded.append(poi_name)

            except Exception as e:
                progress.console.print(f"[red]✗ {poi_name}: {str(e)[:100]}[/red]")
                failed.append((poi_name, str(e)))

            progress.advance(task)

    # Summary
    console.print(f"\n[bold]Batch Generation Summary:[/bold]")
    console.print(f"[green]✓ Succeeded: {len(succeeded)}[/green]")
    if already_exists:
        console.print(f"[dim]⊘ Already exists: {len(already_exists)} (skipped)[/dim]")
    if failed:
        console.print(f"[red]✗ Failed: {len(failed)}[/red]")
        console.print(f"\n[yellow]Failed POIs:[/yellow]")
        for poi_name, error in failed:
            console.print(f"  • {poi_name}: {error[:100]}")

    if succeeded:
        console.print(f"\n[dim]Generated content saved to: {content_dir}/{city}/[/dim]")


@cli.group()
def trip():
    """Trip planning commands"""
    pass


def ensure_poi_transcripts(
    pois: list,
    city: str,
    language: str,
    content_dir: str,
    config: dict,
    provider: str
) -> dict:
    """
    Ensure all POI transcripts exist in the target language.
    Generate missing transcripts automatically.

    Args:
        pois: List of POI names
        city: City name
        language: Target language code (e.g., 'zh-tw')
        content_dir: Content directory path
        config: Application config
        provider: AI provider for generation

    Returns:
        Dict mapping POI name to generation status (True if generated, False if existed)
    """
    generator = ContentGenerator(config)
    generation_status = {}

    console.print(f"\n[cyan]Checking POI transcripts for language: {language}[/cyan]")

    for poi in pois:
        poi_path = get_poi_path(content_dir, city, poi)

        # Check if transcript exists
        available_langs = []
        if poi_path.exists():
            available_langs = list_available_languages(poi_path)

        if language in available_langs:
            console.print(f"  ✓ {poi} - transcript exists")
            generation_status[poi] = False
            continue

        # Generate missing transcript
        console.print(f"  ⚡ {poi} - generating transcript in {language}...")

        try:
            # Ensure POI directory exists
            poi_path = ensure_poi_directory(content_dir, city, poi)

            # Load existing metadata for versioning
            existing_metadata = load_metadata(poi_path)

            # Generate transcript
            transcript, summary_points, gen_metadata = generator.generate(
                poi_name=poi,
                city=city,
                provider=provider,
                language=language,
                skip_research=False,  # Use research for quality
                verify=False  # Skip verification to reduce cost during tour generation
            )

            # Calculate version
            version_num, version_string = get_next_version(existing_metadata)

            # Save transcript (both txt and ssml)
            save_versioned_transcript(poi_path, transcript, version_string, 'txt', language)

            # Convert to SSML if needed (simple wrapper)
            ssml_content = text_to_ssml(transcript, language)
            save_versioned_transcript(poi_path, ssml_content, version_string, 'ssml', language)

            # Update metadata with new version
            existing_metadata['current_version'] = version_num
            if 'version_history' not in existing_metadata:
                existing_metadata['version_history'] = []

            version_entry = {
                'version': version_num,
                'version_string': version_string,
                'timestamp': datetime.now().isoformat(),
                'language': language,
                'provider': provider
            }
            existing_metadata['version_history'].append(version_entry)
            save_metadata(poi_path, existing_metadata)

            console.print(f"    ✓ Generated successfully")
            generation_status[poi] = True

        except Exception as e:
            console.print(f"    ✗ Failed: {e}")
            raise Exception(f"Could not generate transcript for {poi}: {e}")

    return generation_status


@trip.command('plan')
@click.option('--city', required=True, help='City name (e.g., Rome, Athens)')
@click.option('--days', type=int, required=True, help='Number of days for the trip')
@click.option('--interests', multiple=True, help='Interests (can specify multiple: --interests history --interests architecture)')
@click.option('--provider', type=click.Choice(['openai', 'anthropic', 'google']), default='anthropic', help='AI provider for POI selection')
@click.option('--must-see', multiple=True, help='POIs that must be included (can specify multiple)')
@click.option('--pace', type=click.Choice(['relaxed', 'normal', 'packed']), default='normal', help='Trip pace')
@click.option('--walking', type=click.Choice(['low', 'moderate', 'high']), default='moderate', help='Walking tolerance')
@click.option('--language', default='en', help='Tour language (ISO 639-1 code, e.g., en, zh-tw, pt-br)')
@click.option('--mode', type=click.Choice(['simple', 'ilp']), default='simple', help='Optimization mode: simple (greedy+2-opt, fast) or ilp (optimal, slower)')
@click.option('--start-location', help='Starting point (POI name or "lat,lng" coordinates)')
@click.option('--end-location', help='Ending point (POI name or "lat,lng" coordinates)')
@click.option('--start-date', help='Trip start date (YYYY-MM-DD format, e.g., 2026-03-15). Used to check opening hours.')
@click.option('--save', is_flag=True, help='Save the generated tour')
@click.pass_context
def trip_plan(ctx, city, days, interests, provider, must_see, pace, walking, language, mode, start_location, end_location, start_date, save):
    """
    Generate an optimized trip itinerary for a city.

    Example:
        ./pocket-guide trip plan --city Rome --days 3 --interests history --interests architecture --pace normal
    """
    config = ctx.obj['config']

    try:
        # Validate and normalize language
        language = normalize_language_code(language)
        language_name = get_language_name(language)

        console.print(f"\n[cyan]Planning {days}-day trip to {city}...[/cyan]\n")

        # Convert interests tuple to list
        interests_list = list(interests) if interests else []
        must_see_list = list(must_see) if must_see else []

        # Build preferences dict
        preferences = {
            'pace': pace,
            'walking_tolerance': walking,
            'indoor_outdoor': 'balanced'
        }

        console.print(f"[dim]Interests: {', '.join(interests_list) if interests_list else 'General tourism'}[/dim]")
        console.print(f"[dim]Pace: {pace} | Walking: {walking} | Language: {language_name}[/dim]")
        console.print(f"[dim]Optimization mode: {mode}[/dim]")
        if must_see_list:
            console.print(f"[dim]Must-see: {', '.join(must_see_list)}[/dim]")
        if start_location:
            console.print(f"[dim]Start location: {start_location}[/dim]")
        if end_location:
            console.print(f"[dim]End location: {end_location}[/dim]")
        console.print()

        # Step 1: POI Selection
        console.print("[bold cyan]Step 1: Selecting POIs...[/bold cyan]")
        selector = POISelectorAgent(config, provider=provider)

        selection_result = selector.select_pois(
            city=city,
            duration_days=days,
            interests=interests_list,
            preferences=preferences,
            must_see=must_see_list,
            avoid=[],
            language=language
        )

        starting_pois = selection_result.get('starting_pois', [])
        backup_pois = selection_result.get('backup_pois', {})
        rejected_pois = selection_result.get('rejected_pois', [])

        console.print(f"[green]✓ Selected {len(starting_pois)} POIs for itinerary[/green]")
        console.print(f"[dim]  + {len(backup_pois)} backup POIs available[/dim]")
        console.print(f"[dim]  + {len(rejected_pois)} POIs rejected[/dim]\n")

        # Display selected POIs
        table = Table(title="Selected POIs")
        table.add_column("POI", style="cyan")
        table.add_column("Reason", style="dim")

        for poi_info in starting_pois:
            poi_name = poi_info.get('poi', 'Unknown')
            reason = poi_info.get('selection_reason', 'N/A')
            table.add_row(poi_name, reason[:60] + '...' if len(reason) > 60 else reason)

        console.print(table)
        console.print()

        # Parse start/end locations
        def parse_location(location_str):
            """Parse location string as either POI name or lat,lng coordinates"""
            if not location_str:
                return None

            # Check if it's coordinates (lat,lng format)
            if ',' in location_str:
                try:
                    parts = location_str.split(',')
                    lat = float(parts[0].strip())
                    lng = float(parts[1].strip())
                    return {
                        'name': location_str,
                        'coordinates': {'latitude': lat, 'longitude': lng}
                    }
                except:
                    pass

            # Treat as POI name - try to find in starting_pois
            for poi in starting_pois:
                if poi['poi'].lower() == location_str.lower():
                    return {
                        'name': poi['poi'],
                        'coordinates': poi.get('coordinates', {})
                    }

            # If not found, just use the name
            return {'name': location_str, 'coordinates': {}}

        parsed_start = parse_location(start_location)
        parsed_end = parse_location(end_location)

        # Parse start date if provided
        trip_start_date = None
        if start_date:
            try:
                trip_start_date = datetime.strptime(start_date, '%Y-%m-%d')
                console.print(f"[dim]Trip start date: {trip_start_date.strftime('%A, %B %d, %Y')}[/dim]")
            except ValueError:
                console.print(f"[yellow]Warning: Invalid date format '{start_date}'. Expected YYYY-MM-DD. Using current date.[/yellow]")
                trip_start_date = datetime.now()
        else:
            # Default to current date for opening hours checking
            trip_start_date = datetime.now()

        # Step 2: Itinerary Optimization
        console.print("[bold cyan]Step 2: Optimizing itinerary...[/bold cyan]")
        optimizer = ItineraryOptimizerAgent(config)

        optimized_result = optimizer.optimize_itinerary(
            selected_pois=starting_pois,
            city=city,
            duration_days=days,
            start_time="09:00",
            preferences=preferences,
            mode=mode,
            start_location=parsed_start,
            end_location=parsed_end,
            trip_start_date=trip_start_date
        )

        itinerary = optimized_result.get('itinerary', [])
        scores = optimized_result.get('optimization_scores', {})
        solver_stats = optimized_result.get('solver_stats', None)

        console.print(f"[green]✓ Itinerary optimized[/green]")
        console.print(f"[dim]  Distance score: {scores.get('distance_score', 0):.2f}[/dim]")
        console.print(f"[dim]  Coherence score: {scores.get('coherence_score', 0):.2f}[/dim]")
        console.print(f"[dim]  Overall score: {scores.get('overall_score', 0):.2f}[/dim]")
        if solver_stats:
            console.print(f"[dim]  Solver: {solver_stats.get('status', 'N/A')} in {solver_stats.get('solve_time', 0)}s[/dim]")
        console.print()

        # Display itinerary
        for day_plan in itinerary:
            day_num = day_plan.get('day', 0)
            day_pois = day_plan.get('pois', [])
            total_hours = day_plan.get('total_hours', 0)
            total_km = day_plan.get('total_walking_km', 0)

            console.print(f"[bold yellow]Day {day_num}[/bold yellow] ({total_hours:.1f}h total, {total_km:.1f}km walking)")

            for i, poi_entry in enumerate(day_pois, 1):
                poi_name = poi_entry.get('poi', 'Unknown')
                # Use estimated_hours from POI metadata (both simple and ILP modes)
                visit_time = poi_entry.get('estimated_hours', 2.0)

                # Calculate walking time from previous POI
                walking_minutes = 0
                if i > 1:
                    # Calculate distance to previous POI
                    prev_poi = day_pois[i - 2]
                    prev_coords = prev_poi.get('coordinates', {})
                    curr_coords = poi_entry.get('coordinates', {})

                    if prev_coords.get('latitude') and curr_coords.get('latitude'):
                        # Simple Haversine distance
                        from math import radians, sin, cos, sqrt, asin
                        lat1, lon1 = radians(prev_coords['latitude']), radians(prev_coords['longitude'])
                        lat2, lon2 = radians(curr_coords['latitude']), radians(curr_coords['longitude'])
                        dlat, dlon = lat2 - lat1, lon2 - lon1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        distance_km = 2 * 6371 * asin(sqrt(a))

                        # Convert to walking minutes (4 km/h average walking speed)
                        walking_minutes = (distance_km / 4.0) * 60

                if i == 1:
                    console.print(f"  {i}. [cyan]{poi_name}[/cyan] ({visit_time:.1f}h)")
                else:
                    console.print(f"  {i}. [cyan]{poi_name}[/cyan] ({visit_time:.1f}h) [dim]← {walking_minutes:.0f}min walk[/dim]")

            console.print()

        # Step 3: Ensure POI transcripts exist (if saving)
        if save:
            console.print("[bold cyan]Step 3: Checking POI transcripts...[/bold cyan]")

            # Extract all POI names from itinerary
            all_pois = []
            for day in itinerary:
                for poi_obj in day['pois']:
                    all_pois.append(poi_obj['poi'])

            # Generate missing transcripts
            content_dir = ctx.obj['content_dir']
            transcript_status = ensure_poi_transcripts(
                pois=all_pois,
                city=city,
                language=language,
                content_dir=content_dir,
                config=config,
                provider=provider
            )

            # Count how many were generated
            generated_count = sum(1 for status in transcript_status.values() if status)
            if generated_count > 0:
                console.print(f"\n[green]✓ Generated {generated_count} new transcripts in {language_name}[/green]\n")
            else:
                console.print(f"\n[green]✓ All transcripts already exist[/green]\n")

        # Step 4: Save tour (optional)
        if save:
            console.print("[bold cyan]Step 4: Saving tour...[/bold cyan]")
            tour_manager = TourManager(config, content_dir=content_dir)

            input_parameters = {
                'city': city,
                'duration_days': days,
                'interests': interests_list,
                'preferences': preferences,
                'must_see': must_see_list,
                'provider': provider,
                'language': language
            }

            save_result = tour_manager.save_tour(
                tour_data=optimized_result,
                city=city,
                input_parameters=input_parameters,
                selection_result=selection_result,
                language=language
            )

            console.print(f"[green]✓ Tour saved with ID: {save_result['tour_id']}[/green]")
            console.print(f"[dim]  Version: {save_result['version_string']}[/dim]")
            console.print(f"[dim]  Location: {save_result['tour_path']}[/dim]")
        else:
            console.print("[dim]💡 Tip: Use --save to save this itinerary for later[/dim]")

        console.print(f"\n[green]✓ Trip planning complete![/green]")

    except Exception as e:
        console.print(f"[red]Error planning trip: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@trip.command('list')
@click.option('--city', help='Filter by city')
@click.pass_context
def trip_list(ctx, city):
    """List saved tours"""
    config = ctx.obj['config']
    content_dir = ctx.obj['content_dir']

    try:
        tour_manager = TourManager(config, content_dir=content_dir)
        tours = tour_manager.list_tours(city=city)

        if not tours:
            console.print(f"[yellow]No saved tours found{' for ' + city if city else ''}[/yellow]")
            return

        table = Table(title=f"Saved Tours{' - ' + city if city else ''}")
        table.add_column("Tour ID", style="cyan")
        table.add_column("City", style="green")
        table.add_column("Days", style="yellow")
        table.add_column("Languages", style="magenta")
        table.add_column("Score", style="blue")
        table.add_column("Updated", style="dim")

        for tour in tours:
            tour_id = tour.get('tour_id', 'N/A')
            tour_city = tour.get('city', 'N/A')

            # Get available languages
            languages = tour.get('languages', ['en'])
            languages_str = ', '.join(languages)

            # Get latest version info (from any language)
            version_history = tour.get('version_history', [])
            if not version_history:
                # Try language-specific version history
                for lang in languages:
                    version_history_key = f'version_history_{lang}'
                    if version_history_key in tour:
                        version_history = tour[version_history_key]
                        break

            if version_history:
                latest = version_history[-1]
                score = latest.get('optimization_score', 0)
            else:
                score = 0

            # Calculate days from version history or metadata
            days = len(tour.get('itinerary', [])) if 'itinerary' in tour else 'N/A'

            updated = tour.get('updated_at', 'N/A')[:10]  # Show date only

            table.add_row(
                tour_id,
                tour_city,
                str(days),
                languages_str,
                f"{score:.2f}",
                updated
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(tours)} tour(s)[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing tours: {e}[/red]")
        sys.exit(1)


@trip.command('show')
@click.argument('tour_id')
@click.option('--city', required=True, help='City name')
@click.option('--version', type=int, help='Version number (defaults to latest)')
@click.option('--language', default='en', help='Tour language (ISO 639-1 code, e.g., en, zh-tw)')
@click.pass_context
def trip_show(ctx, tour_id, city, version, language):
    """Show details of a saved tour"""
    config = ctx.obj['config']
    content_dir = ctx.obj['content_dir']

    try:
        # Normalize language
        language = normalize_language_code(language)
        language_name = get_language_name(language)

        tour_manager = TourManager(config, content_dir=content_dir)
        tour_data = tour_manager.load_tour(city, tour_id, version, language)

        console.print(f"\n[bold cyan]Tour: {tour_id}[/bold cyan]")
        console.print(f"[dim]City: {city} | Language: {language_name}{f' | Version: v{version}' if version else ' | Latest version'}[/dim]\n")

        # Show optimization scores
        scores = tour_data.get('optimization_scores', {})
        console.print(f"[bold]Optimization Scores:[/bold]")
        console.print(f"  Distance: {scores.get('distance_score', 0):.2f}")
        console.print(f"  Coherence: {scores.get('coherence_score', 0):.2f}")
        console.print(f"  Overall: {scores.get('overall_score', 0):.2f}\n")

        # Show itinerary
        itinerary = tour_data.get('itinerary', [])
        for day_plan in itinerary:
            day_num = day_plan.get('day', 0)
            day_pois = day_plan.get('pois', [])
            total_hours = day_plan.get('total_hours', 0)
            total_km = day_plan.get('total_walking_km', 0)

            console.print(f"[bold yellow]Day {day_num}[/bold yellow] ({total_hours:.1f}h, {total_km:.1f}km)")

            for i, poi_entry in enumerate(day_pois, 1):
                poi_name = poi_entry.get('poi', 'Unknown')
                # Use estimated_hours from POI metadata
                visit_time = poi_entry.get('estimated_hours', 2.0)

                # Calculate walking time from previous POI
                walking_minutes = 0
                if i > 1:
                    prev_poi = day_pois[i - 2]
                    prev_coords = prev_poi.get('coordinates', {})
                    curr_coords = poi_entry.get('coordinates', {})

                    if prev_coords.get('latitude') and curr_coords.get('latitude'):
                        from math import radians, sin, cos, sqrt, asin
                        lat1, lon1 = radians(prev_coords['latitude']), radians(prev_coords['longitude'])
                        lat2, lon2 = radians(curr_coords['latitude']), radians(curr_coords['longitude'])
                        dlat, dlon = lat2 - lat1, lon2 - lon1
                        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                        distance_km = 2 * 6371 * asin(sqrt(a))
                        walking_minutes = (distance_km / 4.0) * 60

                if i == 1:
                    console.print(f"  {i}. {poi_name} ({visit_time:.1f}h)")
                else:
                    console.print(f"  {i}. {poi_name} ({visit_time:.1f}h) ← {walking_minutes:.0f}min walk")

            console.print()

    except FileNotFoundError as e:
        console.print(f"[red]Tour not found: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error showing tour: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


# ==== Validation Commands ====

@cli.group()
def validate():
    """Data validation commands"""
    pass


@validate.command('combo-tickets')
@click.option('--city', required=True, help='City name (e.g., rome, paris)')
@click.pass_context
def validate_combo_tickets(ctx, city):
    """
    Validate combo ticket data consistency.

    Checks:
    - All members in combo tickets are valid POIs
    - All POIs referencing combo tickets have valid IDs
    - Bi-directional consistency between tickets and POI references
    """
    from data.combo_ticket_loader import ComboTicketLoader

    console.print(f"\n[bold cyan]Validating combo tickets for {city}...[/bold cyan]\n")

    loader = ComboTicketLoader()

    try:
        # Load combo tickets
        combo_tickets = loader.load_city_combo_tickets(city)

        if not combo_tickets:
            console.print(f"[yellow]No combo tickets found for {city}[/yellow]")
            return

        console.print(f"[dim]Found {len(combo_tickets)} combo ticket(s)[/dim]\n")

        # Validate
        issues = loader.validate_combo_tickets(city)

        if not issues:
            console.print("[green]✓ All combo tickets are valid![/green]")
            console.print(f"[dim]Validated {len(combo_tickets)} combo ticket(s) with no issues[/dim]")
            return

        # Display issues
        error_count = sum(1 for issue in issues if issue['type'] == 'error')
        warning_count = sum(1 for issue in issues if issue['type'] == 'warning')

        console.print(f"[yellow]Found {len(issues)} validation issue(s):[/yellow]")
        console.print(f"[red]  • {error_count} error(s)[/red]")
        console.print(f"[yellow]  • {warning_count} warning(s)[/yellow]\n")

        # Group issues by type
        errors = [i for i in issues if i['type'] == 'error']
        warnings = [i for i in issues if i['type'] == 'warning']

        if errors:
            console.print("[bold red]Errors:[/bold red]")
            for issue in errors:
                console.print(f"  [red]✗[/red] {issue['message']}")
                if issue.get('entity'):
                    console.print(f"    [dim]Entity: {issue['entity']}[/dim]")
                if issue.get('poi'):
                    console.print(f"    [dim]POI: {issue['poi']}[/dim]")
                if issue.get('combo_ticket'):
                    console.print(f"    [dim]Ticket: {issue['combo_ticket']}[/dim]")
            console.print()

        if warnings:
            console.print("[bold yellow]Warnings:[/bold yellow]")
            for issue in warnings:
                console.print(f"  [yellow]⚠[/yellow] {issue['message']}")
                if issue.get('entity'):
                    console.print(f"    [dim]Entity: {issue['entity']}[/dim]")
                if issue.get('poi'):
                    console.print(f"    [dim]POI: {issue['poi']}[/dim]")
                if issue.get('combo_ticket'):
                    console.print(f"    [dim]Ticket: {issue['combo_ticket']}[/dim]")
            console.print()

        # Exit with error code if there are errors
        if error_count > 0:
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error during validation: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    cli(obj={})
