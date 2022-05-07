import json
import re
from .common import InfoExtractor
from ..utils import (
    float_or_none,
    merge_dicts,
    str_to_int,
    traverse_obj,
    try_call,
    unified_timestamp
)

class PodchaserIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:www\.)?podchaser\.com/
        (?:
            (?:podcasts/[\w-]+-(?P<podcast_id>[\d]+)))
        (?:/episodes/[\w\-]+-
            (?P<id>[\d]+))?'''
    _TESTS = [{
        'url': 'https://www.podchaser.com/podcasts/cum-town-36924/episodes/ep-285-freeze-me-off-104365585',
        'info_dict': {
            'id': '104365585',
            'title': 'Ep. 285 – freeze me off',
            'description': 'cam ahn',
            'thumbnail': r're:^https?://.*\.jpg$',
            'ext': 'mp3',
            'categories': ['Comedy'],
            'tags': ['comedy', 'dark humor'],
            'series': 'Cum Town',
            'duration': 3708,
            'timestamp': 1636531259,
            'upload_date': '20211110',
            'rating': 4.0
        }
    }, {
        'url': 'https://www.podchaser.com/podcasts/the-bone-zone-28853',
        'info_dict': {
            'id': '28853',
            'title': 'The Bone Zone',
            'description': 'Podcast by The Bone Zone',
        },
        'playlist_count': 275
    }, {
        'url': 'https://www.podchaser.com/podcasts/sean-carrolls-mindscape-scienc-699349/episodes',
        'info_dict': {
            'id': '699349',
            'title': 'Sean Carroll\'s Mindscape: Science, Society, Philosophy, Culture, Arts, and Ideas',
            'description': 'md5:2cbd8f4749891a84dc8235342e0b5ff1'
        },
        'playlist_mincount': 225
    }]

    def _real_extract(self, url):
        audio_id, podcast_id = self._match_valid_url(url).group('id', 'podcast_id')
        if audio_id:
            episodes = [self._download_json('https://api.podchaser.com/episodes/%s' % audio_id, audio_id)]
        else:
            total_episode_count = self._download_json(
                'https://api.podchaser.com/list/episode', podcast_id,
                headers={'Content-Type': 'application/json;charset=utf-8'},
                data=json.dumps({
                    'filters': {'podcast_id': podcast_id}
                }).encode()).get('total')
            episodes = []
            for i in range(total_episode_count // 100 + 1):
                curr_episodes_data = self._download_json(
                    'https://api.podchaser.com/list/episode', podcast_id,
                    headers={'Content-Type': 'application/json;charset=utf-8'},
                    data=json.dumps({
                        'start': i * 100,
                        'count': 100,
                        'sort_order': 'SORT_ORDER_RECENT',
                        'filters': {
                            'podcast_id': podcast_id
                        }, 'options': {}
                    }).encode())
                curr_episodes = curr_episodes_data.get('entities') or []
                if len(curr_episodes) + len(episodes) <= total_episode_count:
                    episodes.extend(curr_episodes)

        podcast_data = merge_dicts(
            self._download_json('https://api.podchaser.com/podcasts/%s' % podcast_id, audio_id or podcast_id) or {},
            episodes[0].get('podcast') or {} if episodes else {})

        entries = [{
            'id': str(episode.get('id')),
            'title': episode.get('title'),
            'description': episode.get('description'),
            'url': episode.get('audio_url'),
            'thumbnail': episode.get('image_url'),
            'duration': str_to_int(episode.get('length')),
            'timestamp': unified_timestamp(episode.get('air_date')),
            'rating': float_or_none(episode.get('rating')),
            'categories': list(set(traverse_obj(podcast_data, (('summary', None), 'categories', ..., 'text')))),
            'tags': traverse_obj(podcast_data, ('tags', ..., 'text')),
            'series': podcast_data.get('title'),
        } for episode in episodes]

        if len(entries) > 1:
            return self.playlist_result(
                entries, playlist_id=str(podcast_data.get('id')),
                playlist_title=podcast_data.get('title'),
                playlist_description=podcast_data.get('description'))
        return entries[0]
