import re
import os
import xmlreader

namespaces = set(['Media','Special','Talk','User','User talk','Wiktionary', 'Wiktionary talk', 'File', 'File talk', 'MediaWiki', 'MediaWiki talk', 'Template', 'Template talk', 'Help', 'Help talk', 'Category', 'Category talk', 'Appendix', 'Appendix talk', 'Concordance', 'Concordance talk', 'Index', 'Index talk', 'Rhymes', 'Rhymes talk', 'Transwiki', 'Transwiki talk', 'Wikisaurus', 'Wikisaurus talk', 'WT', 'WT talk', 'Citations', 'Citations talk'])

posses = set(['noun', 'noun phrase', 'noun form', 'verb', 'verb form', 'verb phrase', 'transitive verb', 'intransitive verb', 'adjective', 'adjective form', 'adjective phrase', 'adverb', 'adverb phrase', 'pronoun', 'conjunction', 'contraction', 'interjection', 'preposition', 'proper noun', 'article', 'prefix', 'verb prefix', 'suffix', 'infix', 'interfix', 'circumfix', 'affix', 'idiom', 'phrase', 'acronym', 'abbreviation', 'initialism', 'symbol', 'letter', 'number', 'numeral', 'ordinal number', 'ordinal numeral', 'cardinal number', 'cardinal numeral', 'particle', 'proverb', 'han character', 'kanji', 'hanzi', 'hanja', 'pinyin', 'pinyin syllable', 'syllable', 'katakana character', 'hiragana letter', 'hiragana character', 'counter', 'classifier', 'adnominal', 'determiner', 'expression', 'postposition', 'root', 'participle', '{{initialism}}', '{{acronym}}', '{{abbreviation}}', 'cmavo', 'gismu', 'predicative', 'gerund', 'jyutping syllable', 'lujvo', 'nominal suffix', 'indefinite pronoun', 'measure word', 'kanji reading', 'hiragana', 'romaji', 'verbal noun', 'ligature', 'correlative', 'pronomial adverb'])

for i in range(1,5):
    posses.add('noun %s' % i)
    posses.add('verb %s' % i)

re_language = re.compile(r"^(==\s*(?:\[\[\s*)?([^[=\s].*[^=\s\]])(?:\s*\]\])?\s*==)\s*$", re.M)

def is_part_of_speech(title):
    """
    Is it on our part-of-speech whitelist
    """
    if title:
        if title.lower() in posses or title.startswith('{{abbreviation') or title.startswith('{{initialism') or title.startswith('{{acronym'):
            return True

class Section(object):
    """
    Represents one language's section of a page.

    The text will include the heading
    """
    def __init__(self, heading, text):
        self.heading = heading
        self.text = text

    def __repr__(self):
        return '"""' + self.text + '"""'

def split_entry_trailer(text):
    """
    Split an entry into two parts, the bit with useful stuff, and the bit with categories, interwikis and ----

    rejoining the two gives the original entry
    """
    re_useless = re.compile(r"^ *(----|\[\[ *[Ca-z\-]* *:[^\]]*\]\]|\{\{count page[^\}]*\}\})? *$")
    useful = []
    useless = []
    for line in text.split("\n"):
        if re_useless.match(line):
            useless.append(line)
        else:
            useful += useless
            useful.append(line)
            useless = []

    return ("\n".join(useful) + "\n", "\n".join(useless))

class NotUniqueException(Exception):
    def __init__(self, lst):
        self.message = "More than one 'unique' section"
        self.lst = lst

def unique_section(heading, text):
    """
    Assume there is only one section with a given title on the page, and return it
    """
    base_re = r"^(=+\s*(?:\[\[\s*)?(?:%s)(?:\s*\]\])?\s*=+\s*)$" 
    re_this_heading = re.compile(base_re % heading, re.M)
    re_any_heading = re.compile(base_re % "[^[=\s].*[^=\s\]]", re.M)
    
    split = re_this_heading.split(text)
    if len(split) == 1:
        return Section(None, "")
    elif len(split) >3:
        raise NotUniqueException("More than one 'unique' section")
    else:
        splot = re_any_heading.split(split[2])
        if len(splot) == 1:
            return Section(heading, split[1] + split[2])
        else:
            return Section(heading, split[1] + splot[0])

def all_sections(heading, text):
    raise Exception("Please fix and document use")
    try:
        yield unique_section(heading, text)
    except NotUniqueException, e:
        base_re = r"^(=+\s*(?:\[\[\s*)?(?:%s)(?:\s*\]\])?\s*=+\s*)$" 
        re_any_heading = re.compile(base_re % "[^[=\s].*[^=\s\]]", re.M)
        split = e.lst
        for x in range(0,len(split),3):
            splot = re_any_heading.split(split[x+2])
            if len(splot) == 1:
                yield Section(heading, split[x+1] + split[x+2])
            else:
                yield Section(heading, split[x+1] + splot[x+0])

def all_subsections(text):
    """
        Get all the subsections of a language section (ignoring nesting)
    """
    re_any_heading = re.compile(r"^(=+\s*(?:\[\[\s*)?([^\[=\s].*[^=\s\]])(?:\s*\]\])?\s*=+\s*)$", re.M)
    split = re_any_heading.split(text)

    if len(split) == 1:
        yield Section(None, split[0])
    else:
        first = split.pop(0)
        split[0] = first + split[0]
        for x in range(1,len(split),3):
            yield Section(split[x], split[x-1] + split[x+1])

def all_headings(text, preserve_links=False):
    if preserve_links:
        base_re = r"^(=+\s*((?:\[\[\s*)?%s(?:\s*\]\])?)\s*=+\s*)$" 
    else:
        base_re = r"^(=+\s*(?:\[\[\s*)?(%s)(?:\s*\]\])?\s*=+\s*)$" 
    re_any_heading = re.compile(base_re % "[^[=\s].*[^=\s\]]", re.M)
    
    for m in re_any_heading.findall(text):
        yield m[1]

def language_sections(text):
    """
    Generate LanguageSections from an entry (really splits on == headings)

    If you join together the "text" of these you are guaranteed to re-assemble
    the original entry, anything before the first heading is lumped into the first heading.

    If the entry is unparsable, the language will be `None`
    """

    split = re_language.split(text)
    if len(split) == 1:
        yield Section(None, split[0])

    else:
        split[1] = split[0] + split[1]
        x = 1
        while x < len(split):
            yield Section(split[x+1], split[x] + split[x+2])
            x += 3

def filter_language(language, entry, editor):

    output = ""
    for section in language_sections(entry.text):
        if section.heading == language:
            output += editor(entry, section) or section.text
        else:
            output += section.text

    return output

def filter_heading(heading, entry, editor):
    raise Exception("Broken")

    output = ""
    for section in all_headings(entry):
        if section.heading == heading or section.heading.startswith(heading + " "):
            output += editor(section.text) or section.text
        else:
            otuput += section.text

    return output

def definition_lines(text):
    """
    Get all lines that look like definition lines
    """
    return [line for line in text.split("\n") if len(line) > 2 and line[0] == "#" and line[1] not in ":*#*"]

def latest_dump(offline=False, helper="./latest_dump.sh", __cache=[]):
    """
        Returns the path to the latest dump file according to `helper`
        This function is guaranteed to return the same path throughout the 
        lifetime of program execution.

        WARNING: This function may cause two HTTP requests, one to get the
        latest available version, and the other to download the dump itself.
    """
    if len(__cache):
        return __cache[0];

    if offline:
        stdin = os.popen(helper + " --offline")
        return stdin.read().strip()
    
    else:
        stdin = os.popen(helper)
        __cache.append(stdin.read().strip())
        return latest_dump()

def dump_entries(dump=None, namespace=None, main_only=False, offline=False):
    """
        Returns an iterator over every entry in the `dump`
        If the `dump` is not specified, `latest_dump()` is used.
    """
    if dump is None:
        dump = latest_dump(offline=offline)

    def do_main_only(namespaces):
        for entry in xmlreader.XmlDump(dump).parse():
            if not ":" in entry.title:
                yield entry
            elif not entry.title[:entry.title.find(":")] in namespaces:
                yield entry
    
    def do_namespace(namespace):
        for entry in xmlreader.XmlDump(dump).parse():
            if entry.title[:entry.title.find(":")] == namespace:
                yield entry

    if main_only == False and namespace != "":
        if namespace:
            return do_namespace(namespace)
        else:
            return xmlreader.XmlDump(dump).parse()
    else:
        return do_main_only(namespaces)

def talk_page(title):

    title = title.replace("_", " ")
    if title.startswith(":"):
        title = title[1:]

    parts = title.split(":", 1)

    if len(parts) == 1:
        return "Talk:" + parts[0]
    else:
        if parts[0] in namespaces:
            if parts[0].lower().endswith("talk"):
                return title
            else:
                return parts[0] + " talk" + ":" + parts[1]

        else:
            return "Talk:" + parts[0] + ":" + parts[1]
