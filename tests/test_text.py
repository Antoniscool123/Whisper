from openflow.text import parse_dictionary, tidy_text, word_count


def test_danish_hesitations_and_capitalization():
    assert tidy_text("øh jeg vil gerne have en kaffe øhm tak") == "Jeg vil gerne have en kaffe tak"
    assert tidy_text("Hej, øh, hvordan har du det?") == "Hej, hvordan har du det?"
    assert tidy_text("æbler og øl er godt. øh vi ses") == "Æbler og øl er godt. Vi ses"


def test_does_not_remove_meaningful_words():
    assert tidy_text("Jeg kan faktisk godt lide ligesom dig") == "Jeg kan faktisk godt lide ligesom dig"
    assert tidy_text("The minimum number is rum") == "The minimum number is rum"


def test_commands_are_opt_in():
    source = "Hej komma nyt afsnit hvordan har du det spørgsmålstegn"
    assert "komma" in tidy_text(source, commands=False)
    assert tidy_text(source, commands=False, fillers=False) == "Hej komma nyt afsnit hvordan har du det spørgsmålstegn"
    assert tidy_text(source, commands=True) == "Hej,\n\nHvordan har du det?"


def test_dictionary_unicode_and_no_chaining():
    rules = "aarhus => Aarhus\nanton => Anton\nopen flow => OpenFlow"
    assert tidy_text("jeg bor i aarhus med anton", dictionary=rules) == "Jeg bor i Aarhus med Anton"
    assert tidy_text("open flow", dictionary="open flow => OpenFlow\nOpenFlow => Nope") == "OpenFlow"
    assert tidy_text("OPEN FLOW", dictionary="open flow => OpenFlow") == "OPENFLOW"


def test_dictionary_validation():
    rules, invalid = parse_dictionary("# comment\n\nhello => world\nbad line\nx =>\nhello => duplicate")
    assert len(rules) == 1 and invalid == [4, 5, 6]


def test_word_count_and_whitespace():
    assert word_count("Hej, verden! Æble øl å.") == 5
    assert tidy_text("  hej   verden  ") == "Hej verden"
    assert tidy_text("") == ""
