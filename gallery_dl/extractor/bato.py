# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://bato.to and aliases (v3x only)"""

from .common import ChapterExtractor, MangaExtractor
from .. import text, exception
import re

BASE_PATTERN = r"(?:https?://)?" \
    r"(?:bato\.to|dto\.to|batotoo\.com|wto\.to|mangatoto\.com)"
MANGA_PATTERN = r"/title/\d+(?:-[0-9a-z]+)*/?"
CHAPTER_PATTERN = r"/\d+(?:-vol_\d+)?-ch_\d+\.?\d*/?"


class BatoBase():
    """Base class for bato v3x extractors"""
    category = "bato"
    root = "https://bato.to"


class BatoChapterExtractor(BatoBase, ChapterExtractor):
    """Extractor for manga chapters from bato.to"""
    pattern = BASE_PATTERN + "(" + MANGA_PATTERN + CHAPTER_PATTERN + ")"
    # There are three possible patterns for a chapter
    example = "https://bato.to/title/12345-manga-name-with-spaces/54212-ch_1.5"
    example2 = \
        "https://bato.to/title/12345-manga-name-with-spaces/54212-vol1-ch_1.5"
    example3 = "https://bato.to/title/12345/54212"
    # v2x, not supported
    example4 = "https://bato.to/chapter/54212"

    def __init__(self, match):
        self.path = match.group(1)
        ChapterExtractor.__init__(self, match, self.root + self.path)

    def metadata(self, page):
        info = text.extr(
            page, "<title>", r" - Read Free Manga Online at Bato.To</title>"
        )
        info = info.encode('latin-1').decode('utf-8').replace("\n", "")

        match = re.match(
            r"(.+) - "
            r"(?:Volume *(\d+) )?"
            r"Chapter *([\d\.]+)", info)
        manga, volume, chapter = match.groups() if match else ("", "", info)
        chapter, sep, minor = chapter.partition(".")
        title_section = text.extr(page, '<a href="' + self.path + '"', "</a>")
        title = text.extr(title_section, "<!-- -->", "</span>")

        return {
            "manga"        : text.unescape(manga),
            "title"        : text.unescape(title),
            "author"       : "",
            "volume"       : text.parse_int(volume),
            "chapter"      : text.parse_int(chapter),
            "chapter_minor": sep + minor,
        }

    def images(self, page):
        images_container = text.extr(page, 'pageOpts', ':[0,0]}"')
        images_container = text.unescape(images_container)
        return [
            (url, None)
            for url in text.extract_iter(images_container, r"\"", r"\"")
        ]


class BatoMangaExtractor(BatoBase, MangaExtractor):
    """Extractor for manga from bato.to"""
    reverse = False
    chapterclass = BatoChapterExtractor
    pattern = BASE_PATTERN + "(" + MANGA_PATTERN + "$" + ")"
    # There are two possible patterns for a manga
    example = "https://bato.to/title/12345-manga-name-with-spaces/"
    example2 = "https://bato.to/title/12345/"
    # v2x, not supported
    example3 = "https://bato.to/series/12345/manga-name-with-space"

    def chapters(self, page):
        data = {}
        num_chapters = text.extr(page, ">Chapters<", "</div>")
        num_chapters = text.extr(num_chapters, r"<!-- -->", r"<!-- -->")
        num_chapters = text.parse_int(num_chapters)
        if num_chapters == 0:
            raise exception.NotFoundError("chapter")

        manga = text.extr(
            page, "<title>", r" - Read Free Manga Online at Bato.To</title>"
        )
        manga = manga.encode('latin-1').decode('utf-8').replace("\n", "")
        data["manga"] = manga

        results = []
        for chapter_num in range(num_chapters):
            chapter_info = text.extr(
                page,
                '<div data-hk="0-0-{}-0"'.format(chapter_num),
                r"</time><!--/-->"
            )
            chapter_info += r"</time><!--/-->"  # so we can match the date
            url, pos = text.extract(chapter_info, '<a href="', '"')

            chapter = re.search(r"-ch_([\d\.]+)", url)
            if chapter:
                chapt_major, sep, chapt_minor = chapter.group(1).partition(".")
            title = text.extr(
                chapter_info,
                '<span data-hk="0-0-{}-1"'.format(chapter_num),
                "</span>"
            )
            title = text.extr(title, r"<!--#-->", r"<!--/-->")
            if title is None or title == "" or title == "<!--/-->":
                title, _ = text.extract(chapter_info, ">", "</a>", pos)

            date = text.extr(chapter_info, "<time", "</time>")
            date = text.extr(date, 'time="', '"')

            data["date"] = date
            data["title"] = title
            data["chapter"] = text.parse_int(chapt_major)
            data["chapter_minor"] = sep + chapt_minor

            if url.startswith("/"):
                url = self.root + url
            results.append((url, data.copy()))
        return results
