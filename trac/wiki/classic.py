# -*- coding: utf-8 -*-
#
# Copyright (C) 2013 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.

from ..core import *
from .api import IWikiBlockSyntaxProvider, wiki_regexp
from .parser import *

class TracWikiSyntax(Component):
    """Parser for the classic Trac WikiFormatting syntax, originally
    inspired by the MoinMoin wiki.

    When used alone, should be pretty compatible with Trac 0.12 syntax
    (pre-WikiCreole). It can of course be used together with the other
    syntax elements.
    """

    implements(IWikiBlockSyntaxProvider)

    # IWikiBlockSyntaxProvider methods

    def get_wiki_line_patterns(self):
        """Detect the following WikiFormatting:
            - `` - items``
            - `` || rows ||``
        """

        @wiki_regexp(r' +(?P<trac_bullet>[-*])(?: |$)')
        def build_ulist_item(wikidoc, wikinodes, i, match):
            j, k = match.span('trac_bullet')
            item = WikiItem(i, j, k)
            item.kind = match.group('trac_bullet')
            item.nodes = [WikiInline(i, k + 1)]
            return item
        yield build_ulist_item

        @wiki_regexp(r' *\|\|')
        def build_row(wikidoc, wikinodes, i, match):
            k = match.end(0)
            j = k - 2
            row = WikiRow(i, j, k)
            row.nodes = [WikiInline(i, k)]
            return row
        yield build_row

        @wiki_regexp(r'(?P<trac_sec_depth>={1,6}) '  ### verbose
                     r'(?P<trac_sec>.*?)'
                     r'(?P<trac_sec_anchor>#%s)? *$' % WikiParser.XML_NAME)
        def build_section(wikidoc, wikinodes, i, match):
            j = wikinodes[-1].j
            depth = match.group('trac_sec_depth')
            heading = match.group('trac_sec')
            anchor = match.group('trac_sec_anchor')
            both_sides = heading.endswith(depth)
            depth = len(depth)
            k = j + depth + 1
            section = WikiSection(i, j, k)
            section.depth = depth
            j = k
            k = match.end('trac_sec')
            if both_sides:
                k -= depth
                section.both_sides = True
            if anchor:
                section.anchor = anchor[1:]
            section.nodes = [WikiInline(i, j, k)]
            return section
        yield build_section

        @wiki_regexp(r' *-{4,} *$')
        def build_rule(wikidoc, wikinodes, i, match):
            j = wikinodes[-1].j
            j = wikidoc.lines[i].find('-', j)
            k = wikidoc.lines[i].rfind('-')
            return WikiRule(i, j, k)
        yield build_rule


    def get_wiki_verbatim_sensitive_line_patterns(self):
        """Detect the following WikiFormatting:
            - `` term :: description``
        """

        @wiki_regexp(r' +(?P<trac_term>(?:[^:]|:[^:])+)::(?: |$)')
        def build_dl(wikidoc, wikinodes, i, match):
            j, k = match.span('trac_term')
            desc = WikiDescriptionItem(i, k, k + 2)
            desc.term = WikiInline(i, j, k)
            desc.nodes = [WikiInline(i, k + 2)]
            # No, rather set a continuation function:
            # desc.postprocess = postprocess_dl
            return desc
        yield build_dl
