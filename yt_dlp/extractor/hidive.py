import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    extract_attributes,
    get_element_by_id,
    get_element_html_by_attribute,
    int_or_none,
    traverse_obj,
    try_get,
    url_or_none,
    urlencode_postdata,
)


class HiDiveIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hidive\.com/stream/(?P<id>(?P<title>[^/]+)/(?P<key>[^/?#&]+))'
    # Using X-Forwarded-For results in 403 HTTP error for HLS fragments,
    # so disabling geo bypass completely
    _GEO_BYPASS = False
    _NETRC_MACHINE = 'hidive'
    _LOGIN_URL = 'https://www.hidive.com/account/login'

    _TESTS = [{
        'url': 'https://www.hidive.com/stream/the-comic-artist-and-his-assistants/s01e001',
        'info_dict': {
            'id': 'the-comic-artist-and-his-assistants/s01e001',
            'ext': 'mp4',
            'title': 'the-comic-artist-and-his-assistants/s01e001',
            'series': 'the-comic-artist-and-his-assistants',
            'season_number': 1,
            'episode_number': 1,
        },
        'params': {
            'skip_download': True,
        },
        'skip': 'Requires Authentication',
    }]

    _SUBTITLE_ATTR_RE = re.compile(r'\bdata-captions="([^"]+)"')

    def _perform_login(self, username, password):
        webpage = self._download_webpage(self._LOGIN_URL, None)
        form = self._search_regex(
            r'(?s)<form[^>]+action="/account/login"[^>]*>(.+?)</form>',
            webpage, 'login form', default=None)
        if not form:
            return
        data = self._hidden_inputs(form)
        data.update({
            'Email': username,
            'Password': password,
        })
        login_webpage = self._download_webpage(
            self._LOGIN_URL, None, 'Logging in', data=urlencode_postdata(data))
        # If the user has multiple profiles on their account, select one. For now pick the first profile.
        profile_id = self._search_regex(
            r'<button [^>]+?data-profile-id="(\w+)"', login_webpage, 'profile id', default=None)
        if profile_id is None:
            return  # If only one profile, Hidive auto-selects it
        self._request_webpage(
            'https://www.hidive.com/ajax/chooseprofile', None,
            data=urlencode_postdata({
                'profileId': profile_id,
                'hash': self._search_regex(
                    r'\<button [^>]+?data-hash="(\w+)"', login_webpage, 'profile id hash'),
                'returnUrl': '/dashboard'
            }))

    def _get_preferred_content_language(self):
        profile_html = self._download_webpage('https://www.hidive.com/profile/edit', None,
            'Fetching user profile information')

        lang_select_html = get_element_by_id('UserProfile_Language', profile_html)
        if not lang_select_html:
            return None

        selected_lang_option = get_element_html_by_attribute('selected', 'selected',
            lang_select_html, tag='option')
        if not selected_lang_option:
            return None

        return extract_attributes(selected_lang_option).get('value')

    def _real_initialize(self):
        self._preferred_content_language = self._get_preferred_content_language()
        self.write_debug(f'Preferred content language: {self._preferred_content_language}')

        if not self._preferred_content_language:
            self.report_warning('Failed to determine preferred content language, format sorting might be incorrect')

    def _call_api(self, video_id, title, key, data={}, **kwargs):
        data = {
            **data,
            'Title': title,
            'Key': key,
            'PlayerId': 'f4f895ce1ca713ba263b91caeb1daa2d08904783',
        }
        return self._download_json(
            'https://www.hidive.com/play/settings', video_id,
            data=urlencode_postdata(data), **kwargs) or {}

    def _parse_one_setting(self, setting, video_id, formats, subtitles, parsed_urls):
        restriction = setting.get('restrictionReason')
        if restriction == 'RegionRestricted':
            self.raise_geo_restricted()
        if restriction and restriction != 'None':
            raise ExtractorError(
                '%s said: %s' % (self.IE_NAME, restriction), expected=True)

        for rendition_id, rendition in setting['renditions'].items():
            audio, version, extra = rendition_id.split('_')
            m3u8_url = url_or_none(try_get(rendition, lambda x: x['bitrates']['hls']))
            if m3u8_url not in parsed_urls:
                parsed_urls.add(m3u8_url)
                frmt = self._extract_m3u8_formats(
                    m3u8_url, video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id=rendition_id, fatal=False)
                for f in frmt:
                    f['language'] = audio
                    f['language_preference'] = 10 if audio == self._preferred_content_language else -1
                    f['format_note'] = f'{version}, {extra}'
                formats.extend(frmt)

        for rendition in setting['renditions'].values():
            for cc_file in rendition.get('ccFiles') or []:
                cc_url = url_or_none(try_get(cc_file, lambda x: x[2]))
                cc_lang = try_get(cc_file, (lambda x: x[1].replace(' ', '-').lower(), lambda x: x[0]), str)
                if cc_url not in parsed_urls and cc_lang:
                    parsed_urls.add(cc_url)
                    subtitles.setdefault(cc_lang, []).append(
                        {'url': cc_url, 'name': traverse_obj(cc_file, 1, expected_type=str)}
                    )

    def _real_extract(self, url):
        video_id, title, key = self._match_valid_url(url).group('id', 'title', 'key')
        video_page = self._download_webpage(url, video_id, 'Fetching subtitle languages')

        subtitle_languages = set(self._SUBTITLE_ATTR_RE.findall(video_page))
        settings = [
            self._call_api(video_id, title, key, {'Captions': sl})
            for sl in subtitle_languages
        ]

        formats, parsed_urls = [], {None}
        subtitles = {}

        for a_setting in settings:
            self._parse_one_setting(a_setting, video_id, formats, subtitles, parsed_urls)

        return {
            'id': video_id,
            'title': video_id,
            'subtitles': subtitles,
            'formats': formats,
            'series': title,
            'season_number': int_or_none(
                self._search_regex(r's(\d+)', key, 'season number', default=None)),
            'episode_number': int_or_none(
                self._search_regex(r'e(\d+)', key, 'episode number', default=None)),
            'http_headers': {'Referer': url}
        }
