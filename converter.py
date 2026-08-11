import html

def extract_and_format_custom_emojis(text: str, entities: list) -> tuple[str, bool]:
    """
    Telegram ke UTF-16 offset handling ke saath text/caption 
    se custom emojis extract aur HTML format mein convert karta hai.
    """
    if not text or not entities:
        return text or "", False

    # Filter custom_emoji entities
    custom_emoji_entities = [e for e in entities if getattr(e, 'type', None) == 'custom_emoji']
    if not custom_emoji_entities:
        return text, False

    # Offset ke accoding sort karo
    custom_emoji_entities.sort(key=lambda x: x.offset)

    # Convert text into UTF-16-LE bytes to handle Telegram UTF-16 offsets
    text_utf16 = text.encode('utf-16-le')
    result_parts = []
    last_end = 0

    for ent in custom_emoji_entities:
        start_byte = ent.offset * 2
        end_byte = (ent.offset + ent.length) * 2

        # Text chunk before entity
        if start_byte > last_end:
            before_text = text_utf16[last_end:start_byte].decode('utf-16-le')
            result_parts.append(html.escape(before_text))

        # Extract emoji character & custom_emoji_id
        emoji_char = text_utf16[start_byte:end_byte].decode('utf-16-le')
        emoji_id = getattr(ent, 'custom_emoji_id', '')

        # Tg-emoji format construct karo
        result_parts.append(f'<tg-emoji emoji-id="{emoji_id}">{emoji_char}</tg-emoji>')

        last_end = end_byte

    # Remaining text after the last entity
    if last_end < len(text_utf16):
        after_text = text_utf16[last_end:].decode('utf-16-le')
        result_parts.append(html.escape(after_text))

    return "".join(result_parts), True


def generate_code_snippet(html_text: str, format_type: str) -> str:
    """
    Selected format type ke base par clean, copyable code generator function.
    """
    if format_type == "php":
        escaped_text = html_text.replace('"', '\\"')
        return (
            "```php\n"
            "<?php\n\n"
            f'$text = "{escaped_text}";\n\n'
            "$data = [\n"
            "    'chat_id' => $chat_id,\n"
            "    'text' => $text,\n"
            "    'parse_mode' => 'HTML'\n"
            "];\n\n"
            'file_get_contents("https://api.telegram.org/bot<TOKEN>/sendMessage?" . http_build_query($data));\n'
            "```"
        )
    elif format_type == "python":
        escaped_text = html_text.replace("'", "\\'")
        return (
            "```python\n"
            f"text = '{escaped_text}'\n\n"
            "bot.send_message(\n"
            "    chat_id=chat_id,\n"
            "    text=text,\n"
            "    parse_mode='HTML'\n"
            ")\n"
            "```"
        )
    elif format_type == "markdown":
        return (
            "```html\n"
            f"{html_text}\n"
            "```"
        )
    elif format_type == "aiogram":
        return (
            "```python\n"
            "from aiogram.enums import ParseMode\n\n"
            f"text = '{html_text}'\n\n"
            "await message.answer(\n"
            "    text,\n"
            "    parse_mode=ParseMode.HTML,\n"
            ")\n"
            "```"
        )
    return html_text
