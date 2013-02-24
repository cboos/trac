# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2009 Edgewall Software
# Copyright (C) 2003-2006 Jonas Borgström <jonas@edgewall.com>
# Copyright (C) 2004-2006 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2005-2007 Christian Boos <cboos@edgewall.org>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.
#
# Author: Jonas Borgström <jonas@edgewall.com>
#         Christopher Lenz <cmlenz@gmx.de>
#         Christian Boos <cboos@edgewall.org>

import re

from trac.core import *
from trac.notification import EMAIL_LOOKALIKE_PATTERN

# -- Wiki DOM

class WikiNode(object):
    """A node represents a syntax unit within the Wiki DOM.

    A node can also be seen as a "pointer" into a `WikiDocument`, as
    it usually doesn't store text by itself, but rather refers to the
    text stored in the document.  All nodes have a starting point in
    the document, line ``i`` and column ``j``.

    A node may have children ``nodes``.
    """
    nodes = None # no subnodes
    end = None   # not multiline
    k = -1       # eol

    def __init__(self, *args):
        self.i, self.j = args


class WikiBlock(WikiNode):
    """A block correspond to a multiline section delimited by a pair of
    matching triple curly braces (``{{{`` ... ``}}}``).

    The content of a block starts at line ``start`` and ends at line
    ``end - 1``::

           .j          B3<1-5>
           |
        ................................
        ...{{{.......................... .i
        ...Content starts here.......... .start
        ................................
        ...Content ends here............
        ...}}}.......................... .end
        ................................

    or::

           .j          B3<1+-5>diff
           |
        ................................
        ...{{{.......................... .i
        ...#!diff.......................
        ...Content starts here.......... .start
        ...Content ends here............
        ...}}}.......................... .end
        ................................

    If a block processor is specified (e.g. ``#!diff``), ``name``
    contains its name (here 'diff') and ``params`` is a dict with the
    processor's parameters.
    """
    def __init__(self, i, j, name=None, params=None):
        WikiNode.__init__(self, i, j)
        self.start = self.end = i + 1
        self.name = name or ''
        self.params = params or {}
        self.nodes = []
        self.comment = ''

    def __repr__(self):
        return 'B%d<%d%s-%d>%s%s' % (
            self.j, self.i, '+' * (self.start - self.i - 1), self.end,
            self.name or '', self.comment[:10])


class WikiDocument(WikiBlock):
    """A document corresponds to a wiki text in one unit of storage.

    At the same time, it behaves as a root `WikiBlock` spanning the
    whole content (``start == 0``, ``end == len(lines)``).
    """
    def __init__(self, text):
        WikiBlock.__init__(self, 0, 0)
        text = re.sub(WikiParser._normalize_re, ' ', text or '')
        self.lines = text.splitlines()
        self.start = 0
        self.end = len(self.lines)

    def __repr__(self):
        return 'WikiDocument (%d lines)' % len(self.lines)



class WikiParser(Component):
    """Wiki text parser."""

    # Pre-processing

    _normalize_re = re.compile(r'[\v\f]', re.UNICODE) # Python 2.7 compat

    # Some constants used for clarifying the Wiki regexps:

    BOLDITALIC_TOKEN = "'''''"
    BOLD_TOKEN = "'''"
    BOLD_TOKEN_WIKICREOLE = r"\*\*"
    ITALIC_TOKEN = "''"
    ITALIC_TOKEN_WIKICREOLE = "//"
    UNDERLINE_TOKEN = "__"
    STRIKE_TOKEN = "~~"
    SUBSCRIPT_TOKEN = ",,"
    SUPERSCRIPT_TOKEN = r"\^"
    INLINE_TOKEN = "`" # must be a single char (see P<definition> below)
    STARTBLOCK_TOKEN = r"\{\{\{"
    ENDBLOCK_TOKEN = r"\}\}\}"

    BULLET_CHARS = u"-*\u2022"

    LINK_SCHEME = r"[a-zA-Z][-a-zA-Z0-9+._]*" # as per RFC 2396 + '_'
    INTERTRAC_SCHEME = r"[a-zA-Z.+-]*?" # no digits (for shorthand links)

    QUOTED_STRING = r"'[^']+'|\"[^\"]+\""

    SHREF_TARGET_FIRST = r"[\w/?!#@](?<!_)" # we don't want "_"
    SHREF_TARGET_MIDDLE = r"(?:\|(?=[^|\s])|[^|<>\s])"
    SHREF_TARGET_LAST = r"[\w/=](?<!_)" # we don't want "_"

    # -- WikiBlocks

    STARTBLOCK = "{{{"
    ENDBLOCK = "}}}"

    PROCESSOR = r"(\s*)#\!([\w+-][\w+-/]*)"

    PROCESSOR_PARAM = r'''(?P<proc_pname>\w+)=(?P<proc_pval>".*?"|'.*?'|\w+)'''


    def _lhref_relative_target(sep):
        return r"[/\?#][^%s\]]*|\.\.?(?:[/\?#][^%s\]]*)?" % (sep, sep)

    LHREF_RELATIVE_TARGET = _lhref_relative_target(r'\s')

    XML_NAME = r"[\w:](?<!\d)[\w:.-]*?" # See http://www.w3.org/TR/REC-xml/#id
    def _set_anchor(name, sep):
        return r'=#(?P<anchorname>%s)(?:%s(?P<anchorlabel>[^\]]*))?' % \
               (name, sep)

    # Sequence of regexps used by the engine

    _markup_patterns = [
        # Font styles
        r"(?P<bolditalic>!?%s)" % BOLDITALIC_TOKEN,
        r"(?P<bold>!?%s)" % BOLD_TOKEN,
        r"(?P<bold_wc>!?%s)" % BOLD_TOKEN_WIKICREOLE,
        r"(?P<italic>!?%s)" % ITALIC_TOKEN,
        r"(?P<italic_wc>!?%s)" % ITALIC_TOKEN_WIKICREOLE,
        r"(?P<underline>!?%s)" % UNDERLINE_TOKEN,
        r"(?P<strike>!?%s)" % STRIKE_TOKEN,
        r"(?P<subscript>!?%s)" % SUBSCRIPT_TOKEN,
        r"(?P<superscript>!?%s)" % SUPERSCRIPT_TOKEN,
        ]

    _verbatim_patterns = [
        r"(?P<inlinecode>!?%s(?P<inline>.*?)%s)" \
        % (STARTBLOCK_TOKEN, ENDBLOCK_TOKEN),
        r"(?P<inlinecode2>!?%s(?P<inline2>.*?)%s)" \
        % (INLINE_TOKEN, INLINE_TOKEN),
        ]

    _pre_rules = _markup_patterns + _verbatim_patterns

    # Rules provided by IWikiSyntaxProviders will be inserted here

    _inline_patterns = [
        # WikiCreole line breaks
        r"(?P<linebreak_wc>!?\\\\)",
        # e-mails
        r"(?P<email>!?%s)" % EMAIL_LOOKALIKE_PATTERN,
        # <wiki:Trac bracket links>
        r"(?P<shrefbr>!?<(?P<snsbr>%s):(?P<stgtbr>[^>]+)>)" % LINK_SCHEME,
        # &, < and > to &amp;, &lt; and &gt;
        r"(?P<htmlescape>[&<>])",
        # wiki:TracLinks or intertrac:wiki:TracLinks
        r"(?P<shref>!?((?P<sns>%s):(?P<stgt>%s:(?:%s)|%s|%s(?:%s*%s)?)))" \
        % (LINK_SCHEME, LINK_SCHEME, QUOTED_STRING, QUOTED_STRING,
           SHREF_TARGET_FIRST, SHREF_TARGET_MIDDLE, SHREF_TARGET_LAST),
        # [wiki:TracLinks with optional label] or [/relative label]
        (r"(?P<lhref>!?\[(?:"
         r"(?P<rel>%s)|" % LHREF_RELATIVE_TARGET + # ./... or /...
         r"(?P<lns>%s):(?P<ltgt>%s:(?:%s)|%s|[^\]\s\%s]*))" % \
         (LINK_SCHEME, LINK_SCHEME, QUOTED_STRING, QUOTED_STRING, u'\u200b') +
         # wiki:TracLinks or wiki:"trac links" or intertrac:wiki:"trac links"
         r"(?:[\s%s]+(?P<label>%s|[^\]]*))?\])" % \
         (u'\u200b', QUOTED_STRING)), # trailing space, optional label
        # [=#anchor] creation
        r"(?P<anchor>!?\[%s\])" % _set_anchor(XML_NAME, r'\s+'),
        # [[macro]] call or [[WikiCreole link]]
        (r"(?P<macrolink>!?\[\[(?:[^]]|][^]])+\]\])"),
        ]

    # 1.0 compatibility

    _structural_patterns = [
        # == heading == #hanchor
        r"(?P<heading>^\s*(?P<hdepth>={1,6})\s(?P<htext>.*?)"
        r"(?P<hanchor>#%s)?\s*$)" % XML_NAME,
        #  * list
        r"(?P<list>^(?P<ldepth>\s*)"
        ur"(?:[%s]|(?P<lstart>[0-9]+|[a-zA-Z]|[ivxIVX]{1,5})\.)\s)"
        % (BULLET_CHARS),
        # definition::
        r"(?P<definition>^\s+"
        r"((?:%s[^%s]*%s|%s(?:%s{,2}[^%s])*?%s|[^%s%s:]|:[^:])+::)(?:\s+|$))"
        % (INLINE_TOKEN, INLINE_TOKEN, INLINE_TOKEN,
           STARTBLOCK_TOKEN, ENDBLOCK[0], ENDBLOCK[0], ENDBLOCK_TOKEN,
           INLINE_TOKEN, STARTBLOCK[0]),
        # |- row separator
        r"(?P<table_row_sep>!?\s*\|-+\s*"
        r"(?P<table_row_params>%s\s*)*)" % PROCESSOR_PARAM,
        # (leading space)
        r"(?P<indent>^(?P<idepth>\s+)(?=\S))",
        # || table ||
        r"(?P<table_cell>!?(?P<table_cell_sep>=?(?:\|\|)+=?)"
        r"(?P<table_cell_last>\s*\\?$)?)",
        ]

    _post_rules = _inline_patterns + _structural_patterns

    _anchor_re = re.compile(r'[^\w:.-]+', re.UNICODE)

    _macro_re = re.compile(r'''
        (?P<macroname> [\w/+-]+ \?? | \? )     # macro, macro? or ?
          (?: \( (?P<macroargs> .*? ) \) )? $  # optional arguments within ()
    ''', re.VERBOSE)

    _creolelink_re = re.compile(r'''
        (?:
          (?P<rel> %(rel)s )                # rel is "./..." or "/..."
        | (?: (?P<lns> %(scheme)s ) : )?    # lns is the optional "scheme:"
            (?P<ltgt>                       # ltgt is the optional target
              %(scheme)s : (?:%(quoted)s)   #   - "scheme:'...quoted..'"
            | %(quoted)s                    #   - "'...quoted...'"
            | [^|]+                         #   - anything but a '|'
            )?
        )
        \s* (?: \| (?P<label> .* ) )?       # optional label after a '|'
        $
        ''' % {'rel': _lhref_relative_target(r'|'),
               'scheme': LINK_SCHEME,
               'quoted': QUOTED_STRING}, re.VERBOSE)

    _set_anchor_wc_re = re.compile(_set_anchor(XML_NAME, r'\|\s*') + r'$')

    def __init__(self):
        # 0.12 compatibility
        self._compiled_rules = None
        self._link_resolvers = None
        self._helper_patterns = None
        self._external_handlers = None

    # 0.12 compatibility

    @property
    def rules(self):
        self._prepare_rules()
        return self._compiled_rules

    @property
    def helper_patterns(self):
        self._prepare_rules()
        return self._helper_patterns

    @property
    def external_handlers(self):
        self._prepare_rules()
        return self._external_handlers

    def _prepare_rules(self):
        from trac.wiki.api import WikiSystem
        if not self._compiled_rules:
            helpers = []
            handlers = {}
            syntax = self._pre_rules[:]
            i = 0
            for resolver in WikiSystem(self.env).syntax_providers:
                for regexp, handler in resolver.get_wiki_syntax() or []:
                    handlers['i' + str(i)] = handler
                    syntax.append('(?P<i%d>%s)' % (i, regexp))
                    i += 1
            syntax += self._post_rules[:]
            helper_re = re.compile(r'\?P<([a-z\d_]+)>')
            for rule in syntax:
                helpers += helper_re.findall(rule)[1:]
            rules = re.compile('(?:' + '|'.join(syntax) + ')', re.UNICODE)
            self._external_handlers = handlers
            self._helper_patterns = helpers
            self._compiled_rules = rules

    @property
    def link_resolvers(self):
        if not self._link_resolvers:
            from trac.wiki.api import WikiSystem
            resolvers = {}
            for resolver in WikiSystem(self.env).syntax_providers:
                for namespace, handler in resolver.get_link_resolvers() or []:
                    resolvers[namespace] = handler
            self._link_resolvers = resolvers
        return self._link_resolvers

    # ** wikiparser **

    def parse(self, wikitext):
        """Parse `wikitext` and produce a `WikiDocument`"""
        wikidoc = WikiDocument(wikitext)
        self.vertical_parsing(wikidoc, wikidoc)
        return wikidoc

    def vertical_parsing(self, wikidoc, block):
        """Parses the structural markup in the `block` from `wikidoc`."""
        self._detect_nested_blocks(wikidoc, block)

    # -- WikiBlocks

    _processor_re = re.compile(PROCESSOR)

    _startblock_re = re.compile(r'\s*%(startblock)s(?:%(processor)s|\s*$)' % {
        'startblock': STARTBLOCK, 'processor': PROCESSOR})

    def _detect_nested_blocks(self, wikidoc, scope):
        """Each line between ``scope.start`` included and
        ``scope.end`` excluded can start or end a block, beginning at
        column ``scope.j``::

               scope.j
                    |
           0 ..................................... wikidoc.start
             .....................................
             .......xxxxx xx x.xxxxxxxxx ......... scope.start
             .......{{{xxxxx......................
             .......xxxxx.........................
             ..........{{{.xxxxxx.................
             ..........}}}.xxxxxxxx...............
             .......}}}.xxxxxxxxxxxxxxxx..........
             ..................................... scope.end
             .....................................
           n                                       wikidoc.end

        """
        ancestors = [scope]
        for i in xrange(scope.start, scope.end):
            line = wikidoc.lines[i]
            if scope.j:
                line = line[scope.j:]
            if self.ENDBLOCK in line:
                line = line.strip()
                if line.startswith(self.ENDBLOCK):
                    if len(ancestors) == 1: # stray }}}, edit mistake?
                        continue
                    block = ancestors.pop()
                    block.end = i
                    if line != self.ENDBLOCK:
                        block.comment = line[len(self.ENDBLOCK):]
                    if not block.name and block.end - block.start > 0:
                        #  {{{       .i
                        #  #!name    .start
                        #  [...]
                        #  }}}       .end
                        startline = wikidoc.lines[block.start]
                        if scope.j:
                            startline = startline[j:]
                        match = self._processor_re.match(startline)
                        if match:
                            block.start += 1
                            block.name = match.group(2)
                            block.params = parse_processor_params(
                                startline[match.end():])
            else:
                match = self._startblock_re.match(line)
                if match:
                    name = params = match.group(2)
                    if name:
                        # {{{#!name [arg1=val1 arg2="second value" ...]
                        params = parse_processor_params(line[match.end():])
                    j = line.find(WikiParser.STARTBLOCK) + scope.j
                    block = WikiBlock(i, j, name, params)
                    ancestors[-1].nodes.append(block)
                    ancestors.append(block)
        # close unfinished blocks
        while len(ancestors) > 1:
            block = ancestors.pop()
            block.end = scope.end

    _processor_param_re = re.compile(PROCESSOR_PARAM)
    # Note: not using re.UNICODE here as pnames are used as keyword arguments


def parse_processor_params(processor_params):
    """Parse a string containing parameter assignements, and return
    the corresponding dictionary.

    Isolated keywords are interpreted as `bool` flags, `False` if the
    keyword is prefixed with "-", `True` otherwise.

    >>> parse_processor_params('ab="c de -f gh=ij" -')
    {'ab': 'c de -f gh=ij'}

    >>> sorted(parse_processor_params('ab=c de -f gh="ij klmn"').items())
    [('ab', 'c'), ('de', True), ('f', False), ('gh', 'ij klmn')]
    """
    args = WikiParser._processor_param_re.split(processor_params)
    keys = [str(k) for k in args[1::3]] # used as keyword parameters
    values = [v[1:-1] if v[:1] + v[-1:] in ('""', "''") else v
              for v in args[2::3]]
    for flags in args[::3]:
        for flag in flags.strip().split():
            if re.match(r'-?\w+$', flag):
                if flag[0] == '-':
                    if len(flag) > 1:
                        keys.append(str(flag[1:]))
                        values.append(False)
                else:
                    keys.append(str(flag))
                    values.append(True)
    return dict(zip(keys, values))

parse_processor_args = parse_processor_params # 1.0 compat
