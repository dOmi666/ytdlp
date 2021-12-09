# coding: utf-8
from __future__ import unicode_literals

import re
from .common import InfoExtractor
from ..utils import (
    determine_ext,
    extract_attributes,
    int_or_none,
    traverse_obj,
    unified_strdate,
    unified_timestamp,
)


class FranceCultureIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?franceculture\.fr/emissions/(?:[^/]+/)*(?P<id>[^/?#&]+)'
    _TESTS = [{
        # playlist
        'url': 'https://www.franceculture.fr/emissions/hasta-dente',
        'playlist_count': 12,
        'info_dict': {
            'id': 'hasta-dente',
            'title': 'Hasta Dente !',
            'description': None,
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20190305',
            'timestamp': 1551744000,
        },
        'playlist': [{
            'info_dict': {
                'id': '/emissions/hasta-dente/episode-1-jeudi-vous-avez-dit-bizarre',
                'ext': 'mp3',
                'title': 'Épisode 1. Jeudi, vous avez dit bizarre ?',
                'description': 'md5:52ce4deeb6f3facba27f9fc4a546678b',
                'duration': 604,
                'timestamp': 1518486300,
                'uploader': None,
                'upload_date': '20180213',
            },
        },
        ],
    }, {
        'url': 'https://www.franceculture.fr/emissions/carnet-nomade/rendez-vous-au-pays-des-geeks',
        'info_dict': {
            'id': 'rendez-vous-au-pays-des-geeks',
            'display_id': 'rendez-vous-au-pays-des-geeks',
            'ext': 'mp3',
            'title': 'Rendez-vous au pays des geeks',
            'thumbnail': r're:^https?://.*\.jpg$',
            'upload_date': '20140301',
            'vcodec': 'none',
            'duration': 3569,
            'description': None,
            'timestamp': 1393632000,
        },
    }, {
        # no thumbnail
        'url': 'https://www.franceculture.fr/emissions/la-recherche-montre-en-main/la-recherche-montre-en-main-du-mercredi-10-octobre-2018',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        display_id = self._match_id(url)

        webpage = self._download_webpage(url, display_id)

        video_data = extract_attributes(self._search_regex(
            r'''(?sx)
                (?:
                    </h1>|
                    <div[^>]+class="[^"]*?(?:title-zone-diffusion|heading-zone-(?:wrapper|player-button))[^"]*?"[^>]*>
                ).*?
                (<button[^>]+data-(?:url|asset-source)="[^"]+"[^>]+>)
            ''',
            webpage, 'video data'))

        title = self._html_search_regex(
            r'(?s)<h1[^>]*itemprop="[^"]*name[^"]*"[^>]*>(.+?)</h1>',
            webpage, 'title', default=self._og_search_title(webpage))
        description = self._html_search_regex(
            r'(?s)<div[^>]+class="intro"[^>]*>.*?<h2>(.+?)</h2>',
            webpage, 'description', default=None)

        playlist_data = self._search_regex(
            r'''(?sx)
                <div[^>]+class="[^"]*?podcast-list[^"?]*?"[^>]*>
                (.*?)
                <div[^>]+class="[^"]*?see-more-anchor[^"]*?">
            ''',
            webpage, 'playlist data', fatal=False, default=None)

        thumbnail = self._og_search_thumbnail(webpage)
        uploader = self._html_search_regex(
            r'(?s)<span class="author">(.*?)</span>',
            webpage, 'uploader', default=None)
        upload_date = self._search_regex(
            r'(?s)"datePublished":\s*"(\d{4}-\d{2}-\d{2})',
            webpage, 'date', default=None)

        infos = {
            'thumbnail': thumbnail,
            'uploader': uploader,
            'timestamp': unified_timestamp(upload_date) if upload_date is not None else None,
            'upload_date': unified_strdate(upload_date) if upload_date is not None else None,
        }

        # page has playlist
        if playlist_data is not None:
            entries = []

            for item, item_description in re.findall(
                r'(?s)(<button[^<]*class="[^"]*replay-button[^>]*>).*?<p[^>]*class="[^"]*teaser-content-body[^>]*>(.*?)</p>',
                playlist_data):
                    item_attributes = extract_attributes(item)

                    entries.append({
                        'id': item_attributes.get('data-diffusion-path'),
                        'url': item_attributes.get('data-url'),
                        'title': item_attributes.get('data-diffusion-title'),
                        'duration': int_or_none(traverse_obj(item_attributes, 'data-duration-seconds', 'data-duration-seconds')),
                        'description': item_description,
                        'timestamp': int_or_none(item_attributes.get('data-start-time')),
                        'thumbnail': thumbnail,
                        'uploader': uploader,
                    })

            return self.playlist_result(entries, display_id, title, description, **infos)

        video_url = traverse_obj(video_data, 'data-url', 'data-asset-source')

        ext = determine_ext(video_url.lower())

        infos.update({
            'id': display_id,
            'display_id': display_id,
            'url': video_url,
            'title': title,
            'description': description,
            'ext': ext,
            'vcodec': 'none' if ext == 'mp3' else None,
            'duration': int_or_none(video_data.get('data-duration')),
        })

        return infos
