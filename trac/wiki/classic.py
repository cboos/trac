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
from .parser import WikiDescriptionItem, WikiInline, WikiItem, WikiRow


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
            item = WikiItem(i, j)
            item.kind = match.group('trac_bullet')
            item.k = k
            return item
        yield build_ulist_item

        @wiki_regexp(r' *\|\|')
        def build_row(wikidoc, wikinodes, i, match):
            k = match.end(0)
            j = k - 2
            row = WikiRow(i, j)
            row.k = k
            return row
        yield build_row


    def get_wiki_verbatim_sensitive_line_patterns(self):
        """Detect the following WikiFormatting:
            - `` term :: description``
        """

        @wiki_regexp(r' +(?P<trac_term>(?:[^:]|:[^:])+)::(?: |$)')
        def build_dl(wikidoc, wikinodes, i, match):
            j, k = match.span('trac_term')
            desc = WikiDescriptionItem(i, j)
            desc.k = k
            #desc.term = WikiInline(i, j)
            #desc.term.k = k
            # No, rather set a continuation function:
            # desc.postprocess = postprocess_dl
            return desc
        yield build_dl
