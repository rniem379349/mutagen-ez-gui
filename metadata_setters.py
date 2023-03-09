from typing import Iterable

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from mutagen import File
from mutagen.id3 import TALB, TDRC, TIT2, TOPE, TPE1, TPE2, TRCK
from mutagen.mp3 import HeaderNotFoundError
from mutagen.oggopus import OggOpus
from mutagen.wave import _WaveID3


class BaseMetadataSetter:
    input_metadata_key_to_target_tag_map = {
        "artist": "",
        "album": "",
        "title": "",
        "track_number": "",
        "recording_year": "",
    }

    def __init__(self, filething, filepath, input_metadata_key, *args, **kwargs):
        if input_metadata_key not in self.input_metadata_key_to_target_tag_map.keys():
            raise ValueError(
                "Input metadata key not supported. Supported input names: {}".format(
                    ",".join(self.input_metadata_key_to_target_tag_map.keys())
                )
            )
        super().__init__(*args, **kwargs)
        self.filething = filething
        self.filepath = filepath
        self.input_metadata_key = input_metadata_key

    def set_tag(self, value):
        key = self.input_metadata_key_to_target_tag_map[self.input_metadata_key]
        self.filething.tags[key] = value

    def save_tags_to_file(self):
        self.filething.save(self.filepath)


class MP4MetadataSetter(BaseMetadataSetter):
    """
    Metadata setter for MP4 files.
    Info on mutagen's MP4 API:
    https://mutagen.readthedocs.io/en/latest/api/mp4.html
    """

    input_metadata_key_to_target_tag_map = {
        "artist": "\xa9ART",
        "album": "\xa9alb",
        "title": "\xa9nam",
        "track_number": "trkn",
        "recording_year": "\xa9day",
    }
    # def __init__(self, filething, filepath, input_metadata_key, *args, **kwargs):
    #     if input_metadata_key not in self.input_metadata_key_to_target_tag_map.keys():
    #         raise ValueError("Input metadata key not supported. Supported input names: {}".format(
    #             ",".join(self.input_metadata_key_to_target_tag_map.keys())
    #         ))
    #     super().__init__(*args, **kwargs)
    #     self.filething = filething
    #     self.filepath = filepath
    #     self.input_metadata_key = input_metadata_key

    def set_tag(self, value):
        key = self.input_metadata_key_to_target_tag_map[self.input_metadata_key]
        # edge case: track number takes in a tuple of ints, not an int
        # the second int is the number of total tracks
        # setting to 0 for simplicity
        if key == "trkn":
            value = [[int(value), 0]]
        self.filething.tags[key] = value

    # def save_tags_to_file(self):
    #     self.filething.save(self.filepath)


class VorbisMetadataSetter(BaseMetadataSetter):
    """
    Metadata setter for files with Vorbis tags (.ogg family, .flac files).
    using metadata fieldname standard outlined by Ogg Vorbis:
    https://xiph.org/vorbis/doc/v-comment.html#fieldnames
    Info on mutagen's Ogg Vorbis API:
    https://mutagen.readthedocs.io/en/latest/api/ogg.html
    """

    input_metadata_key_to_target_tag_map = {
        "artist": "artist",
        "album": "album",
        "title": "title",
        "track_number": "tracknumber",
        "recording_year": "date",
    }
    # def __init__(self, filething, filepath, input_metadata_key, *args, **kwargs):
    #     if input_metadata_key not in self.input_metadata_key_to_target_tag_map.keys():
    #         raise ValueError("Input metadata key not supported. Supported input names: {}".format(
    #             ",".join(self.input_metadata_key_to_target_tag_map.keys())
    #         ))
    #     super().__init__(*args, **kwargs)
    #     self.filething = filething
    #     self.filepath = filepath
    #     self.input_metadata_key = input_metadata_key

    # def set_tag(self, value):
    #     key = self.input_metadata_key_to_target_tag_map[self.input_metadata_key]
    #     self.filething.tags[key] = value

    # def save_tags_to_file(self):
    #     self.filething.save(self.filepath)


class ID3MetadataSetter(BaseMetadataSetter):
    """
    Metadata setter for files with ID3 tags (mostly .mp3 files).
    Info on mutagen's ID3 API:
    https://mutagen.readthedocs.io/en/latest/api/id3.html
    """

    input_metadata_key_to_id3_tag_map = {
        "artist": [TPE1, TPE2, TOPE],
        "album": TALB,
        "title": TIT2,
        "track_number": TRCK,
        "recording_year": TDRC,
    }

    # def __init__(self, tags, filepath, input_metadata_key, *args, **kwargs):
    #     if input_metadata_key not in self.input_metadata_key_to_id3_tag_map.keys():
    #         raise ValueError("Input metadata key not supported. Supported input names: {}".format(
    #             ",".join(self.input_metadata_key_to_id3_tag_map.keys())
    #         ))
    #     super().__init__(*args, **kwargs)
    #     self.tags = tags
    #     self.filepath = filepath
    #     self.input_metadata_key = input_metadata_key

    def set_tag(self, value):
        mapped_ID3_tags = self.input_metadata_key_to_id3_tag_map[
            self.input_metadata_key
        ]
        tags = []
        if not isinstance(mapped_ID3_tags, list):
            mapped_ID3_tags = [mapped_ID3_tags]
        for tag in mapped_ID3_tags:
            filled_tag = tag(encoding=3, text=value)
            self.tags[filled_tag.__class__.__name__] = filled_tag

    # def save_tags_to_file(self):
    #     self.tags.save(self.filepath)
