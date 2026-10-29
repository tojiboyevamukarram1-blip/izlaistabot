from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.extractors.models import MediaMetadata, Platform
from bot.locales import uz


def get_youtube_keyboard(meta: MediaMetadata) -> InlineKeyboardMarkup:
    """Builds inline keyboard for YouTube genuinely available qualities."""
    buttons = []
    row = []

    # Video formats
    video_formats = [f for f in meta.formats if not f.is_audio]
    for idx, fmt in enumerate(video_formats):
        size_str = f"({fmt.formatted_size})" if fmt.formatted_size else ""
        text = uz.BTN_VIDEO_FORMAT.format(resolution=fmt.resolution, size_label=size_str).strip()
        # Callback data format: dl:<cache_key>:<format_idx>
        cb_data = f"dl:{meta.cache_key}:v_{idx}"
        row.append(InlineKeyboardButton(text=text, callback_data=cb_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Audio formats
    audio_formats = [f for f in meta.formats if f.is_audio]
    audio_row = []
    for idx, fmt in enumerate(audio_formats):
        size_str = f"({fmt.formatted_size})" if fmt.formatted_size else ""
        if "mp3" in fmt.resolution.lower():
            text = uz.BTN_AUDIO_MP3.format(size_label=size_str).strip()
        else:
            text = uz.BTN_AUDIO_ORIGINAL.format(size_label=size_str).strip()
        cb_data = f"dl:{meta.cache_key}:a_{idx}"
        audio_row.append(InlineKeyboardButton(text=text, callback_data=cb_data))

    if audio_row:
        buttons.append(audio_row)

    # Cancel button
    buttons.append([InlineKeyboardButton(text=uz.BTN_CANCEL, callback_data="cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pinterest_keyboard(meta: MediaMetadata, is_video: bool = False) -> InlineKeyboardMarkup:
    """Builds inline keyboard for Pinterest options."""
    buttons = []
    if is_video:
        buttons.append([
            InlineKeyboardButton(
                text=uz.BTN_PINTEREST_VIDEO,
                callback_data=f"dl:{meta.cache_key}:pin_vid",
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text=uz.BTN_PINTEREST_PHOTO,
                callback_data=f"dl:{meta.cache_key}:pin_photo",
            ),
            InlineKeyboardButton(
                text=uz.BTN_PINTEREST_DOC,
                callback_data=f"dl:{meta.cache_key}:pin_doc",
            ),
        ])

    buttons.append([InlineKeyboardButton(text=uz.BTN_CANCEL, callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_instagram_keyboard(meta: MediaMetadata) -> InlineKeyboardMarkup:
    """Builds inline keyboard for Instagram."""
    buttons = []
    if meta.is_carousel:
        count = len(meta.items)
        buttons.append([
            InlineKeyboardButton(
                text=uz.BTN_INSTAGRAM_CAROUSEL.format(count=count),
                callback_data=f"dl:{meta.cache_key}:ig_carousel",
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text=uz.BTN_INSTAGRAM_VIDEO,
                callback_data=f"dl:{meta.cache_key}:ig_vid",
            )
        ])

    buttons.append([InlineKeyboardButton(text=uz.BTN_CANCEL, callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
