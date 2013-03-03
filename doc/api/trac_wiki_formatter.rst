:mod:`trac.wiki.formatter` -- The Wiki Formatter API
====================================================

.. module :: trac.wiki.formatter

Rendering a `WikiDocument`
--------------------------

..   autofunction :: format_to
..   autofunction :: format_to_html
..   autofunction :: format_to_oneliner


Utilities
---------

..   autofunction :: extract_link
..   autofunction :: split_url_into_path_query_fragment
..   autofunction :: concat_path_query_fragment


The implementation of standard formatters
-----------------------------------------

.. autoclass :: WikiHtmlFormatters
   :members:

The above component yields the following `~trac.wiki.api.WikiFormatter`:

.. autoclass :: WikiPageFormatter
   :members:

.. autoclass :: WikiInlineFormatter
   :members:

.. autoclass :: WikiOutlineFormatter
   :members:

Besides HTML, it is also possible out of the box to format to text.

.. autoclass :: WikiSourceFormatters
   :members:

.. autoclass :: WikiSourceFormatter
   :members:

.. autoclass :: DebugSource
   :members:

There are a few more formatters for helping to debug the wiki parser.

.. autoclass :: DebugFormatters
   :members:

.. autoclass :: DebugParseTime
   :members:

.. autoclass :: DebugBlockStructure
   :members:


The legacy API
--------------

..      autoclass :: Formatter
..   autofunction :: wiki_to_html
..   autofunction :: wiki_to_oneliner
..   autofunction :: wiki_to_outline

