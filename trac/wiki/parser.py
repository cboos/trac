# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2013 Edgewall Software
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

from StringIO import StringIO
import re

from trac.core import *
from trac.notification import EMAIL_LOOKALIKE_PATTERN
from .api import IWikiBlockSyntaxProvider, IWikiInlineSyntaxProvider


# -- Wiki DOM

class WikiNode(object):
    """A node represents a syntax unit within the Wiki DOM.

    A node can also be seen as a "pointer" into a `WikiDocument`, as
    it usually doesn't store text by itself, but rather refers to the
    text stored in the document.  All nodes have a starting point in
    the document, line ``i`` and column ``j``.

    A node may have a logical end column ``k``, otherwise it expands
    till the end of the line.

    A node may have children ``nodes``.
    """

    nodes = None #: subnodes
    end = None   #: multiline if not `None`
    k = None     #: eol for this node

    def __init__(self, i, j, k=None):
        self.i = i #: line in corresponding `WikiDocument.lines`
        self.j = j #: start of node within the line
        if k:
            self.k = k

    def lastline(self):
        return self.end or self.i


class WikiBlock(WikiNode):
    """A block corresponds to a multiline section delimited by a pair
    of matching triple curly braces (``{{{`` ... ``}}}``).

    The content of a block starts at line ``start`` and ends at line
    ``end - 1``::

           .j          B3<1-5>
           |
        ................................
        ...{{{#!optional-name........... .i
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
        ...#!name.......................
        ...Content starts here.......... .start
        ...Content ends here............
        ...}}}...optional comment....... .end
        ................................

    If a block processor is specified (e.g. ``#!diff``), ``name``
    contains its name (here 'diff') and ``params`` is a dict with the
    processor's parameters.
    """
    def __init__(self, i, j, name=None, params=None):
        WikiNode.__init__(self, i, j)
        self.start = i + 1 #: start of the actual content
        self.end = self.start
        self.name = name or '' #: name of the directive, empty if no directives
        self.params = params or {} #: parameters of the directive or empty dict
        self.nodes = []
        self.comment = '' #: trailing comment (used as editing help only)

    def __repr__(self):
        return 'B%d<%d%s-%d>%s%s' % (
            self.j, self.i, '+' * (self.start - self.i - 1), self.end,
            self.name or '', self.comment[:10])

    def nodes_of_type(self, types):
        """Iterate on the subset of `.nodes` which are of the given type(s)."""
        for node in self.nodes:
            if isinstance(node, types):
                yield node


class WikiDocument(WikiBlock):
    """A document corresponds to a wiki text in one unit of storage.

    At the same time, it behaves as a root `WikiBlock` spanning the
    whole content (``start == 0``, ``end == len(lines)``).
    """
    def __init__(self, text):
        WikiBlock.__init__(self, 0, 0)
        text = re.sub(WikiParser._normalize_re, ' ', text or '')
        self.lines = text.splitlines() #: original wiki source lines
        self.start = 0
        self.end = len(self.lines)

    def __repr__(self):
        return 'WikiDocument (%d lines)' % len(self.lines)

    def eol(self, i):
        return len(self.lines[i])


# -- Standard structural elements

class WikiItem(WikiNode):
    """Generic block-level wiki syntax node.

    Also used as items in plain unnumbered lists.
    """

    kind = '' #: detail on the nature of the item (e.g. bullet type)

    def __repr__(self):
        return '(%s)%d<%s%s>' % (
            self.kind, self.j, self.i, '-%d' % self.end if self.end else '')


class WikiEnumeratedItem(WikiItem):
    """Specialized item for numbered lists."""


class WikiDescriptionItem(WikiItem):
    """Specialized item for description lists."""

    kind = '::' #: default kind for the WikiDescriptionItem


class WikiRow(WikiItem):
    """Specialized "item" corresponding to a row in a table."""

    kind = '||' #: default kind for the WikiRow


class WikiSection(WikiItem):
    """Specialized "item" corresponding to a section."""

    kind = '='
    depth = 1 #: depth of the section
    anchor = None #: explicit section id
    both_sides = False #: are the '=' characters on both sides?


# -- Standard inline elements

class WikiInline(WikiNode):
    """Generic inline-level wiki syntax node.

    Also used for plain text content. A WikiInline instance never
    spans more than one source line (subclasses can).
    """

    def __repr__(self):
        return 'T%d<%d>:%s' % (self.j, self.i, self.k or '')

class WikiBlankLine(WikiInline):
    """Special kind of inline-level wiki syntax (or non-syntax).

    The blank line can have special meaning during block markup
    consolidation.
    """

    def __repr__(self):
        return '/'


class WikiParser(Component):
    """Wiki text parser."""

    wiki_block_syntax_providers = ExtensionPoint(IWikiBlockSyntaxProvider)
    wiki_inline_syntax_providers = ExtensionPoint(IWikiInlineSyntaxProvider)

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

    _block_raw_re = None
    _block_sensitive_re = None
    _inline_syntax_re = None

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
            # checking _collect_partial_patterns by also using it for legacy
            regexps, handlers = self._collect_partial_patterns(
                WikiSystem(self.env).syntax_providers, 'get_wiki_syntax')
            # note: the groups names have changed from i\d to _i\d
            syntax = self._pre_rules + regexps + self._post_rules
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


    # -- New 1.1.x Wiki Engine

    _private_helper_re = re.compile(r'\(?P<_i\d+>')

    def _collect_partial_patterns(self, providers, method):
        regexps = []
        handlers = {}
        i = 0
        for provider in providers:
            provider_method = getattr(provider, method, None)
            if provider_method:
                method_repr = '%s.%s' % (provider.__class__.__name__, method)
                for builder in provider_method() or []:
                    if isinstance(builder, tuple):
                        regexp, builder = builder
                    else:
                        regexp = builder.regexp
                    # we reserve the (?<_i\d> ...) group names for us
                    forbidden = self._private_helper_re.findall(regexp)
                    if forbidden:
                        self.log.warn(
                            "Rejecting wiki syntax extension from %s '%r'"
                            "as it contains reserved group identifiers: %r",
                            method_repr, regexp, forbidden)
                        continue
                    # each partial regexp must be valid in its own right
                    try:
                        re.compile(regexp)
                    except re.error, e:
                        self.log.warn(
                            "Rejecting wiki syntax extension from %s '%r' "
                            "which is invalid (%s)",
                            method_repr, regexp, e)
                        continue
                    key = '_i' + str(i)
                    i += 1 # I hate Python
                    regexps.append('(?P<%s>%s)' % (key, regexp))
                    handlers[key] = builder
        return regexps, handlers

    @property
    def block_raw_re(self):
        if self._block_raw_re is None:
            regexps, handlers = self._collect_partial_patterns(
                self.wiki_block_syntax_providers, 'get_wiki_line_patterns')
            self._block_raw_re = re.compile('(?:%s)' % '|'.join(regexps),
                                            re.UNICODE)
            self._block_raw_handlers = handlers
        return self._block_raw_re

    @property
    def block_sensitive_re(self):
        if self._block_sensitive_re is None:
            regexps, handlers = self._collect_partial_patterns(
                self.wiki_block_syntax_providers,
                'get_wiki_verbatim_sensitive_line_patterns')
            self._block_sensitive_re = re.compile('(?:%s)' % '|'.join(regexps),
                                                  re.UNICODE)
            self._block_sensitive_handlers = handlers
        return self._block_sensitive_re

    @property
    def inline_regexps(self):
        if self._inline_regexps is None:
            regexps, handlers = self._collect_partial_patterns(
                self.wiki_inline_syntax_providers, 'get_wiki_line_patterns')
        return self._inline_regexps

    # ** wikiparser **

    def parse(self, wikitext):
        """Parse `wikitext` and produce a `WikiDocument`"""
        wikidoc = WikiDocument(wikitext)
        self.vertical_parsing(wikidoc, wikidoc)
        return wikidoc

    def vertical_parsing(self, wikidoc, block):
        """Parses the structural markup in the `block` from `wikidoc`.

        .. todo:: we would actually need to keep track of the stack of
           blocks, i.e. the scopes (or if we decide we don't, remove it
           from IWikiBlockSyntaxProvider).
        """
        self._detect_nested_blocks(wikidoc, block)
        self._parse_between_blocks(wikidoc, [block])

    # -- WikiBlocks

    _processor_re = re.compile(PROCESSOR)

    _processor_param_re = re.compile(PROCESSOR_PARAM)
    # Note: not using re.UNICODE here as pnames are used as keyword arguments

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

        The tree of nested blocks will be rooted in the given *scope*.
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

    # -- WikiItems

    _indent_re = re.compile('\s*')

    def _parse_between_blocks(self, wikidoc, scopes):
        """Associate one WikiNode with lines outside of `WikiBlock` subnodes.

        Each line outside of the children `WikiBlock` will be parsed
        with regexps contributed by
        `~trac.wiki.api.IWikiSyntaxProviders` and the corresponding
        nodes will be built and merged with the `WikiBlock` nodes.
        """
        def build_node(handlers, i, fullmatch):
            if fullmatch:
                for name, match in fullmatch.groupdict().items():
                    if match and name.startswith('_i'): # TODO check \d+
                        builder = handlers.get(name)
                        if builder:
                            return builder(wikidoc, scopes, i, fullmatch)
        scope = scopes[-1]
        oldnodes = scope.nodes
        n = 0
        oldnode = oldnodes[n] if n < len(oldnodes) else None
        newnodes = []
        i = scope.start
        while i < scope.end:
            # integrate oldnode into the new nodes if we're hitting it
            if oldnode and i == oldnode.i:
                newnodes.append(oldnode)
                n += 1
                i = oldnode.end + 1
                oldnode = oldnodes[n] if n < len(oldnodes) else None
                continue
            # we're in between blocks, parse for structural syntax
            line = wikidoc.lines[i]
            if line:
                fullmatch = self.block_raw_re.match(line, scope.j)
                newnode = build_node(self._block_raw_handlers, i,
                                     fullmatch)
                if newnode is None:
                    safe_line = self.make_verbatime_safe(line)
                    fullmatch = self.block_sensitive_re.match(safe_line,
                                                              scope.j)
                    newnode = build_node(self._block_sensitive_handlers, i,
                                         fullmatch)
                if newnode is None:
                    fullmatch = self._indent_re.match(line, scope.j)
                    j = fullmatch.end(0)
                    newnode = (WikiInline if j < wikidoc.eol(i)
                               else WikiBlankLine)(i, j)
            else:
                newnode = WikiBlankLine(i, scope.j)
            newnodes.append(newnode)
            i += 1
        scope.nodes = newnodes

    def make_verbatime_safe(self, line):
        """This is a very crude verbatim escape.

        I think it does what Trac 1.0 did, but we'll need to use
        `IWikiInlineSyntaxProvider.get_wiki_verbatim_patterns` here.
        """
        def replace_verbatim(match):
            s, e = match.span(0)
            return 'x' * (e - s)
        return re.sub(r'`[^`]+`|{{{(?:[^}]|}[^}]|}}[^}])+}}}',
                      replace_verbatim, line)


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
