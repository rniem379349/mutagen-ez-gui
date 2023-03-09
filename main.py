from random import randint

import mutagen
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import NumericProperty, ObjectProperty, ReferenceListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import (
    FileChooserIconView,
    FileChooserListLayout,
    FileChooserListView,
)
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.vector import Vector
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.wave import WAVE

from metadata_setters import (
    ID3MetadataSetter,
    MetadataDisplayPanel,
    MP4MetadataSetter,
    VorbisMetadataSetter,
)


class MutagenMetadataInputGroup(BoxLayout):
    """
    Widget for setting a particular metadata tag.
    Contains a text input for the metadata, and a button to set the tag.
    Needs a metadata tag key, and a list of files to open and add metadata to.
    """

    metadata_key = ""
    selection = []

    def set_metadata(self):
        """
        Try to open the selected files with mutagen,
        guess their type and set the tag using the appropriate metadata setter.
        """
        for filepath in self.selection:
            try:
                tags = mutagen.File(filepath)
                if isinstance(tags, WAVE):
                    if tags.tags is None:
                        tags.add_tags()
                    metadata_setter = ID3MetadataSetter(
                        tags, filepath, self.metadata_key
                    )
                elif isinstance(tags, MP4):
                    metadata_setter = MP4MetadataSetter(
                        tags, filepath, self.metadata_key
                    )
                elif isinstance(
                    tags.tags,
                    (
                        mutagen.oggvorbis.OggVCommentDict,
                        mutagen.oggopus.OggOpusVComment,
                        mutagen.flac.VCFLACDict,
                    ),
                ):
                    metadata_setter = VorbisMetadataSetter(
                        tags, filepath, self.metadata_key
                    )
                elif isinstance(tags, MP3) or tags.tags is None:
                    try:
                        tags = ID3(filepath)
                    except ID3NoHeaderError:
                        tags = ID3()
                    metadata_setter = ID3MetadataSetter(
                        tags, filepath, self.metadata_key
                    )
            except Exception as exc:
                print("Couldn't open file {}, exception: {}".format(filepath, exc))
                continue
            metadata_setter.set_tag(self.metadata_input.text)
            metadata_setter.save_tags_to_file()

    def __init__(self, metadata_key, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.metadata_key = metadata_key
        self.metadata_input = TextInput()
        self.apply_button = Button(
            text="Set {}".format(metadata_name.capitalize().replace("_", " "))
        )
        self.apply_button.on_press = self.set_metadata
        self.add_widget(self.metadata_input)
        self.add_widget(self.apply_button)


class FileExplorer(FileChooserIconView):
    """File explorer widget, linked to metadata display"""

    def __init__(self, input_groups, metadata_display, **kwargs):
        super().__init__(**kwargs)
        self.input_groups = input_groups
        self.metadata_display = metadata_display
        self.multiselect = True

    def on_selection(self, instance, value):
        """
        callback which runs on selecting/deselecting a file in the explorer
        """
        for input_group in self.input_groups:
            input_group.selection = value
        # Display metadata info only when one file is selected
        if len(value) == 1:
            self.metadata_display.set_metadata_labels(value[0])
        else:
            self.metadata_display.clear_metadata_labels()


class MetadataDisplayRow(BoxLayout):
    def __init__(self, metadata_key, **kwargs) -> None:
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.metadata_key = metadata_key
        self.key_label = Label()
        self.key_label.halign = "left"
        self.key_label.valign = "middle"
        self.key_label.text = metadata_key.capitalize().replace("_", " ")
        self.value_label = Label()
        self.add_widget(self.key_label)
        self.add_widget(self.value_label)


class MetadataDisplayPanel(GridLayout):
    metadata_keys = ("artist", "album", "title", "date", "tracknumber")
    metadata_widgets = dict()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rows = 5
        self.cols = 1
        for key in self.metadata_keys:
            display_widget = MetadataDisplayRow(key)
            self.metadata_widgets[key] = display_widget
            self.add_widget(display_widget)

    def get_metadata(self, filepath):
        try:
            tags = File(filepath, easy=True)
            if isinstance(tags.tags, _WaveID3):
                artist = ", ".join(getattr(tags.get("TPE1", None), "text", ["Unknown"]))
                album = ", ".join(getattr(tags.get("TALB", None), "text", ["Unknown"]))
                title = ", ".join(getattr(tags.get("TIT2", None), "text", ["Unknown"]))
                date_stringified = [
                    str(timestamp)
                    for timestamp in getattr(
                        tags.get("TDRC", None), "text", ["Unknown"]
                    )
                ]
                date = ", ".join(date_stringified)
                tracknumber = ", ".join(
                    getattr(tags.get("TRCK", None), "text", ["Unknown"])
                )
            else:
                artist = tags.get("artist", "Unknown")
                album = tags.get("album", "Unknown")
                title = tags.get("title", "Unknown")
                date = tags.get("date", "Unknown")
                tracknumber = tags.get("tracknumber", "Unknown")
        except (HeaderNotFoundError, AttributeError):
            artist = "Unknown"
            album = "Unknown"
            title = "Unknown"
            date = "Unknown"
            tracknumber = "Unknown"
        return {
            "artist": artist,
            "album": album,
            "title": title,
            "date": date,
            "tracknumber": tracknumber,
        }

    def set_metadata_labels(self, filepath):
        tags = self.get_metadata(filepath)
        print("tags", tags)
        for key in self.metadata_keys:
            value = tags[key]
            if isinstance(value, list):
                value = ", ".join(value)
            self.metadata_widgets[key].value_label.text = value

    def clear_metadata_labels(self):
        for key in self.metadata_keys:
            self.metadata_widgets[key].value_label.text = ""


class MutaGUIMain(BoxLayout):
    """
    Main app window. This class builds the structure of the widgets that comprise the app.
    In essence, the structure is as follows:
        - The left half of the window consists of an input panel for setting metadata tags,
          and a metadata display panel below;
        - The right half of the window contains the file explorer widget
          for choosing files to edit.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        # panel for setting and displaying metadata
        self.metadata_panel = GridLayout(cols=1, rows=6, row_default_height=50)
        # input groups
        self.artist_input_group = MutagenMetadataInputGroup("artist")
        self.album_input_group = MutagenMetadataInputGroup("album")
        self.title_input_group = MutagenMetadataInputGroup("title")
        self.track_number_input_group = MutagenMetadataInputGroup("track_number")
        self.recording_year_input_group = MutagenMetadataInputGroup("recording_year")
        self.metadata_display_panel = MetadataDisplayPanel()

        self.metadata_panel.add_widget(self.artist_input_group)
        self.metadata_panel.add_widget(self.album_input_group)
        self.metadata_panel.add_widget(self.title_input_group)
        self.metadata_panel.add_widget(self.track_number_input_group)
        self.metadata_panel.add_widget(self.recording_year_input_group)
        self.metadata_panel.add_widget(self.metadata_display_panel)

        self.chooser = FileExplorer(
            input_groups=[
                self.artist_input_group,
                self.album_input_group,
                self.title_input_group,
                self.track_number_input_group,
                self.recording_year_input_group,
            ],
            metadata_display=self.metadata_display_panel,
        )

        self.add_widget(self.metadata_panel)
        self.add_widget(self.chooser)


class MutaGuiApp(App):
    """Mutagen GUI Kivy app object."""

    def build(self):
        MutaGUI = MutaGUIMain()
        return MutaGUI


if __name__ == "__main__":
    MutaGuiApp().run()
