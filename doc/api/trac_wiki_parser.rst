:mod:`trac.wiki.parser` -- The Wiki Parser API
==============================================

.. module :: trac.wiki.parser


The Wiki Document Object Model
------------------------------

A WikiDOM tree is made of `WikiNode` and its subclasses.

..      autoclass :: WikiNode
   :members:

..      autoclass :: WikiBlock
   :members:

..      autoclass :: WikiDocument
   :members:


The parser
----------

..      autoclass :: WikiParser
   :members:

..   autofunction :: parse_processor_params


For backward compatibility with Trac 1.0
----------------------------------------

..    py:function :: parse_processor_args
  
  Alias for `parse_processor_params`.
