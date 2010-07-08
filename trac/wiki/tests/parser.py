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
    }}}
    {{{#!td
    Well, for the arbirary nesting, I think it's OK...
    {{{
    #!python
    def hello(self):
       return "world"
    }}}
    {{{#!comment
      We could always add more levels...
      {{{
         {{{
         }}}
         ...
         {{{
             ...
         }}}
      }}}
      but it should already be good enough
    }}}
    }}}
    |-------
    {{{#!td
    Arbitrary list of parameters can be given in blocks:
        {{{#!div style="white-space:pre; font-family: monospace"
        this ... is ...
            some ... fixed ... space ... text
               ...
        }}}
        or even:
        {{{
        #!div class="important" style="border: 4px outset red"
        See?
        }}}
    }}}
  }}}
    More content:
     - a first item in a list
     {{{
     a block in this first item
     }}}
     - a second item
       {{{
    A second block, in this second item
    }}}
 - back to a previous level (we were in a quote above)
   {{{
More block content
    {{{
        ...
    }}}
   }}}
  }}}
}}}
More toplevel content
{{{#!comment
    ... nothing to see here ...
}}}
 - a toplevel list
   {{{
   next to last block
   }}}
  {{{
       last block
  }}}
 - a toplevel list (2)
"""

class WikiDocumentInvariants(unittest.TestCase):
    def test_empty(self):
        w = WikiDocument(empty)
        self.assertEquals(w.root.key, 'W')
        self.assertEquals(repr(w.root), 'W0')
        self.assertEquals(w.lines, [])
        self.assertEquals(w.blocks, [])

    def test_None(self):
        w = WikiDocument(None)
        self.assertEquals(w.root.key, 'W')
        self.assertEquals(repr(w.root), 'W0')
        self.assertEquals(w.lines, [])
        self.assertEquals(w.blocks, [])

    def test_singleline(self):
        w = WikiDocument(singleline)
        self.assertEquals(w.root.key, 'W')
        self.assertEquals(repr(w.root), 'W0')
        self.assertEquals(len(w.lines), 1)
        self.assertEquals(w.blocks, [])

    def test_multiline(self):
        w = WikiDocument(multiline)
        self.assertEquals(w.root.key, 'W')
        self.assertEquals(repr(w.root), 'W0')
        self.assertEquals(len(w.lines), 4)
        self.assertEquals(w.blocks, [])

    # ...
    
    def test_multilevelblock(self):
        w = WikiDocument(multilevelblock)
        self.assertEquals(w.root.key, 'W')
        self.assertEquals(repr(w.root), 'W0')
        self.assertEquals(len(w.lines), 74)
        self.assertEquals(w.blocks, [])



class WikiDocumentBlocks(unittest.TestCase):
    def setUp(self):
        self.env = EnvironmentStub()

    def detect_nested_blocks(self, source):
        wikidoc = WikiDocument(source)
        WikiParser(self.env)._detect_nested_blocks(wikidoc)
        return wikidoc

    def blocktree(self, wb):
        if wb.blocks:
            return '%s {%s}' % \
                   (repr(wb), ', '.join(self.blocktree(b) for b in wb.blocks))
        else:
            return repr(wb)

    def test_empty(self):
        w = self.detect_nested_blocks(empty)
        self.assertEquals(w.blocks, [])
        self.assertEquals(self.blocktree(w), 'WikiDocument (0 lines)')

    def test_None(self):
        w = self.detect_nested_blocks(None)
        self.assertEquals(w.blocks, [])
        self.assertEquals(self.blocktree(w), 'WikiDocument (0 lines)')

    def test_singleline(self):
        w = self.detect_nested_blocks(singleline)
        self.assertEquals(w.blocks, [])
        self.assertEquals(self.blocktree(w), 'WikiDocument (1 lines)')

    def test_multiline(self):
        w = self.detect_nested_blocks(multiline)
        self.assertEquals(w.blocks, [])
        self.assertEquals(self.blocktree(w), 'WikiDocument (4 lines)')

    def test_singleblock(self):
        w = self.detect_nested_blocks(singleblock)
        self.assertEquals(repr(w.blocks), '[B0<1-3>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (5 lines) {B0<1-3>}')
    
    def test_stillsingleblock(self):
        w = self.detect_nested_blocks(stillsingleblock)
        self.assertEquals(repr(w.blocks), '[B0<0-4>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (5 lines) {B0<0-4>}')
    
    def test_nestedemptyblock(self):
        w = self.detect_nested_blocks(nestedemptyblock)
        self.assertEquals(repr(w.blocks), '[B0<0-4>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (5 lines) {'
                          + 'B0<0-4> {'
                          +  'B0<2-3>nested'
                          + '}'
                          '}')

    def test_nestedblock(self):
        w = self.detect_nested_blocks(nestedblock)
        self.assertEquals(repr(w.blocks), '[B0<0-5>embeds]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (6 lines) {'
                          + 'B0<0-5>embeds {'
                          +  'B0<2-4>nested'
                          + '}'
                          '}')

    def test_startblock(self):
        w = self.detect_nested_blocks(startblock)
        self.assertEquals(repr(w.blocks), '[B0<0-2>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (4 lines) {B0<0-2>}')

    def test_endblock(self):
        w = self.detect_nested_blocks(endblock)
        self.assertEquals(repr(w.blocks), '[B0<1-3>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (4 lines) {B0<1-3>}')

    def test_unfinishedblock(self):
        w = self.detect_nested_blocks(unfinishedblock)
        self.assertEquals(repr(w.blocks), '[B0<1-3>]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (3 lines) {B0<1-3>}')

    def test_multiblock(self):
        w = self.detect_nested_blocks(multiblock)
        self.assertEquals(repr(w.blocks),
                          '[B0<0-2>first, B2<3-5>second, B0<7-9>third]')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (10 lines) {'
                          + 'B0<0-2>first, '
                          + 'B2<3-5>second, '
                          + 'B0<7-9>third'
                          '}')

    def test_multilevelblock(self):
        w = self.detect_nested_blocks(multilevelblock)
        self.assertEquals(repr(w.blocks), '['
                          'B0<1-60>div, B0<63-65>comment, B3<67-69>, B2<70-72>'
                          ']')
        self.assertEquals(self.blocktree(w),
                          'WikiDocument (74 lines) {'
                          + 'B0<1-60>div {'
                          +  'B2<3-43>table {'
                          +   'B4<4-8>th, '
                          +   'B4<9-28>td {'
                          +    'B4<11-15>python, '
                          +    'B4<16-27>comment {'
                          +     'B6<18-25> {'
                          +      'B9<19-20>, '
                          +      'B9<22-24>'
                          +     '}'
                          +    '}'
                          +   '}, '
                          +   'B4<30-42>td {'
                          +    'B8<32-36>div, '
                          +    'B8<38-41>div'
                          +   '}'
                          +  '}, '
                          +  'B5<46-48>, '
                          +  'B7<50-52>, '
                          +  'B3<54-59> {'
                          +    'B4<56-58>'
                          +  '}'  
                          + '}, '
                          + 'B0<63-65>comment, '
                          + 'B3<67-69>, '
                          + 'B2<70-72>'
                          '}'
                          )


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(WikiDocumentInvariants, 'test'))
    suite.addTest(unittest.makeSuite(WikiDocumentBlocks, 'test'))
    return suite
    
if __name__ == '__main__':
    unittest.main(defaultTest='suite')

