import click

from ai_artist_detector.lib.helpers import get_first_query_param


@click.group('iimuzyka')
def iimuzyka_group() -> None:
    """> iimuzyka commands"""


@iimuzyka_group.command('ambiguous')
def list_ambiguous_artists() -> None:
    """List artists that could not be matched to YouTube profile automatically"""
    from loguru import logger

    from ai_artist_detector.containers import core, repositories

    all_query_results = repositories.youtube_search_results_repository.get_all()

    ambiguous_queries = {query for query, results in all_query_results if len(results) > 1}

    if not ambiguous_queries:
        logger.info('NoAmbiguousQueriesFound')
        return

    logger.debug('FoundAmbiguousQueries', count=len(ambiguous_queries))

    cached_iimuzyka_artists = repositories.iimuzyka_ids_mapping_repository.get_all()

    ambiguous_artist_ids: dict[int, str] = {}

    for artist_id, name, youtube_paths in cached_iimuzyka_artists:
        for path, query_params in youtube_paths:
            if path.strip('/') != 'results':
                continue
            search_query = get_first_query_param(query_params, 'search_query')
            if search_query is None:
                continue

            normalized_query = search_query.lower().strip()
            if normalized_query in ambiguous_queries:
                ambiguous_artist_ids[artist_id] = name

    if not ambiguous_artist_ids:
        logger.info('NoAmbiguousArtistsFound')
        return

    for artist_id, name in ambiguous_artist_ids.items():
        logger.info(
            'AmbiguousArtist',
            artist_name=name,
            artist_url=f'https://{core.config.sources.iimuzyka_top.host}/{artist_id}',
        )


@iimuzyka_group.command('override')
@click.option('--artist-id', '-i', 'artist_id', help='Iimuzyka artist ID', required=True, type=click.INT)
@click.option('--youtube-id', '-y', 'youtube_id', help='YouTube artist ID or handle', required=True, type=click.STRING)
def override_artist_youtube(artist_id: int, youtube_id: str) -> None:
    """Override YouTube profile for artists that could not be matched automatically"""
    import re

    from loguru import logger

    from ai_artist_detector.containers import core, repositories

    youtube_id = youtube_id.strip()

    if not youtube_id.startswith('@') and not re.match(r'[A-Za-z0-9_-]{11}', youtube_id):
        msg = 'Invalid YouTube ID'
        raise click.BadParameter(msg)

    repositories.iimuzyke_overrides_repository.set_override(iimuzyka_id=artist_id, youtube_handle=youtube_id)

    if youtube_id.startswith('@'):
        youtube_url = f'https://youtube.com/{youtube_id}'
    else:
        youtube_url = f'https://youtube.com/channel/{youtube_id}'

    logger.info(
        'ArtistYouTubeOverrideSet',
        artist_profile=f'https://{core.config.sources.iimuzyka_top.host}/{artist_id}',
        youtube_url=youtube_url,
    )
