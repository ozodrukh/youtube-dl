import os
import re
from hashlib import sha1

from .common import InfoExtractor
from ..compat import (compat_cookiejar)
from ..utils import (
    ExtractorError,
    urlencode_postdata,
    get_elements_by_class,
    get_element_by_class,
    extract_attributes,
    clean_html,
)


class KinoProIE(InfoExtractor):
    _VALID_URL = r"http://(?:www\.)?kinopro\.uz/player/(?P<type>[\w]+)/(?P<title>[\w]+)"
    _NETRC_MACHINE = "kinopro"
    _LOGIN_REQUIRED = True

    _LOGIN_URL = "http://kinopro.uz/"

    _directory = '/tmp/kinopro'
    _pattern = re.compile(_VALID_URL)

    def _real_initialize(self):
        self._login()

    def _login(self):
        username, password = self._get_login_info()

        if username is None or password is None:
            self.raise_login_required()

        filename = sha1(username + password).hexdigest()

        if not os.path.exists(self._directory):
            os.mkdir(self._directory)

        cookiejar = compat_cookiejar.MozillaCookieJar()

        if os.path.exists(self._directory + filename):
            cookiejar.load(self._directory + filename)
            self._downloader.cookiejar._cookies = cookiejar._cookies.copy()

        login_source, handle = self._download_webpage_handle(
            self._LOGIN_URL,
            video_id=None,
            note="Checking login required",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "http://kinopro.uz/",
            }
        )

        if "BITRIX_SM_LOGIN" in self._get_cookies(self._LOGIN_URL):
            self.to_screen("Valid auth token found, skipping login")
            return True

        form_data = self._hidden_inputs(login_source)
        form_data.update({
            "USER_LOGIN": username,
            "USER_PASSWORD": password
        })

        self._download_webpage_handle(
            self._LOGIN_URL,
            video_id=None,
            data=urlencode_postdata(form_data),
            note="Logging in",
            query={"login": "yes"},
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "http://kinopro.uz/",
            })

        if "BITRIX_SM_LOGIN" not in self._get_cookies(self._LOGIN_URL):
            if os.path.exists(self._directory + filename):
                os.remove(self._directory + filename)

            raise ExtractorError("Invalid username or password, or someone already logged in")

        cookiejar._cookies = self._downloader.cookiejar._cookies.copy()
        cookiejar.save(self._directory + filename)
        return True

    def _real_extract(self, url):
        matches = self._pattern.match(url)

        type = matches.group("type")
        title = matches.group("title")

        page_source = self._download_webpage(url,
                                             video_id=title,
                                             note="Extracting page meta_data for {}".format(title))

        entities = []
        seasons_list = get_elements_by_class("slist", page_source)
        for i, season in enumerate(seasons_list):
            episodes = get_elements_by_class("item", season)
            for episode in episodes:
                episode_link = extract_attributes(episode)["link"]
                episode_number_name = clean_html(get_element_by_class("play_episod", episode))
                entities.append({
                    "id": episode_number_name,
                    "episode": "{}_{}".format(title, episode_number_name),
                    "season_number": i,
                })

        return {
            "_type": "multi_video",
            "id": title,
            "title": title,
            "entities": []
        }
