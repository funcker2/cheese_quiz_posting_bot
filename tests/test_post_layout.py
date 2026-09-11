from post_layout import CaptionMode, plan_post_layout, split_preview_notice, utf16_len


def test_utf16_len_counts_emoji_as_telegram_does() -> None:
    # 🏆 is U+1F3C6 → one Python char, two UTF-16 code units
    assert utf16_len("🏆") == 2
    assert utf16_len("a") == 1


def test_single_photo_short_text_glues_caption_and_button_on_photo() -> None:
    layout = plan_post_layout(n_photos=1, text="hello", has_button=True)
    assert layout.caption_mode is CaptionMode.GLUE
    assert layout.button_on == "media"


def test_single_photo_short_text_no_button() -> None:
    layout = plan_post_layout(n_photos=1, text="hello", has_button=False)
    assert layout.caption_mode is CaptionMode.GLUE
    assert layout.button_on == "none"


def test_single_photo_exactly_1024_still_glues() -> None:
    text = "a" * 1024
    layout = plan_post_layout(n_photos=1, text=text, has_button=True)
    assert utf16_len(text) == 1024
    assert layout.caption_mode is CaptionMode.GLUE
    assert layout.button_on == "media"


def test_single_photo_long_text_splits_and_puts_button_on_text() -> None:
    text = "a" * 1025
    layout = plan_post_layout(n_photos=1, text=text, has_button=True)
    assert layout.caption_mode is CaptionMode.SPLIT
    assert layout.button_on == "text"


def test_single_photo_long_text_without_button_still_splits() -> None:
    text = "a" * 1025
    layout = plan_post_layout(n_photos=1, text=text, has_button=False)
    assert layout.caption_mode is CaptionMode.SPLIT
    assert layout.button_on == "none"


def test_emoji_pushes_1024_python_chars_over_caption_limit() -> None:
    # 1023 ASCII + one non-BMP emoji = 1024 Python chars, 1025 UTF-16
    text = ("a" * 1023) + "🏆"
    assert len(text) == 1024
    assert utf16_len(text) == 1025
    layout = plan_post_layout(n_photos=1, text=text, has_button=True)
    assert layout.caption_mode is CaptionMode.SPLIT
    assert layout.button_on == "text"


def test_two_photos_short_text_glues_album_caption_button_as_followup() -> None:
    layout = plan_post_layout(n_photos=2, text="hello", has_button=True)
    assert layout.caption_mode is CaptionMode.GLUE
    assert layout.button_on == "followup"


def test_two_photos_short_text_no_button() -> None:
    layout = plan_post_layout(n_photos=2, text="hello", has_button=False)
    assert layout.caption_mode is CaptionMode.GLUE
    assert layout.button_on == "none"


def test_two_photos_long_text_splits_and_puts_button_on_text() -> None:
    layout = plan_post_layout(n_photos=2, text="b" * 1025, has_button=True)
    assert layout.caption_mode is CaptionMode.SPLIT
    assert layout.button_on == "text"


def test_recap_from_hang_must_split() -> None:
    text = (
        "Друзья, всем солнечный! ☀️\n\n"
        "После хорошего летнего отдыха, мы начали новый сезон Осень-Зима 26–27. "
        "И первой игрой была выбрана BACK to SCHOOL.\n\n"
        "Вечер получился легким и веселым. Вашей партой были бланки, а физика и химия "
        "заставляли немножечко поскрипеть извилинами.\n\n"
        "1️⃣ А'СИСИКЕМБЭЛ шли уверенно весь вечер и не отдавали первую строчку: "
        "мощный второй раунд на логике сразу задал темп, а огромные 20 баллов "
        "в финальном раунде превратили преимущество в уверенную победу.\n\n"
        "2️⃣ ЛЮБИТЕЛИ ЭТОГО ДЕЛА весь вечер держались рядом с лидерами, и на "
        "синемузыке в третьем раунде сделали важный рывок. Ровная игра без провалов "
        "и отличная финальная концовка принесли команде серебро.\n\n"
        "3️⃣ FAQ — стабильность весь вечер, ни одного слабого раунда. До последнего "
        "дышали в спину серебру, и битва за второе-третье место получилась одной из "
        "самых плотных за вечер: команды разделили меньше шести баллов.\n\n"
        "Спасибо всем, кто пришёл в этот вечер — за азарт, за атмосферу и за то, "
        "что соскучились и сопереживали. ❤️ До встречи на следующем квизе в четверг 🏆"
    )
    assert utf16_len(text) > 1024
    layout = plan_post_layout(n_photos=1, text=text, has_button=True)
    assert layout.caption_mode is CaptionMode.SPLIT
    assert layout.button_on == "text"
    notice = split_preview_notice(text)
    over = utf16_len(text) - 1024
    assert notice is not None
    assert str(over) in notice
    assert "двумя сообщениями" in notice
    assert "склеить" in notice


def test_no_split_notice_when_caption_fits() -> None:
    assert split_preview_notice("hello") is None
    assert split_preview_notice("a" * 1024) is None


def test_split_notice_uses_russian_plural_for_overflow() -> None:
    assert "1 символ" in split_preview_notice("a" * 1025)
    assert "2 символа" in split_preview_notice("a" * 1026)
    assert "7 символов" in split_preview_notice("a" * 1031)
    assert "11 символов" in split_preview_notice("a" * 1035)
    assert "21 символ" in split_preview_notice("a" * 1045)
