"""
Kivy widget styles overrides.
Provides a template string which extends the existing styles.
Info on style customisation:
https://kivy.org/doc/stable/api-kivy.lang.html#template-example
https://kivy.org/doc/stable/api-kivy.lang.html#kivy.lang.BuilderBase.load_string
"""

file_chooser_file_icon_entry_styles = """
[FileIconEntry@Widget]:
    locked: False
    path: ctx.path
    selected: self.path in ctx.controller().selection
    size_hint: None, None

    on_touch_down: self.collide_point(*args[1].pos) and \
        ctx.controller().entry_touched(self, args[1])
    on_touch_up: self.collide_point(*args[1].pos) and \
        ctx.controller().entry_released(self, args[1])
    size: '150dp', '150dp'

    canvas:
        Color:
            rgba: 0.7, 0.7, 0.7, 1 if self.selected else 0
        BorderImage:
            border: 8, 8, 8, 8
            pos: root.pos
            size: root.size
            source: 'atlas://data/images/defaulttheme/filechooser_selected'

    Image:
        size: '48dp', '48dp'
        source: 'assets/folder-img.png'
        pos: root.x + dp(50), root.y + dp(60)
    Label:
        text: ctx.name
        font_name: ctx.controller().font_name
        text_size: (root.width, self.height)
        halign: 'center'
        shorten: True
        size: '140dp', '16dp'
        pos: root.x + dp(4), root.y + dp(16)
    Label:
        text: '{}'.format(ctx.get_nice_size())
        font_name: ctx.controller().font_name
        font_size: '11sp'
        color: .8, .8, .8, 1
        size: '100dp', '16sp'
        pos: root.x + dp(22), root.y
        halign: 'center'
"""
