import base64

from mutagen.flac import Picture
from mutagen.id3 import APIC, TALB, TDRC, TIT2, TOPE, TPE1, TPE2, TRCK
from mutagen.mp4 import MP4Cover


class BaseMetadataSetter:
    input_metadata_key_to_target_tag_map = {
        "artist": "",
        "album": "",
        "title": "",
        "track_number": "",
        "recording_year": "",
        "cover": "",
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

    def set_cover(self, byteimage):
        key = self.input_metadata_key_to_target_tag_map[self.input_metadata_key]
        self.filething.tags[key] = byteimage

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
        "cover": "covr",
    }

    def set_tag(self, value):
        key = self.input_metadata_key_to_target_tag_map[self.input_metadata_key]
        # edge case: track number takes in a tuple of ints, not an int
        # the second int is the number of total tracks
        # setting to 0 for simplicity
        if key == "trkn":
            value = [[int(value), 0]]
        self.filething.tags[key] = value

    def set_cover(self, byteimage):
        key = self.input_metadata_key_to_target_tag_map[self.input_metadata_key]
        mp4_cover = [MP4Cover(byteimage)]
        self.filething.tags[key] = mp4_cover


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
        "cover": "metadata_block_picture",
    }

    def set_cover(self, byteimage):
        print("setting image for .opus file")
        cover = Picture()
        cover.data = byteimage
        cover.type = 3
        cover.mime = "image/jpeg"
        cover.width = 400
        cover.height = 400
        cover.depth = 24

        cover_data = cover.write()
        encoded_data = base64.b64encode(cover_data)
        vcomment_value = encoded_data.decode("ascii")

        self.filething["metadata_block_picture"] = [vcomment_value]
        # file_.save()


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

    def set_tag(self, value):
        mapped_ID3_tags = self.input_metadata_key_to_id3_tag_map[
            self.input_metadata_key
        ]
        if not isinstance(mapped_ID3_tags, list):
            mapped_ID3_tags = [mapped_ID3_tags]
        for tag in mapped_ID3_tags:
            filled_tag = tag(encoding=3, text=value)
            self.filething[filled_tag.__class__.__name__] = filled_tag

    def set_cover(self, byteimage):
        print("setting image for ID3 file")
        # byteimage = open(picture, 'rb').read()
        self.filething["APIC"] = APIC(3, "image/jpeg", 3, "Front cover", byteimage)
