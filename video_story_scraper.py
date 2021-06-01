#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Define a web scraping spider class to scrape a 
single Russian news story and download:
1. The story metadata
2. The video transcript
3. The video
"""

# Python standard library
import json
import pathlib
import time
from urllib.parse import urlparse
from urllib.request import urlretrieve

# External packages
import moviepy.editor
import requests
from bs4 import BeautifulSoup


def _get_json_from_response(response):
    return response.json() if response and response.status_code == 200 else None


class VideoStoryScraper:
    """docstring"""
    def __init__(
        self,
        data_store_root = None,
        url = None,
        video_version = ["ld"],
    ):

        data_store_root = pathlib.Path(data_store_root)
        assert data_store_root.exists()
        self.data_store_root = data_store_root

        self.url = url
        self.hostname = urlparse(url).hostname
        self.scheme = urlparse(url).scheme

        self.video_version = video_version

        self.page = None
        self.soup = None
        self.transcript_html = None
        self.url_data_playlist_url = None
        self.playlist_data = None
        self.title = None
        self.uid = None
        self.filename_metadata = None
        self.filename_transcript = None
        self.filepath_metadata = None
        self.filepath_transcript = None
        
    def _request_page(self):
        self.page = requests.get(self.url)

    def _parse_page(self):
        self.soup = BeautifulSoup(self.page.text, "html.parser")

    def _parse_transcript(self):
        selector_transcript = ".itv-text.itv-col-8.itv-col-hd-12.w_content.th-color-text-article .editor.text-block.active"
        transcript_list = self.soup.select(selector_transcript)
        assert len(transcript_list) == 1
        transcript_soup = transcript_list[0]
        self.transcript_html = transcript_soup.prettify()

    def _parse_data_playlist_url(self):
        selector_data_playlist_url = "div.tv1player:not(.hidden)"
        target_attr = "data-playlist-url"
        data_playlist_url_list = self.soup.select(selector_data_playlist_url)
        assert len(data_playlist_url_list) == 1
        data_playlist_url_soup = data_playlist_url_list[0]
        data_playlist_url_end = data_playlist_url_soup.attrs[target_attr]
        self.url_data_playlist_url = (
            self.scheme + "://" + self.hostname + data_playlist_url_end
        )

    def _request_playlist_data(self):
        #self.page = requests.get(self.url)
        response = requests.get(self.url_data_playlist_url)
        self.playlist_data = _get_json_from_response(response)
        assert len(self.playlist_data) == 1
        self.playlist_data = self.playlist_data[0]

    def _simplify_playlist_data(self):
        exclude_keys = [
            "poster", 
            "poster_thumb", 
            "embed_allowed", 
            "ads", 
            "show_advertising_checked", 
            "timeline_actions",
        ]
        self.playlist_data = {
            k : v for k, v in self.playlist_data.items() if k not in exclude_keys
        }

    def _set_uid(self):
        self.uid = self.playlist_data["uid"]

    def _parse_title(self):
        self.title = self.playlist_data["title"]

    def _set_data_store_leaf(self):
        self.data_store_leaf = self.data_store_root / str(self.uid)

    def _set_filename_metadata(self):
        self.filename_metadata = ("metadata_" + str(self.uid) + ".json")

    def _set_filename_transcript(self):
        self.filename_transcript = ("transcript_" + str(self.uid) + ".html")

    def _set_filepath_metadata(self):
        self.filepath_metadata = self.data_store_leaf / self.filename_metadata 

    def _set_filepath_transcript(self):
        self.filepath_transcript = self.data_store_leaf / self.filename_transcript

    def _set_video_urls(self):
        vid_links = {
            vid_link.get("name") : vid_link.get("src")
            for vid_link in self.playlist_data.get("mbr")
        }

        vid_links = {
            k : (self.scheme + ":" + v) for k, v in vid_links.items()
        }

        self.video_urls = vid_links

    def _set_filenames_videos(self):
        self.filenames_videos = {
            k : ("video_" + k + ".mp4") for k in self.video_urls.keys()
        }
        
    def _set_filepaths_videos(self):
        self.filepaths_videos = {
            k : (self.data_store_leaf / v) for k, v in self.filenames_videos.items()
        }

    def request_and_parse_page(self):
        self._request_page()
        self._parse_page()
        self._parse_transcript()
        self._parse_data_playlist_url()
        self._request_playlist_data()
        self._simplify_playlist_data()
        self._parse_title()
        self._set_uid()
        self._set_data_store_leaf()
        self._set_filename_metadata()
        self._set_filename_transcript()
        self._set_filepath_metadata()
        self._set_filepath_transcript()
        self._set_video_urls()
        self._set_filenames_videos()
        self._set_filepaths_videos()

    def _make_data_store_leaf(self):
        self.data_store_leaf.mkdir(exist_ok=True)

    def _download_playlist_data(self):
        with open(self.filepath_metadata, "w", encoding='utf-8') as file:
            json.dump(self.playlist_data, file, ensure_ascii=False, indent=4)

    def _download_transcript(self):
        with open(self.filepath_transcript, "w", encoding='utf-8') as file:
            file.write(self.transcript_html)

    def _download_videos(self):
        for i, version in enumerate(self.video_version):
            filepath = self.filepaths_videos[version]

            if filepath.exists():
                # Skip if it already exists
                continue

            url_video = self.video_urls[version]
            urlretrieve(url_video, filepath)

            # Wait between videos
            if i > 0:
                time.sleep(60)

    def _generate_mp3(self):
        version_for_mp3 = self.video_version[-1]
        filepath_video = self.filepaths_videos[version]
        assert filepath_video.exists()

        video = moviepy.editor.VideoFileClip(str(filepath_video))

        self.filename_mp3 = "audio.mp3"
        self.filepath_mp3 = self.data_store_leaf / "audio.mp3"
        video.audio.write_audiofile(self.filepath_mp3)

    def download_data(self, generate_mp3=True):
        print(f"Saving data to {self.data_store_leaf}")
        self._make_data_store_leaf()
        self._download_playlist_data()
        self._download_transcript()
        self._download_videos()
        if generate_mp3:
            self._generate_mp3()
