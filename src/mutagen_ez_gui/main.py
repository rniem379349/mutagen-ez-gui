import io

import mutagen
from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from metadata_setters import ID3MetadataSetter, MP4MetadataSetter, VorbisMetadataSetter
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.mp4 import MP4
from mutagen.wave import WAVE, _WaveID3
from PIL import Image
from styles import file_chooser_file_icon_entry_styles

# Load custom styles
Builder.load_string(file_chooser_file_icon_entry_styles)


class BaseMutagenMetadataInputGroup:
    metadata_key = ""
    selection = []
    cover_selection = []
    is_cover = False

    def __init__(self, metadata_key, **kwargs):
        self.metadata_display_panel = kwargs.pop("metadata_display_panel", None)
        super().__init__(**kwargs)

    def set_metadata(self, custom_selection=None):
        """
        Try to open the selected files with mutagen,
        guess their type and set the tag using the appropriate metadata setter.
        """
        print("custom? ", custom_selection)
        print("original? ", self.selection)
        for filepath in custom_selection or self.selection:
            print("setting for ", filepath)
            try:
                filething = mutagen.File(filepath)
                if isinstance(filething, WAVE):
                    if filething.tags is None:
                        filething.add_tags()
                    metadata_setter = ID3MetadataSetter(
                        filething, filepath, self.metadata_key
                    )
                elif isinstance(filething, MP4):
                    metadata_setter = MP4MetadataSetter(
                        filething, filepath, self.metadata_key
                    )
                elif isinstance(
                    filething.tags,
                    (
                        mutagen.oggvorbis.OggVCommentDict,
                        mutagen.oggopus.OggOpusVComment,
                        mutagen.flac.VCFLACDict,
                    ),
                ):
                    metadata_setter = VorbisMetadataSetter(
                        filething, filepath, self.metadata_key
                    )
                elif isinstance(filething, MP3) or filething.tags is None:
                    try:
                        filething = ID3(filepath)
                    except ID3NoHeaderError:
                        filething = ID3()
                    metadata_setter = ID3MetadataSetter(
                        filething, filepath, self.metadata_key
                    )
            except Exception as exc:
                print("Couldn't open file {}, exception: {}".format(filepath, exc))
                continue
            tag_value = self.get_value_to_save_in_tag()
            if self.metadata_key == "cover":
                metadata_setter.set_cover(tag_value)
            else:
                metadata_setter.set_tag(tag_value)
            metadata_setter.save_tags_to_file()
        if self.metadata_display_panel and len(self.selection) == 1:
            self.metadata_display_panel.set_metadata_labels(self.selection[0])

    def get_value_to_save_in_tag(self):
        raise NotImplementedError(
            "override this method to return the value to be saved to a tag "
            "(e.g. text/image data)."
        )


class MutagenMetadataInputGroup(BaseMutagenMetadataInputGroup, BoxLayout):
    """
    Widget for setting a particular metadata tag.
    Contains a text input for the metadata, and a button to set the tag.
    Needs a metadata tag key, and a list of files to open and add metadata to.
    Can be supplied a reference to the display panel to instantly
    reflect metadata changes when setting tags.
    """

    def __init__(self, metadata_key, **kwargs):
        super().__init__(metadata_key, **kwargs)
        self.orientation = "horizontal"
        self.metadata_key = metadata_key
        self.metadata_input = TextInput()
        self.apply_button = Button(
            halign="center",
            padding=(5, 5),
            text="Set {}".format(metadata_key.capitalize().replace("_", " ")),
            text_size=(120, None),
            size_hint_x=None,
            width=120,
        )
        self.apply_button.on_press = self.set_metadata
        self.add_widget(self.metadata_input)
        self.add_widget(self.apply_button)

    def get_value_to_save_in_tag(self):
        return self.metadata_input.text


class FileExplorer(FileChooserIconView):
    """File explorer widget, linked to metadata display"""

    def __init__(self, input_groups, metadata_display, file_selection_label, **kwargs):
        super().__init__(**kwargs)
        self.input_groups = input_groups
        self.metadata_display = metadata_display
        self.file_selection_label = file_selection_label
        self.multiselect = True

    def on_selection(self, instance, value):
        """
        callback which runs on selecting/deselecting a file in the explorer
        """
        filenames = [path.split("/")[-1] for path in value]
        self.file_selection_label.text = f"Selected: {', '.join(filenames)}"
        for input_group in self.input_groups:
            input_group.selection = value
        # Display metadata info only when one file is selected
        if len(value) == 1:
            self.metadata_display.set_metadata_labels(value[0])
        else:
            self.metadata_display.clear_metadata_labels()


class ArtCoverExplorer(FileChooserIconView, BaseMutagenMetadataInputGroup):
    """Art cover explorer widget, used to select a picture to set as an album cover"""

    metadata_key = "cover"

    def __init__(self, music_file_explorer, **kwargs):
        super().__init__(**kwargs)
        self.music_file_explorer = music_file_explorer
        self.raw_cover_data = b""

    def get_value_to_save_in_tag(self):
        return self.raw_cover_data

    def convert_to_jpeg(self, image):
        pass

    def get_raw_cover_data(self, picture):
        # picture = picture[0]
        byteIO = io.BytesIO()
        print("picture path: ", picture)
        thumb = Image.open(picture)
        thumb.thumbnail((400, 400), Image.Resampling.LANCZOS)
        thumb.save(byteIO, format="JPEG")
        byteimage = byteIO.getvalue()

        return byteimage

    def on_selection(self, instance, value):
        """
        callback which runs on selecting/deselecting a file in the explorer
        """
        try:
            self.raw_cover_data = self.get_raw_cover_data(value[0])
            print(
                "selection: ",
                self.music_file_explorer.selection,
                "setting pic: ",
                self.raw_cover_data[:10],
            )
            self.set_metadata(custom_selection=self.music_file_explorer.selection)
        except IndexError:
            print(f"cannot parse selection: {value} - aborting cover setting")


class BorderedBox:
    """
    Class to add to widget to give it a border box.
    Border is added in the .kv file
    """

    pass


class MetadataDisplayRow(BorderedBox, BoxLayout):
    def __init__(self, metadata_key, **kwargs) -> None:
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.metadata_key = metadata_key
        self.key_label = Label()
        self.key_label.halign = "left"
        self.key_label.valign = "middle"
        self.key_label.text = metadata_key.capitalize().replace("_", " ")
        self.value_label = Label(
            text_size=(180, None),
            halign="center",
            valign="middle",
        )
        self.add_widget(self.key_label)
        self.add_widget(self.value_label)


class FileSelectionLabel(BorderedBox, Label):
    """
    Label which lists the currently selected files.
    Useful when unable to see full file name in file chooser.
    Styled in .kv file.
    """

    pass


class MetadataDisplayPanel(GridLayout):
    metadata_keys = ("artist", "album", "title", "date", "tracknumber")
    metadata_widgets = dict()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rows = 5
        self.cols = 1
        self.padding = (0, 10)

        for key in self.metadata_keys:
            display_widget = MetadataDisplayRow(key)
            self.metadata_widgets[key] = display_widget
            self.add_widget(display_widget)

    def get_metadata(self, filepath):
        try:
            filething = mutagen.File(filepath, easy=True)
            # edge case:
            # _WaveID3 doesn't seem to implement the mutagen easy tag functionality
            if isinstance(filething.tags, _WaveID3):
                artist = ", ".join(
                    getattr(filething.get("TPE1", None), "text", ["Unknown"])
                )
                album = ", ".join(
                    getattr(filething.get("TALB", None), "text", ["Unknown"])
                )
                title = ", ".join(
                    getattr(filething.get("TIT2", None), "text", ["Unknown"])
                )
                date_stringified = [
                    str(timestamp)
                    for timestamp in getattr(
                        filething.get("TDRC", None), "text", ["Unknown"]
                    )
                ]
                date = ", ".join(date_stringified)
                tracknumber = ", ".join(
                    getattr(filething.get("TRCK", None), "text", ["Unknown"])
                )
            else:
                artist = filething.get("artist", "Unknown")
                album = filething.get("album", "Unknown")
                title = filething.get("title", "Unknown")
                date = filething.get("date", "Unknown")
                tracknumber = filething.get("tracknumber", "Unknown")
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
        for key in self.metadata_keys:
            value = tags[key]
            if isinstance(value, list):
                value = ", ".join(value)
            self.metadata_widgets[key].value_label.text = value

    def clear_metadata_labels(self):
        for key in self.metadata_keys:
            self.metadata_widgets[key].value_label.text = ""


class AlbumCoverSetterWindow(Popup):
    title = "Test popup"
    close_button = Button(text="Close", size_hint_y=None, height=50)
    anchor_x = "center"
    anchor_y = "center"
    auto_dismiss = False

    def __init__(self, music_file_explorer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.close_button.on_release = self.dismiss
        root = BoxLayout()
        root.orientation = "vertical"
        root.size = self.size
        chooser = ArtCoverExplorer(
            metadata_key="cover", music_file_explorer=music_file_explorer
        )
        root.add_widget(chooser)
        root.add_widget(self.close_button)
        self.add_widget(root)


class MutaEZGUIMain(BoxLayout):
    """
    Main app window.
    This class builds the structure of the widgets that comprise the app.
    In essence, the structure is as follows:
        - The left half of the window consists of an input panel
          for setting metadata tags, and a metadata display panel below;
        - The right half of the window contains the file explorer widget
          for choosing files to edit.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        # panel for setting and displaying metadata
        self.metadata_panel = GridLayout(
            cols=1,
            rows=8,
        )
        # input groups
        self.metadata_display_panel = MetadataDisplayPanel(size_hint_y=None, height=240)
        self.artist_input_group = MutagenMetadataInputGroup(
            "artist",
            metadata_display_panel=self.metadata_display_panel,
            size_hint_y=None,
            height=50,
        )
        self.album_input_group = MutagenMetadataInputGroup(
            "album",
            metadata_display_panel=self.metadata_display_panel,
            size_hint_y=None,
            height=50,
        )
        self.title_input_group = MutagenMetadataInputGroup(
            "title",
            metadata_display_panel=self.metadata_display_panel,
            size_hint_y=None,
            height=50,
        )
        self.track_number_input_group = MutagenMetadataInputGroup(
            "track_number",
            metadata_display_panel=self.metadata_display_panel,
            size_hint_y=None,
            height=50,
        )
        self.recording_year_input_group = MutagenMetadataInputGroup(
            "recording_year",
            metadata_display_panel=self.metadata_display_panel,
            size_hint_y=None,
            height=50,
        )
        self.file_selection_label = FileSelectionLabel()

        self.chooser = FileExplorer(
            input_groups=[
                self.artist_input_group,
                self.album_input_group,
                self.title_input_group,
                self.track_number_input_group,
                self.recording_year_input_group,
            ],
            metadata_display=self.metadata_display_panel,
            file_selection_label=self.file_selection_label,
        )
        self.album_cover_setter_popup = AlbumCoverSetterWindow(
            music_file_explorer=self.chooser
        )
        self.album_cover_setter_button = Button(
            text="Set Cover", height=50, size_hint_y=None
        )
        self.album_cover_setter_button.bind(on_press=self.album_cover_setter_popup.open)
        self.album_cover_setter_popup.close_button.bind(
            on_press=self.album_cover_setter_popup.dismiss
        )

        self.metadata_panel.add_widget(self.artist_input_group)
        self.metadata_panel.add_widget(self.album_input_group)
        self.metadata_panel.add_widget(self.title_input_group)
        self.metadata_panel.add_widget(self.track_number_input_group)
        self.metadata_panel.add_widget(self.recording_year_input_group)
        self.metadata_panel.add_widget(self.album_cover_setter_button)
        self.metadata_panel.add_widget(self.file_selection_label)
        self.metadata_panel.add_widget(self.metadata_display_panel)

        self.add_widget(self.metadata_panel)
        self.add_widget(self.chooser)


class MutaGUIApp(App):
    """Mutagen GUI Kivy app object."""

    def build(self):
        Window.size = (1000, 580)
        MutaGUI = MutaEZGUIMain()
        return MutaGUI


if __name__ == "__main__":
    MutaGUIApp().run()
