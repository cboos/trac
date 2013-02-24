:mod:`trac.wiki.parser` -- The Wiki Parser API
==============================================

.. module :: trac.wiki.parser


The Wiki Document Object Model
------------------------------

..      autoclass :: WikiDocument


A WikiDOM tree is made of `WikiNode` and its subclasses.

..      autoclass :: WikiNode

..      autoclass :: WikiBlock


The parser
----------

..      autoclass :: WikiParser

..   autofunction :: parse_processor_params


For backward compatibility with Trac 1.0
----------------------------------------

..   function :: parse_processor_args
  
  Alias for `parse_processor_params`.
