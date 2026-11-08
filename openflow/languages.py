"""All 100 language codes exposed by the bundled Whisper engine."""
LANGUAGES: dict[str, str] = {
    "af": "Afrikaans", "am": "Amharic · አማርኛ", "ar": "Arabic · العربية",
    "as": "Assamese · অসমীয়া", "az": "Azerbaijani · Azərbaycan", "ba": "Bashkir",
    "be": "Belarusian · Беларуская", "bg": "Bulgarian · Български",
    "bn": "Bengali · বাংলা", "bo": "Tibetan · བོད་སྐད", "br": "Breton",
    "bs": "Bosnian · Bosanski", "ca": "Catalan · Català", "cs": "Czech · Čeština",
    "cy": "Welsh · Cymraeg", "da": "Danish · Dansk", "de": "German · Deutsch",
    "el": "Greek · Ελληνικά", "en": "English", "es": "Spanish · Español",
    "et": "Estonian · Eesti", "eu": "Basque · Euskara", "fa": "Persian · فارسی",
    "fi": "Finnish · Suomi", "fo": "Faroese · Føroyskt", "fr": "French · Français",
    "gl": "Galician · Galego", "gu": "Gujarati · ગુજરાતી", "ha": "Hausa",
    "haw": "Hawaiian · ʻŌlelo Hawaiʻi", "he": "Hebrew · עברית", "hi": "Hindi · हिन्दी",
    "hr": "Croatian · Hrvatski", "ht": "Haitian Creole", "hu": "Hungarian · Magyar",
    "hy": "Armenian · Հայերեն", "id": "Indonesian · Bahasa Indonesia",
    "is": "Icelandic · Íslenska", "it": "Italian · Italiano", "ja": "Japanese · 日本語",
    "jw": "Javanese · Basa Jawa", "ka": "Georgian · ქართული", "kk": "Kazakh · Қазақша",
    "km": "Khmer · ខ្មែរ", "kn": "Kannada · ಕನ್ನಡ", "ko": "Korean · 한국어",
    "la": "Latin", "lb": "Luxembourgish · Lëtzebuergesch", "ln": "Lingala",
    "lo": "Lao · ລາວ", "lt": "Lithuanian · Lietuvių", "lv": "Latvian · Latviešu",
    "mg": "Malagasy", "mi": "Māori", "mk": "Macedonian · Македонски",
    "ml": "Malayalam · മലയാളം", "mn": "Mongolian · Монгол", "mr": "Marathi · मराठी",
    "ms": "Malay · Bahasa Melayu", "mt": "Maltese · Malti", "my": "Burmese · မြန်မာ",
    "ne": "Nepali · नेपाली", "nl": "Dutch · Nederlands", "nn": "Norwegian Nynorsk",
    "no": "Norwegian · Norsk", "oc": "Occitan", "pa": "Punjabi · ਪੰਜਾਬੀ",
    "pl": "Polish · Polski", "ps": "Pashto · پښتو", "pt": "Portuguese · Português",
    "ro": "Romanian · Română", "ru": "Russian · Русский", "sa": "Sanskrit · संस्कृतम्",
    "sd": "Sindhi · سنڌي", "si": "Sinhala · සිංහල", "sk": "Slovak · Slovenčina",
    "sl": "Slovenian · Slovenščina", "sn": "Shona", "so": "Somali · Soomaali",
    "sq": "Albanian · Shqip", "sr": "Serbian · Српски", "su": "Sundanese · Basa Sunda",
    "sv": "Swedish · Svenska", "sw": "Swahili · Kiswahili", "ta": "Tamil · தமிழ்",
    "te": "Telugu · తెలుగు", "tg": "Tajik · Тоҷикӣ", "th": "Thai · ไทย",
    "tk": "Turkmen · Türkmençe", "tl": "Tagalog / Filipino", "tr": "Turkish · Türkçe",
    "tt": "Tatar · Татарча", "uk": "Ukrainian · Українська", "ur": "Urdu · اردو",
    "uz": "Uzbek · Oʻzbekcha", "vi": "Vietnamese · Tiếng Việt", "yi": "Yiddish · ייִדיש",
    "yo": "Yoruba · Yorùbá", "yue": "Cantonese · 廣東話", "zh": "Chinese · 中文",
}
LANGUAGE_CODES = frozenset(LANGUAGES)


def language_name(code: str) -> str:
    return "Auto-detect" if code == "auto" else LANGUAGES.get(code, code or "Unknown")
