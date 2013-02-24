# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.

import unittest
from trac.test import EnvironmentStub
from trac.wiki.parser import WikiBlock, WikiDocument, WikiNode, WikiParser

empty = ""

singleline = u"This is some very simple text, with hardly any markup..."

multiline = u"""\
This is some larger text,
but there's still not much to see...

Eventually a new paragraph, but that's it.
"""

singleblock = u"""\
Now this is getting more interesting:
{{{
A block
}}}
(single block in the middle)
"""

stillsingleblock = u"""\
{{{
A block
{{{#!not}}}
{{{a}}}
}}}
"""

emptyblock = u"""\
{{{
}}}
"""

nestedemptyblock = u"""\
{{{
A block
{{{#!nested
}}}
}}}
"""

nestedblock = u"""\
{{{#!embeds
A block
{{{#!nested
block
}}}
}}}
"""
startblock = u"""\
{{{
A block
}}}
(single block in the middle)
"""

endblock = u"""\
Now this is getting more interesting:
{{{
A block
}}}
"""

unfinishedblock = u"""\
Now this is getting more interesting:
{{{
A block
"""

multiblock = u"""\
{{{#!first
first
}}}
  {{{#!second
second
  }}}
third:
{{{#!third
block
}}}
"""

multilevelblock = u"""\
Now this is getting even more interesting:
{{{#!div
A block:
  {{{#!table style="border-width: 0"
    {{{#!th rowspan=2 style="border-width: 2px"
    Different things to support:
     - arbitrary nesting
     - parameterized blocks
    }}} th
    {{{#!td
    Well, for the arbirary nesting, I think it's OK...
    {{{
    #!python
    def hello(self):
       return "world"
    }}} py
    {{{#!comment
      We could always add more levels...
      {{{
         {{{
         }}} a11
         ...
         {{{
             ...
         }}} a12
      }}} a1
      but it should already be good enough
    }}} comment1
    }}} td1
    |-------
    {{{#!td
    Arbitrary list of parameters can be given in blocks:
        {{{#!div style="white-space:pre; font-family: monospace"
        this ... is ...
            some ... fixed ... space ... text
               ...
        }}} div+style
        or even:
        {{{
        #!div class="important" style="border: 4px outset red"
        See?
        }}} div+class
    }}} td2
  }}} th
    More content:
     - a first item in a list
     {{{
     a block in this first item
     }}} a2
     - a second item
       {{{
    A second block, in this second item
    }}} a3
 - back to a previous level (we were in a quote above)
   {{{
More block content
    {{{
        ...
    }}} a41
   }}} starts at col 3!
  }}} table
}}} toplevel div
More toplevel content
{{{#!comment
    ... nothing to see here ...
}}} comment2
 - a toplevel list
   {{{
   next to last block
   }}} b1
  {{{
       last block
  }}} b2
 - a toplevel list (2)
"""

scopedblock = """\
At global level, there's no block.
> But starting from here, we'll see one:
> {{{#!div
> Nested:
> > {{{
> > ...
> > }}}
> }}}
"""

class WikiDocumentInvariants(unittest.TestCase):
    def test_empty(self):
        w = WikiDocument(empty)
        self.assertEquals(w.lines, [])
        self.assertEquals(w.nodes, [])

    def test_None(self):
        w = WikiDocument(None)
        self.assertEquals(w.lines, [])
        self.assertEquals(w.nodes, [])

    def test_singleline(self):
        w = WikiDocument(singleline)
        self.assertEquals(len(w.lines), 1)
        self.assertEquals(w.nodes, [])

    def test_multiline(self):
        w = WikiDocument(multiline)
        self.assertEquals(len(w.lines), 4)
        self.assertEquals(w.nodes, [])

    # ...

    def test_multilevelblock(self):
        w = WikiDocument(multilevelblock)
        self.assertEquals(len(w.lines), 74)
        self.assertEquals(w.nodes, [])



class WikiDocumentBlocks(unittest.TestCase):
    def setUp(self):
        self.env = EnvironmentStub()

    def detect_nested_blocks(self, source, scope=None):
        wikidoc = WikiDocument(source)
        if not scope:
            scope = wikidoc
        WikiParser(self.env)._detect_nested_blocks(wikidoc, scope)
        return scope

    def blocktree(self, wb):
        if wb.nodes:
            return '%s {%s}' % (
                repr(wb), ', '.join(self.blocktree(b) for b in wb.nodes))
        else:
            return repr(wb)

    def test_empty(self):
        w = self.detect_nested_blocks(empty)
        self.assertEquals(w.nodes, [])
        self.assertEquals(self.blocktree(w), 'WikiDocument (0 lines)')

    def test_None(self):
        w = self.detect_nested_blocks(None)
        self.assertEquals(w.nodes, [])
        self.assertEquals(self.blocktree(w), 'WikiDocument (0 lines)')

    def test_singleline(self):
        w = self.detect_nested_blocks(singleline)
        self.assertEquals(w.nodes, [])
        self.assertEquals(self.blocktree(w), 'WikiDocument (1 lines)')

    def test_multiline(self):
        w = self.detect_nested_blocks(multiline)
        self.assertEquals(w.nodes, [])
        self.assertEquals(self.blocktree(w), 'WikiDocument (4 lines)')

    def test_singleblock(self):
        w = self.detect_nested_blocks(singleblock)
        self.assertEquals(repr(w.nodes), '[B0<1-3>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (5 lines) {B0<1-3>}')

    def test_stillsingleblock(self):
        w = self.detect_nested_blocks(stillsingleblock)
        self.assertEquals(repr(w.nodes), '[B0<0-4>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (5 lines) {B0<0-4>}')

    def test_nestedemptyblock(self):
        w = self.detect_nested_blocks(nestedemptyblock)
        self.assertEquals(repr(w.nodes), '[B0<0-4>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (5 lines) {'
                          + 'B0<0-4> {'
                          +  'B0<2-3>nested'
                          + '}'
                          '}')

    def test_nestedblock(self):
        w = self.detect_nested_blocks(nestedblock)
        self.assertEquals(repr(w.nodes), '[B0<0-5>embeds]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (6 lines) {'
                          + 'B0<0-5>embeds {'
                          +  'B0<2-4>nested'
                          + '}'
                          '}')

    def test_startblock(self):
        w = self.detect_nested_blocks(startblock)
        self.assertEquals(repr(w.nodes), '[B0<0-2>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (4 lines) {B0<0-2>}')

    def test_endblock(self):
        w = self.detect_nested_blocks(endblock)
        self.assertEquals(repr(w.nodes), '[B0<1-3>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (4 lines) {B0<1-3>}')

    def test_unfinishedblock(self):
        w = self.detect_nested_blocks(unfinishedblock)
        self.assertEquals(repr(w.nodes), '[B0<1-3>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (3 lines) {B0<1-3>}')

    def test_multiblock(self):
        w = self.detect_nested_blocks(multiblock)
        self.assertEquals(repr(w.nodes),
                          '[B0<0-2>first, B2<3-5>second, B0<7-9>third]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (10 lines) {'
                          + 'B0<0-2>first, '
                          + 'B2<3-5>second, '
                          + 'B0<7-9>third'
                          '}')

    def test_multilevelblock(self):
        w = self.detect_nested_blocks(multilevelblock)
        self.assertEquals(repr(w.nodes), '['
                          'B0<1-60>div table, ' # toplevel div
                          'B0<63-65>comment comment2, '
                          'B3<67-69> b1, '
                          'B2<70-72> b2'
                          ']')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (74 lines) {'
                          + 'B0<1-60>div table {' # toplevel div
                          +  'B2<3-43>table th {'
                          +   'B4<4-8>th th, '
                          +   'B4<9-28>td td1 {'
                          +    'B4<11+-15>python py, '
                          +    'B4<16-27>comment comment1 {'
                          +     'B6<18-25> a1 {'
                          +      'B9<19-20> a11, '
                          +      'B9<22-24> a12'
                          +     '}'
                          +    '}'
                          +   '}, '
                          +   'B4<30-42>td td2 {'
                          +    'B8<32-36>div div+style, '
                          +    'B8<38+-41>div div+class'
                          +   '}'
                          +  '}, '
                          +  'B5<46-48> a2, '
                          +  'B7<50-52> a3, '
                          +  'B3<54-59> starts at {'
                          +    'B4<56-58> a41'
                          +  '}'
                          + '}, '
                          + 'B0<63-65>comment comment2, '
                          + 'B3<67-69> b1, '
                          + 'B2<70-72> b2'
                          '}'
                          )

    def test_multilevelblock_subblock(self):
        scope = WikiBlock(44, 4)
        scope.end = 44 + 16
        w = self.detect_nested_blocks(multilevelblock, scope)
        self.assertEquals(repr(w.nodes), '['
                          'B5<46-48> a2, '
                          'B7<50-52> a3, '
                          'B4<56-58> a41'
                          ']')
        self.assertEquals(self.blocktree(w),
                          'B4<44-60> {'
                          + 'B5<46-48> a2, '
                          + 'B7<50-52> a3, '
                          + 'B4<56-58> a41'
                          '}'
                          )

    def test_scopedblock(self):
        w = self.detect_nested_blocks(scopedblock)
        self.assertEquals(repr(w.nodes), '[]')
        scope = WikiBlock(1, 1)
        scope.end = 7
        w2 = self.detect_nested_blocks(scopedblock, scope)
        self.assertEquals(repr(w2.nodes), '[B2<2-7>div]')
        self.assertEquals(self.blocktree(w2), 'B1<1-7> {B2<2-7>div}')

    def test_wikiprocessor_name_and_params(self):
        w = self.detect_nested_blocks(multilevelblock)
        table = w.nodes[0].nodes[0]
        self.assertEquals(table.name, 'table')
        self.assertEquals(table.params, {'style': 'border-width: 0'})
        th = table.nodes[0]
        self.assertEquals(th.name, 'th')
        self.assertEquals(len(th.params), 2)
        self.assertEquals(th.params['rowspan'], '2')
        self.assertEquals(th.params['style'], 'border-width: 2px')
        td = table.nodes[2]
        self.assertEquals(td.name, 'td')
        div1 = td.nodes[0]
        self.assertEquals(div1.name, 'div')
        self.assertEquals(div1.params, {
            'style': 'white-space:pre; font-family: monospace'})
        div2 = td.nodes[1]
        self.assertEquals(div2.name, 'div')
        self.assertEquals(len(div2.params), 2)
        self.assertEquals(div2.params['class'], 'important')
        self.assertEquals(div2.params['style'], 'border: 4px outset red')



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(WikiDocumentInvariants, 'test'))
    suite.addTest(unittest.makeSuite(WikiDocumentBlocks, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
