:mod:`trac.wiki.api` -- The Wiki API
====================================

.. module :: trac.wiki.api


Interfaces
----------

The wiki module presents several possibilities of extension, for
interacting with the Wiki application and also for extending the Wiki
syntax.

Interacting with Wiki pages
...........................

First, components can be notified of the changes happening in the
wiki.

.. autoclass :: IWikiChangeListener
   :members:

   See also :extensionpoints:`trac.wiki.api.IWikiChangeListener`.

Components can also interfere with the changes, before or after
they're made.

.. autoclass :: IWikiPageManipulator
   :members:

   See also :extensionpoints:`trac.wiki.api.IWikiPageManipulator`.


Augmenting the Wiki syntax
..........................

Then, the Wiki syntax itself can be extended. The first and less
intrusive way is to provide new Wiki macros or Wiki processors. Those
are basically the same thing, as they're implemented using the
following interface. The difference comes from the invocation
syntax used in the Wiki markup, which manifests itself in the `args`
parameter of :meth:`IWikiMacroProvider.expand_macro`.

.. autoclass :: IWikiMacroProvider
   :members:

   See also `~trac.wiki.macros.WikiMacroBase` and
   :teo:`wiki/WikiMacros#DevelopingCustomMacros` and
   :extensionpoints:`trac.wiki.api.IWikiMacroProvider`.


The Wiki syntax can also be extended by introducing new markup.

.. autoclass :: IWikiSyntaxProvider
   :members:

   See also :teo:`wiki:TracDev/IWikiSyntaxProviderExample` and
   :extensionpoints:`trac.wiki.api.IWikiSyntaxProvider`.

.. autoclass :: IWikiBlockSyntaxProvider
   :members:

   See also :extensionpoints:`trac.wiki.api.IWikiBlockSyntaxProvider`.

.. autoclass :: IWikiInlineSyntaxProvider
   :members:

   See also :extensionpoints:`trac.wiki.api.IWikiInlineSyntaxProvider`.

Note that the regular expressions provided by the above two will be
used with `re.match`, so there's no need to prepend the ``^`` sign.


Adding rendering formats
........................

..      autoclass :: IWikiFormatterProvider
   :members:


The Wiki System
---------------

The wiki system provide an access to all the pages.

.. autoclass :: WikiSystem
   :members:
   :exclude-members: get_resource_description, resource_exists



Other Functions
---------------

.. autofunction :: wiki_regexp
.. autofunction :: parse_args
.. autofunction :: validate_page_name

