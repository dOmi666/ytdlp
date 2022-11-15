# ⚠ Don't use relative imports
from yt_dlp.extractor.common import InfoExtractor


# ℹ️ Instructions on making extractors can be found at:
# 🔗 https://github.com/yt-dlp/yt-dlp/blob/master/CONTRIBUTING.md#adding-support-for-a-new-site

class NormalPluginIE(InfoExtractor):
    _WORKING = False
    IE_DESC = False
    _VALID_URL = r'^normalplugin:'

    def _real_extract(self, url):
        self.to_screen('URL "%s" successfully captured' % url)
